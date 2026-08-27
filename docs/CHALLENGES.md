# Receipt and safety mini-challenges

These challenges are contribution prompts, not permission to run risky commands. Use a disposable temporary repository and stay in `inspect` mode.

## 1. Smallest useful repository recipe

Create one recipe that answers a concrete repository question in at most three read-only steps. It must validate, execute in CI, and produce low-risk receipts with no network access.

## 2. Receipt tamper detector

Add a regression test that changes exactly one receipt field and proves signature verification fails while the error remains privacy-safe. Do not weaken or replace HMAC verification.

## 3. Sandbox escape fixture

Create a safe test fixture for one path, symlink, shell-composition, output, timeout, or cross-session escape attempt. The test must prove the attempt is denied and must not access real private files.

Open an issue before a larger challenge. Include the threat being tested, the harmless fixture, the expected policy decision, and the test command. Never submit destructive payloads, real secrets, or host-wide scans.
