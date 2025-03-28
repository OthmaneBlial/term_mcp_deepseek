import re
import time

class SendControlCharacter:
    def __init__(self, shell):
        self.shell = shell

    def send(self, letter: str):
        """
        Send a control character, e.g. letter='C' => Ctrl-C
        """
        letter = letter.upper()
        if not re.match(r'^[A-Z]$', letter):
            raise ValueError("Invalid control character letter (must be A-Z).")
        ctrl_code = chr(ord(letter) - 64)  # 'C' => 3
        self.shell.send(ctrl_code)
        # small delay
        time.sleep(0.2)
