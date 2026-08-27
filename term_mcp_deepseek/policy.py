"""Default-deny command policy scoped to one workspace."""

from __future__ import annotations

import os
import re
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path

from term_mcp_deepseek.domain import ApprovalMode, PolicyDecision, RiskLevel

SHELL_METACHARACTERS = re.compile(r"[|&;<>\u0060$()\n\r]")
READ_ONLY_COMMANDS = {
    "cat",
    "df",
    "du",
    "find",
    "git",
    "grep",
    "head",
    "ls",
    "pwd",
    "rg",
    "stat",
    "tail",
    "wc",
}
WRITE_COMMANDS = {"cp", "mkdir", "mv", "rm", "touch"}
DEVELOPMENT_COMMANDS = {
    "cargo",
    "go",
    "make",
    "npm",
    "pnpm",
    "pytest",
    "ruff",
    "sleep",
    "uv",
    "yarn",
}
ALWAYS_BLOCKED_COMMANDS = {
    "bash",
    "curl",
    "dd",
    "docker",
    "env",
    "fdisk",
    "fish",
    "mkfs",
    "nc",
    "netcat",
    "node",
    "perl",
    "php",
    "pip",
    "python",
    "python3",
    "ruby",
    "scp",
    "sh",
    "ssh",
    "sudo",
    "wget",
    "zsh",
}
READ_ONLY_GIT_SUBCOMMANDS = {
    "branch",
    "diff",
    "log",
    "ls-files",
    "rev-parse",
    "show",
    "status",
}
WRITE_GIT_SUBCOMMANDS = {"add", "commit", "restore", "switch"}
BLOCKED_FIND_FLAGS = {"-delete", "-exec", "-execdir", "-fls", "-fprint", "-fprintf", "-ok"}
BLOCKED_RG_FLAGS = {"--pre", "--hostname-bin"}
PATH_OPTIONS = {
    "-C",
    "--cwd",
    "--directory",
    "--file",
    "--git-dir",
    "--output",
    "--path",
    "--work-tree",
}
SYSTEM_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
SYMLINK_FOLLOW_FLAGS = {
    "du": {"-L", "--dereference"},
    "find": {"-H", "-L"},
    "grep": {"-R", "--dereference-recursive"},
    "rg": {"-L", "--follow"},
}


