import time
import asyncio
from tools.tty_output_reader import TtyOutputReader
from tools.process_tracker import ProcessTracker
from tools.utils import sleep

class CommandExecutor:
    def __init__(self, shell):
        """
        :param shell: The pexpect.spawn object representing our shell session
        """
        self.shell = shell

    async def execute_command(self, command: str) -> str:
        """
        Execute the given 'command' in our shell session.
        1) Read leftover output first
        2) Send command
        3) Wait until shell is 'idle' by checking CPU usage
        4) Return entire buffer or new lines
        """
        # read any leftover output first
        TtyOutputReader.read_shell_output(self.shell)
        before_buffer = TtyOutputReader.get_buffer()
        before_len = len(before_buffer.split("\n"))

        # send the command
        self.shell.sendline(command)

        # short delay so output can start showing
        await sleep(0.2)

        # approximate 'processing' wait - watch CPU usage
        tracker = ProcessTracker()
        start_time = time.time()
        while True:
            # read any new shell output
            TtyOutputReader.read_shell_output(self.shell)

            active_process = tracker.get_active_process()
            # If no process or CPU usage < 1, assume idle
            if not active_process or active_process["metrics"]["totalCPUPercent"] < 1:
                # wait a bit for final lines to appear
                await sleep(0.2)
                TtyOutputReader.read_shell_output(self.shell)
                break

            if (time.time() - start_time) > 20:
                # safety cutoff after 20s
                break

            await sleep(0.3)

        # final read
        TtyOutputReader.read_shell_output(self.shell)
        after_buffer = TtyOutputReader.get_buffer()
        after_len = len(after_buffer.split("\n"))
        lines_output = after_len - before_len

        return after_buffer
