# tools/tty_output_reader.py
import pexpect
import re

ANSI_ESCAPE_PATTERN = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')


class TtyOutputReader:
    """
    Manages a buffer of shell output. We'll do non-blocking reads
    using shell.read_nonblocking(). 
    """

    _buffer = ""

    @staticmethod
    def read_shell_output(shell: pexpect.spawn):
        try:
            while True:
                chunk = shell.read_nonblocking(1024, timeout=0.05)
                if not chunk:
                    break
                # Append chunk
                TtyOutputReader._buffer += chunk
                # Strip ANSI codes and carriage returns
                TtyOutputReader._buffer = ANSI_ESCAPE_PATTERN.sub('', TtyOutputReader._buffer)
                TtyOutputReader._buffer = TtyOutputReader._buffer.replace('\r', '')
        except pexpect.TIMEOUT:
            pass
        except pexpect.EOF:
            pass

    @staticmethod
    def get_buffer() -> str:
        """Return the entire accumulated buffer so far."""
        return TtyOutputReader._buffer

    @staticmethod
    def read_tail(lines_of_output: int) -> str:
        """
        Return the last N lines from _buffer as a string.
        """
        lines = TtyOutputReader._buffer.split("\n")
        tail = lines[-lines_of_output:] if lines_of_output < len(lines) else lines
        return "\n".join(tail)

    @staticmethod
    def clear_buffer():
        """Clear everything if needed."""
        TtyOutputReader._buffer = ""

    @staticmethod
    def call(lines_of_output: int) -> str:
        """
        Convenience method: read the last `lines_of_output` lines from _buffer.
        """
        return TtyOutputReader.read_tail(lines_of_output)
