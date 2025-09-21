"""
MCP Server Business Logic
Handles MCP protocol implementation and terminal operations
"""

import asyncio
from typing import Dict, Any, List
from tools.command_executor import CommandExecutor
from tools.tty_output_reader import TtyOutputReader
from tools.send_control_character import SendControlCharacter
from tools.json_rpc import JSONRPCError
from tools.input_validator import InputValidator
from config import Config
config = Config()

class MCPServer:
    """MCP Server implementation with business logic"""

    def __init__(self, shell):
        self.shell = shell
        self.jsonrpc_server = None

    def register_methods(self, jsonrpc_server):
        """Register MCP methods with JSON-RPC server"""
        self.jsonrpc_server = jsonrpc_server

        jsonrpc_server.register_method("tools/list", self.list_tools)
        jsonrpc_server.register_method("tools/call", self.call_tool)
        jsonrpc_server.register_method("prompts/list", self.list_prompts)
        jsonrpc_server.register_method("prompts/get", self.get_prompt)
        jsonrpc_server.register_method("resources/list", self.list_resources)
        jsonrpc_server.register_method("resources/read", self.read_resource)
        jsonrpc_server.register_method("roots/list", self.list_roots)

    # MCP Tools
    def list_tools(self) -> Dict[str, Any]:
        """List available MCP tools"""
        return {
            "tools": [
                {
                    "name": "write_to_terminal",
                    "description": "Writes text to the active terminal session (like running a command).",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "The command to run or text to write"
                            }
                        },
                        "required": ["command"]
                    }
                },
                {
                    "name": "read_terminal_output",
                    "description": "Reads the output from the active terminal session",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "linesOfOutput": {
                                "type": "number",
                                "description": "How many lines from the bottom to read"
                            }
                        },
                        "required": ["linesOfOutput"]
                    }
                },
                {
                    "name": "send_control_character",
                    "description": "Sends a control character to the active terminal (like Ctrl-C)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "letter": {
                                "type": "string",
                                "description": "Letter for the control char (e.g. 'C' for Ctrl-C)"
                            }
                        },
                        "required": ["letter"]
                    }
                }
            ]
        }

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        if name == "write_to_terminal":
            return self._execute_write_terminal(arguments, loop)
        elif name == "read_terminal_output":
            return self._execute_read_terminal(arguments)
        elif name == "send_control_character":
            return self._execute_send_control(arguments)
        else:
            raise JSONRPCError(-32601, "Method not found", f"Unknown tool '{name}'")

    def _execute_write_terminal(self, arguments: Dict[str, Any], loop: asyncio.AbstractEventLoop) -> Dict[str, Any]:
        """Execute write_to_terminal tool"""
        command = InputValidator.sanitize_command(arguments.get("command", ""))

        executor = CommandExecutor(self.shell)
        async def do_write():
            before_buffer = TtyOutputReader.get_buffer()
            before_lines = len(before_buffer.split("\n"))

            await executor.execute_command(command)

            after_buffer = TtyOutputReader.get_buffer()
            after_lines = len(after_buffer.split("\n"))
            diff = after_lines - before_lines

            msg = (f"{diff} lines were output after sending the command to the terminal. "
                   f"Read the last {diff} lines of terminal contents to orient yourself. "
                   f"Never assume that the command was executed or that it was successful.")
            return msg

        result_msg = loop.run_until_complete(do_write())
        return {
            "content": [{
                "type": "text",
                "text": result_msg
            }]
        }

    def _execute_read_terminal(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute read_terminal_output tool"""
        lines_of_output = InputValidator.validate_lines_of_output(arguments.get("linesOfOutput", 25))
        output = TtyOutputReader.call(lines_of_output)
        return {
            "content": [{
                "type": "text",
                "text": output
            }]
        }

    def _execute_send_control(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute send_control_character tool"""
        letter = InputValidator.validate_control_character(arguments.get("letter", ""))

        sender = SendControlCharacter(self.shell)
        try:
            sender.send(letter)
        except Exception as e:
            raise JSONRPCError(-32603, "Internal error", str(e))

        return {
            "content": [{
                "type": "text",
                "text": f"Sent control character: Control-{letter.upper()}"
            }]
        }

    # MCP Prompts
    def list_prompts(self) -> Dict[str, Any]:
        """List available MCP prompts"""
        return {
            "prompts": [
                {
                    "name": "terminal_help",
                    "description": "Get help with terminal commands and operations",
                    "arguments": []
                },
                {
                    "name": "file_operations",
                    "description": "Common file and directory operations",
                    "arguments": []
                },
                {
                    "name": "system_info",
                    "description": "Get system information and status",
                    "arguments": []
                },
                {
                    "name": "process_management",
                    "description": "Manage running processes",
                    "arguments": []
                }
            ]
        }

    def get_prompt(self, name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get a specific MCP prompt"""
        prompts = {
            "terminal_help": self._get_terminal_help_prompt(),
            "file_operations": self._get_file_operations_prompt(),
            "system_info": self._get_system_info_prompt(),
            "process_management": self._get_process_management_prompt()
        }

        if name not in prompts:
            raise JSONRPCError(-32601, "Method not found", f"Unknown prompt '{name}'")

        return prompts[name]

    def _get_terminal_help_prompt(self) -> Dict[str, Any]:
        """Get terminal help prompt"""
        content = """You are a terminal assistant. Help the user with shell commands and terminal operations.

Available tools:
- write_to_terminal: Execute commands in the terminal
- read_terminal_output: Read terminal output
- send_control_character: Send control characters (like Ctrl+C)

Common commands:
- ls: List files and directories
- cd: Change directory
- pwd: Print working directory
- mkdir: Create directory
- rm: Remove files/directories
- cp: Copy files
- mv: Move/rename files
- cat: Display file contents
- grep: Search for text patterns
- ps: Show running processes
- top/htop: Monitor system resources

When the user asks for help with terminal operations, provide clear explanations and examples."""

        return {
            "description": "Get help with terminal commands and operations",
            "messages": [
                {
                    "role": "system",
                    "content": content
                }
            ]
        }

    def _get_file_operations_prompt(self) -> Dict[str, Any]:
        """Get file operations prompt"""
        content = """You are a file operations assistant. Help with file and directory management.

Common file operations:
- Create files: touch filename
- Edit files: Use terminal editors like nano, vim, or echo redirection
- View files: cat, less, head, tail
- Find files: find /path -name "pattern"
- File permissions: chmod, chown
- Archive files: tar, zip

Directory operations:
- Create: mkdir dirname
- Remove: rmdir (empty) or rm -rf (with contents)
- Navigate: cd path
- List contents: ls -la

Always be careful with destructive operations like rm -rf."""

        return {
            "description": "Common file and directory operations",
            "messages": [
                {
                    "role": "system",
                    "content": content
                }
            ]
        }

    def _get_system_info_prompt(self) -> Dict[str, Any]:
        """Get system info prompt"""
        content = """You are a system information assistant. Help gather system details.

Useful commands:
- uname -a: System information
- df -h: Disk usage
- free -h: Memory usage
- top: Process monitor
- who: Logged in users
- uptime: System uptime
- lscpu: CPU information
- lsblk: Block devices
- ifconfig/ip addr: Network interfaces

Provide clear, organized information about the system's current state."""

        return {
            "description": "Get system information and status",
            "messages": [
                {
                    "role": "system",
                    "content": content
                }
            ]
        }

    def _get_process_management_prompt(self) -> Dict[str, Any]:
        """Get process management prompt"""
        content = """You are a process management assistant. Help with running processes.

Process commands:
- ps aux: List all processes
- top/htop: Interactive process viewer
- kill PID: Terminate a process
- kill -9 PID: Force terminate
- nice: Set process priority
- nohup: Run in background
- jobs: List background jobs
- fg/bg: Foreground/background control

Monitor system resources and manage process lifecycle effectively."""

        return {
            "description": "Manage running processes",
            "messages": [
                {
                    "role": "system",
                    "content": content
                }
            ]
        }

    # MCP Resources
    def list_resources(self) -> Dict[str, Any]:
        """List available MCP resources"""
        # Implementation similar to original
        resources = []

        try:
            import os
            cwd = os.getcwd()
            resources.append({
                "uri": f"file://{cwd}",
                "name": "Current Working Directory",
                "description": f"Current working directory: {cwd}",
                "mimeType": "inode/directory"
            })

            # List some files in current directory
            for item in os.listdir(cwd)[:10]:  # Limit to first 10 items
                item_path = os.path.join(cwd, item)
                if os.path.isfile(item_path):
                    resources.append({
                        "uri": f"file://{item_path}",
                        "name": f"File: {item}",
                        "description": f"File: {item}",
                        "mimeType": "text/plain"
                    })
        except Exception:
            pass  # Ignore errors when listing resources

        # Terminal output resource
        resources.append({
            "uri": "terminal://output",
            "name": "Terminal Output Buffer",
            "description": "Current terminal output buffer",
            "mimeType": "text/plain"
        })

        # System info resource
        resources.append({
            "uri": "system://info",
            "name": "System Information",
            "description": "Basic system information",
            "mimeType": "text/plain"
        })

        return {"resources": resources}

    def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a specific MCP resource"""
        if uri.startswith("file://"):
            file_path = uri[7:]  # Remove "file://" prefix
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {
                    "contents": [{
                        "uri": uri,
                        "mimeType": "text/plain",
                        "text": content
                    }]
                }
            except Exception as e:
                raise JSONRPCError(-32603, "Internal error", f"Cannot read file: {str(e)}")

        elif uri == "terminal://output":
            output = TtyOutputReader.get_buffer()
            return {
                "contents": [{
                    "uri": uri,
                    "mimeType": "text/plain",
                    "text": output
                }]
            }

        elif uri == "system://info":
            try:
                import platform
                import os
                info = f"""System Information:
OS: {platform.system()} {platform.release()}
Platform: {platform.platform()}
Python: {platform.python_version()}
Current Directory: {os.getcwd()}
User: {os.getlogin() if hasattr(os, 'getlogin') else 'Unknown'}
"""
                return {
                    "contents": [{
                        "uri": uri,
                        "mimeType": "text/plain",
                        "text": info
                    }]
                }
            except Exception as e:
                raise JSONRPCError(-32603, "Internal error", f"Cannot get system info: {str(e)}")

        else:
            raise JSONRPCError(-32601, "Method not found", f"Unknown resource URI: {uri}")

    # MCP Roots
    def list_roots(self) -> Dict[str, Any]:
        """List available MCP roots"""
        roots = []

        try:
            import os

            # Current working directory
            cwd = os.getcwd()
            roots.append({
                "uri": f"file://{cwd}",
                "name": "Current Working Directory",
                "description": f"Current working directory: {cwd}"
            })

            # Home directory
            home = os.path.expanduser("~")
            roots.append({
                "uri": f"file://{home}",
                "name": "Home Directory",
                "description": f"User home directory: {home}"
            })

            # System root (if accessible)
            if os.access("/", os.R_OK):
                roots.append({
                    "uri": "file:///",
                    "name": "System Root",
                    "description": "System root directory"
                })

            # Project directory (if we're in a git repo)
            try:
                import subprocess
                result = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                      capture_output=True, text=True, cwd=cwd)
                if result.returncode == 0:
                    project_root = result.stdout.strip()
                    roots.append({
                        "uri": f"file://{project_root}",
                        "name": "Project Root",
                        "description": f"Git project root: {project_root}"
                    })
            except:
                pass  # Git not available or not in repo

        except Exception:
            # Fallback to basic roots
            roots = [{
                "uri": "file:///tmp",
                "name": "Temporary Directory",
                "description": "System temporary directory"
            }]

        return {"roots": roots}

    def handle_chat(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chat request with DeepSeek API integration"""
        from tools.deepseek_client import chat, DeepseekError
        import re

        message = data.get("message", "").strip()
        if not message:
            return {
                "message": "(No message provided)",
                "session_id": "default"
            }

        try:
            # Create conversation with system message
            conversation = [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful AI assistant with terminal access. "
                        "If you need to run a shell command to answer the user, include a line in your assistant message:\n"
                        "CMD: the_command_here\n\n"
                        "The server will intercept that line, run the command, and append the actual output to your final message. "
                        "Only use 'CMD:' if you truly need to run a command."
                    )
                },
                {
                    "role": "user",
                    "content": message
                }
            ]

            # Call DeepSeek API using the robust client
            assistant_message = chat(conversation)

            # Check for CMD: instructions and execute them
            final_message = assistant_message
            if "CMD:" in assistant_message:
                lines = assistant_message.split("\n")
                final_lines = []

                for line in lines:
                    if line.strip().startswith("CMD:"):
                        cmd = line.strip()[len("CMD:"):].strip()
                        if cmd:
                            try:
                                # Execute the command
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)

                                executor = CommandExecutor(self.shell)
                                async def run_cmd():
                                    before_buffer = TtyOutputReader.get_buffer()
                                    before_lines = len(before_buffer.split("\n"))

                                    await executor.execute_command(cmd)

                                    after_buffer = TtyOutputReader.get_buffer()
                                    after_lines = len(after_buffer.split("\n"))
                                    diff = after_lines - before_lines

                                    lines_of_output = diff if diff > 0 else 25
                                    new_output = TtyOutputReader.call(lines_of_output)

                                    # Remove trailing prompt
                                    last_line = new_output.strip().split("\n")[-1]
                                    if re.search(r'(\$|%|#)\s*$', last_line):
                                        splitted = new_output.strip().split("\n")
                                        splitted.pop()
                                        new_output = "\n".join(splitted)

                                    return new_output.strip() or "(No output)"

                                output = loop.run_until_complete(run_cmd())
                                final_lines.append(f"(Ran: {cmd})\n{output}")
                            except Exception as e:
                                final_lines.append(f"(Error running '{cmd}': {e})")
                        else:
                            final_lines.append("(No command specified.)")
                    else:
                        final_lines.append(line)

                final_message = "\n".join(final_lines).strip()

            return {
                "message": final_message,
                "session_id": "default"
            }

        except DeepseekError as e:
            return {
                "message": f"DeepSeek API Error: {str(e)}",
                "session_id": "default"
            }
        except Exception as e:
            return {
                "message": f"Error: {str(e)}",
                "session_id": "default"
            }

    def get_info(self) -> Dict[str, Any]:
        """Get server information"""
        return {
            "name": "term-mcp-deepseek",
            "version": "1.0.0",
            "description": "MCP server for terminal access with DeepSeek AI integration",
            "capabilities": {
                "tools": ["write_to_terminal", "read_terminal_output", "send_control_character"],
                "prompts": ["terminal_help", "file_operations", "system_info", "process_management"],
                "resources": ["file://", "terminal://output", "system://info"],
                "roots": ["current_directory", "home_directory", "system_root", "project_root"]
            },
            "transports": ["http", "stdio"],
            "authentication": ["oauth2"],
            "session_management": True
        }