@dataclass(frozen=True)
class CommandPolicy:
    workspace_root: Path
    mode: ApprovalMode = ApprovalMode.INSPECT
    allow_network: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "workspace_root", self.workspace_root.resolve())

    def analyze(self, command: str, cwd: str | Path | None = None) -> PolicyDecision:
        reasons: list[str] = []
        if not command or not isinstance(command, str):
            return self._blocked("command must be a non-empty string")
        if len(command) > 1000:
            return self._blocked("command exceeds the 1000 character limit")
        if SHELL_METACHARACTERS.search(command):
            return self._blocked("shell composition and expansion are not allowed")

        try:
            argv = shlex.split(command, posix=True)
        except ValueError:
            return self._blocked("command quoting is invalid")
        if not argv:
            return self._blocked("command must contain an executable")

        executable = Path(argv[0]).name
        if argv[0] != executable:
            return self._blocked("executable paths are not accepted; use an allowlisted name", argv)
        if executable in ALWAYS_BLOCKED_COMMANDS:
            return self._blocked(f"{executable} is outside the safe command surface", argv)

        selected_cwd = self._resolve_cwd(cwd)
        if selected_cwd is None:
            return self._blocked("working directory is outside the configured workspace", argv)

        path_error = self._validate_paths(argv[1:], selected_cwd)
        if path_error:
            return self._blocked(path_error, argv)
        blocked_follow_flags = SYMLINK_FOLLOW_FLAGS.get(executable, set())
        if any(token in blocked_follow_flags for token in argv[1:]):
            return self._blocked("options that follow symlinks are blocked", argv)

        resolved_executable = self._resolve_executable(
            executable,
            include_workspace_venv=executable in DEVELOPMENT_COMMANDS,
        )
        if resolved_executable is None:
            return self._blocked(f"{executable} is not installed in a trusted location", argv)
        argv[0] = resolved_executable

        if executable == "git":
            return self._analyze_git(argv, reasons)
        if executable == "find" and any(token in BLOCKED_FIND_FLAGS for token in argv[1:]):
            return self._blocked("find actions that execute or modify files are blocked", argv)
        if executable == "rg" and any(
            token.split("=", 1)[0] in BLOCKED_RG_FLAGS for token in argv[1:]
        ):
            return self._blocked("ripgrep preprocessors are blocked", argv)

        if executable == "sleep":
            return PolicyDecision(
                True,
                RiskLevel.MEDIUM,
                self.mode is not ApprovalMode.TRUSTED,
                ["long-running process requires an explicit approval"],
                argv,
            )

        if executable in READ_ONLY_COMMANDS:
            return PolicyDecision(True, RiskLevel.LOW, False, ["read-only command"], argv)

        if executable in WRITE_COMMANDS:
            broad_delete = executable == "rm" and self._is_broad_delete(argv[1:])
            if broad_delete:
                return self._blocked("broad deletion of the workspace is never allowed", argv)
            if self.mode is ApprovalMode.INSPECT:
                return self._blocked("write commands are disabled in inspect mode", argv)
            return PolicyDecision(
                True,
                RiskLevel.HIGH,
                self.mode is ApprovalMode.CONFIRM,
                ["command can modify workspace files"],
                argv,
            )

        if executable in DEVELOPMENT_COMMANDS:
            if self.mode is ApprovalMode.INSPECT:
                return self._blocked("development commands require confirm or trusted mode", argv)
            if not self.allow_network and self._requests_network(executable, argv[1:]):
                return self._blocked("network-capable dependency operations are disabled", argv)
            return PolicyDecision(
                True,
                RiskLevel.MEDIUM,
                self.mode is ApprovalMode.CONFIRM,
                ["development command may execute project-defined code"],
                argv,
            )

        return self._blocked(f"{executable} is not in the configured command allowlist", argv)

    def resolve_cwd(self, cwd: str | Path | None = None) -> Path:
        selected = self._resolve_cwd(cwd)
        if selected is None:
            raise ValueError("working directory is outside the configured workspace")
        return selected

    def resolve_resource(self, relative_path: str) -> Path:
        unresolved = self.workspace_root / relative_path
        if unresolved.is_symlink():
            raise ValueError("resource symlinks are not readable")
        candidate = unresolved.resolve()
        if not candidate.is_relative_to(self.workspace_root):
            raise ValueError("resource path is outside the configured workspace")
        return candidate

    def _analyze_git(
        self,
        argv: list[str],
        reasons: list[str],
    ) -> PolicyDecision:
        subcommand = next((token for token in argv[1:] if not token.startswith("-")), "")
        if subcommand in READ_ONLY_GIT_SUBCOMMANDS:
            return PolicyDecision(True, RiskLevel.LOW, False, ["read-only git command"], argv)
        if subcommand in WRITE_GIT_SUBCOMMANDS:
            if self.mode is ApprovalMode.INSPECT:
                return self._blocked("git write commands are disabled in inspect mode", argv)
            reasons.append("git command modifies repository state")
            return PolicyDecision(
                True,
                RiskLevel.HIGH,
                self.mode is ApprovalMode.CONFIRM,
                reasons,
                argv,
            )
        return self._blocked("git subcommand is not allowlisted", argv)

    def _resolve_cwd(self, cwd: str | Path | None) -> Path | None:
        candidate = self.workspace_root if cwd is None else Path(cwd)
        if not candidate.is_absolute():
            candidate = self.workspace_root / candidate
        candidate = candidate.resolve()
        if not candidate.is_dir() or not candidate.is_relative_to(self.workspace_root):
            return None
        return candidate

    def _resolve_executable(
        self,
        executable: str,
        *,
        include_workspace_venv: bool,
    ) -> str | None:
        search_entries = SYSTEM_PATH.split(":")
        for entry in os.environ.get("PATH", "").split(":"):
            if not entry:
                continue
            path = Path(entry)
            if not path.is_absolute():
                continue
            resolved = path.resolve()
            if resolved.is_relative_to(self.workspace_root):
                continue
            value = str(resolved)
            if value not in search_entries:
                search_entries.append(value)
        if include_workspace_venv:
            search_entries.insert(0, str(self.workspace_root / ".venv" / "bin"))
        return shutil.which(executable, path=":".join(search_entries))

    def _validate_paths(self, args: list[str], cwd: Path) -> str | None:
        expect_path = False
        for token in args:
            if token == "--":
                expect_path = False
                continue
            if token in PATH_OPTIONS:
                expect_path = True
                continue
            option, separator, option_value = token.partition("=")
            if separator and option in PATH_OPTIONS:
                path_error = self._validate_path_token(option_value, cwd)
                if path_error:
                    return path_error
                continue
            if token.startswith("-") and not expect_path:
                continue
            if expect_path or self._looks_like_path(token, cwd):
                path_error = self._validate_path_token(token, cwd)
                if path_error:
                    return path_error
            expect_path = False
        return None

    def _validate_path_token(self, token: str, cwd: Path) -> str | None:
        if not token or token in {".", "./"}:
            return None
        candidate = Path(token)
        if not candidate.is_absolute():
            candidate = cwd / candidate
        resolved = candidate.resolve(strict=False)
        if not resolved.is_relative_to(self.workspace_root):
            return f"path escapes the workspace: {token}"
        return None

    @staticmethod
    def _looks_like_path(token: str, cwd: Path) -> bool:
        return token.startswith(("/", "./", "../", "~")) or "/" in token or (cwd / token).exists()

    @staticmethod
    def _is_broad_delete(args: list[str]) -> bool:
        dangerous_targets = {".", "./", "*", "**", "..", "../"}
        return any(token in dangerous_targets for token in args)

    @staticmethod
    def _requests_network(executable: str, args: list[str]) -> bool:
        if executable in {"npm", "pnpm", "yarn"}:
            return any(arg in {"add", "install", "update"} for arg in args)
        if executable == "cargo":
            return any(arg in {"add", "fetch", "install", "update"} for arg in args)
        if executable == "go":
            return any(arg in {"get", "install"} for arg in args)
        if executable == "uv":
            return any(arg in {"add", "pip", "sync"} for arg in args)
        return False

    @staticmethod
    def _blocked(reason: str, argv: list[str] | None = None) -> PolicyDecision:
        return PolicyDecision(False, RiskLevel.BLOCKED, False, [reason], argv or [])


__all__ = ["CommandPolicy"]
