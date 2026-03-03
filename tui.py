##
import os
import signal
import sys
import threading
import time
from operator import is_

# --- ANSI Constants ---
ESC = "\033"
CLEAR = f"{ESC}[2J"
HOME = f"{ESC}[H"
RED = f"{ESC}[31m"
RESET = f"{ESC}[0m"
HIDE_CURSOR = f"{ESC}[?25l"
SHOW_CURSOR = f"{ESC}[?25h"
SELECTION_STYLE = f"{ESC}[7m"


class KeyboardListener:
    """
    A cross-platform keyboard listener using only Python standard libraries.
    Works on Windows, Linux, and macOS.
    """

    def __init__(self):

        self.is_windows = sys.platform.startswith("win")

        if not self.is_windows:
            # Linux/macOS uses termios/tty
            import select
            import termios
            import tty

            self.tty = tty
            self.termios = termios
            self.select = select
        else:
            import msvcrt

            self.msvcrt = msvcrt

    def get_key(self):
        if self.is_windows:
            return self._get_key_windows()
        else:
            return self._get_key_unix()

    def _get_key_windows(self):
        """Windows implementation using msvcrt"""

        ch = self.msvcrt.getch()

        if ch in (b"\x00", b"\xe0"):
            seq = self.msvcrt.getch()
            if seq == b"H":
                return "KEY_UP"
            if seq == b"P":
                return "KEY_DOWN"
            if seq == b"K":
                return "KEY_LEFT"
            if seq == b"M":
                return "KEY_RIGHT"
            return f"SPECIAL_{seq}"

        if ch == b"\x08":
            return "KEY_BACKSPACE"

        if ch == b"\r":
            return "KEY_ENTER"
        if ch == b"\n":
            return "KEY_ENTER"

        return ch.decode("utf-8")

    def _get_key_unix(self):
        """
        Reads a single character from standard input without requiring the user
        to press Enter. This blocks execution until a key is pressed.
        """
        # Unix/Linux/macOS implementation
        # We must switch the terminal to 'raw' mode to read 1 byte at a time
        # instead of waiting for a newline (canonical mode).
        fd = sys.stdin.fileno()
        old_settings = self.termios.tcgetattr(fd)
        try:
            self.tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)

            # Handle Escape Sequences (Arrow keys start with ESC \x1b)
            if ch == "\x1b":
                # Check if there are more characters waiting (non-blocking peek)
                # If nothing follows immediately, it was just the ESC key.
                # Setting timeout to 0 makes it instant.
                if self.select.select([sys.stdin], [], [], 0)[0]:
                    # Read the next two characters (expected '[A', '[B', etc.)
                    seq = sys.stdin.read(2)

                    if seq == "[A":
                        return "KEY_UP"
                    if seq == "[B":
                        return "KEY_DOWN"
                    if seq == "[C":
                        return "KEY_RIGHT"
                    if seq == "[D":
                        return "KEY_LEFT"

            if ch == "\x7f":
                return "KEY_BACKSPACE"

            if ch == "\r" or ch == "\n":
                return "KEY_ENTER"

            return ch

        finally:
            # Always restore terminal settings to normal, otherwise the
            # terminal will remain in a weird state after exit.
            self.termios.tcsetattr(fd, self.termios.TCSADRAIN, old_settings)


class ScreenCursor:
    def __init__(self):
        self.pos_y = 1
        self.pos_x = 1
        self.hidden = False

    def write(self, text):
        """Writes text at current cursor position."""

        init_pos_x = self.pos_x
        init_pos_y = self.pos_y
        lines = text.split("\n")

        for line_idx, line in enumerate(lines):
            sys.stdout.write(line)
            self.pos_x += len(line)

            # Move to next line if there are more lines to write
            if line_idx < len(lines) - 1:
                self.pos_y += 1
                self.pos_x = init_pos_x
                self.move_to(self.pos_y, self.pos_x)

        sys.stdout.flush()

    def move_to(self, y, x):
        """Moves cursor to (y, x) position."""
        sys.stdout.write(f"{ESC}[{y};{x}H")
        self.pos_y = y
        self.pos_x = x
        sys.stdout.flush()

    def backspaces(self, n=1):
        """Moves cursor back by n columns."""
        self.pos_x -= n
        sys.stdout.write(f"{ESC}[{n}D")
        sys.stdout.flush()

    def deletes(self, n=1):
        """Deletes n characters at current cursor position."""
        sys.stdout.write(f"{ESC}[{n}P")
        sys.stdout.flush()

    def lines_down(self, n=1):
        """Moves cursor down by n lines."""
        self.pos_y += n
        sys.stdout.write(f"{ESC}[{n}B")

    def lines_up(self, n=1):
        """Moves cursor up by n lines."""
        self.pos_y -= n
        sys.stdout.write(f"{ESC}[{n}A")

    def hide(self, set=None):
        if set is None:
            self.hidden = not self.hidden
        else:
            self.hidden = set

        if self.hidden:
            sys.stdout.write(HIDE_CURSOR)
        else:
            sys.stdout.write(SHOW_CURSOR)
        sys.stdout.flush()

    def quit(self):
        """Restores cursor visibility and exits."""
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.write(RESET)
        sys.stdout.write(CLEAR)
        sys.stdout.write(HOME)
        sys.stdout.flush()
        print("Goodbye!")


class TUI(threading.Thread):
    def __init__(self, fastReader) -> None:
        super().__init__()
        self.kbListener = KeyboardListener()
        self.cursor = ScreenCursor()
        if hasattr(signal, "SIGWINCH"):
            signal.signal(signal.SIGWINCH, self.on_resize)
        signal.signal(signal.SIGINT, self.on_exit)

        self.fastReader = fastReader

        self.running = True
        self.reloadRequired = False
        self.requestedInput = False
        self.userInputResult = None
        self.mode = "NORMAL"
        self.input_buffer = ""

    def close(self):
        self.running = False
        self.join()

    def quit(self):
        self.running = False
        self.fastReader.stop()

    def get_size(self):
        """Returns terminal size as (rows, cols)."""
        return os.get_terminal_size().lines, os.get_terminal_size().columns

    def on_resize(self, signum, frame):
        # Handle terminal resize events if needed
        self.reloadRequired = True

    def on_exit(self, signum, frame):
        self.cursor.quit()
        sys.exit(0)

    def paint_screen(self):
        self.cursor.write(CLEAR)
        self.cursor.move_to(1, 1)
        rows, cols = self.get_size()

        # draw border

        self.cursor.write(f"+{'-' * (cols - 2)}+\n")
        for _ in range(rows - 2):
            self.cursor.write(f"|{' ' * (cols - 2)}|\n")
        self.cursor.write(f"+{'-' * (cols - 2)}+\n")

        self.cursor.move_to(rows - 1, 3)
        if self.mode == "NORMAL":
            self.cursor.write("Load URL: i | Clear: c | Reading: r | Quit: q")
        elif self.mode == "INPUT":
            self.cursor.write("--INSERT--")
        elif self.mode == "READ":
            self.cursor.write(
                "--READING--   pause: space | next <p>: -> | prev <p>: <- | change speed: arrows-up/down | back: q"
            )

        # self.cursor.write(f"{RED}+{'-' * (cols//3)}+{'-' * (cols -3- cols//3)}+{RESET}\n")
        # for _ in range(rows - 8):
        #    self.cursor.write(f"{RED}|{RESET}{' ' * (cols//3)}{RED}|{RESET}{' ' * (cols -3- cols//3)}{RED}|{RESET}\n")
        # self.cursor.write(f"{RED}+{' ' * (cols//3)}+{'-' * (cols -3- cols//3)}+{RESET}\n")
        # for _ in range(5):
        #    self.cursor.write(f"{RED}|{RESET}{' ' * (cols//3)}{RED}|{RESET}{' ' * (cols -3- cols//3)}{RED}|{RESET}\n")
        # self.cursor.write(f"{RED}+{'-' * (cols//3)}+{'-' * (cols -3- cols//3)}+{RESET}\n")

    def getUserInput(self, prompt: str) -> str:
        self.requestedInput = True
        self.mode = "INPUT"
        self.paint_screen()
        self.cursor.move_to(5, 5)
        self.cursor.write(prompt)
        while self.userInputResult is None:
            time.sleep(0.1)
        result = self.userInputResult
        self.userInputResult = None
        self.requestedInput = False
        self.paint_screen()
        return result

    def put_word(self, word: str) -> None:
        size = self.get_size()
        self.cursor.move_to(size[0] // 2, 1)
        self.cursor.write(" " * (size[1] - 2))
        self.cursor.move_to(size[0] // 2, (size[1] - len(word)) // 2)
        self.cursor.write(word)

    def run(self) -> None:
        self.cursor.hide(True)
        self.cursor.write(CLEAR)
        self.cursor.move_to(1, 1)
        self.paint_screen()
        self.cursor.move_to(3, 5)
        self.cursor.write("TUI Started. Press 'q' to quit.\n")
        self.cursor.write(
            f"{RED}Terminal Size: {self.get_size()[0]} rows x {self.get_size()[1]} cols{RESET}\n"
        )

        self.cursor.hide(False)

        while self.running:
            key = self.kbListener.get_key()

            if self.requestedInput:
                self.mode = "INPUT"

            if self.mode == "INPUT":
                if key == "KEY_ENTER":
                    self.userInputResult = self.input_buffer
                    self.input_buffer = ""
                    self.mode = "NORMAL"
                elif key == "KEY_BACKSPACE":
                    if len(self.input_buffer) > 0:
                        self.input_buffer = self.input_buffer[:-1]
                        self.cursor.backspaces()
                        self.cursor.deletes()
                else:
                    self.input_buffer += key
                    self.cursor.write(key)

            elif self.mode == "NORMAL":
                if key == "q":
                    self.quit()
                elif key == "i":
                    self.fastReader.url_request()
                elif key == "c":
                    self.reloadRequired = True
                elif key == "d":
                    self.fastReader.dump()
                elif key == "r":
                    self.mode = "READ"
                    self.fastReader.pause(True)
                    self.cursor.hide(True)
                    self.reloadRequired = True

            elif self.mode == "READ":
                if key == "q":
                    self.mode = "NORMAL"
                    self.fastReader.pause(False)
                    self.cursor.hide(False)
                    self.reloadRequired = True
                if key == "KEY_UP":
                    self.fastReader.speed_up()
                if key == "KEY_DOWN":
                    self.fastReader.speed_down()
                if key == "KEY_LEFT":
                    self.fastReader.p_back()
                if key == "KEY_RIGHT":
                    self.fastReader.p_forward()
                if key == " ":
                    self.fastReader.pause()

            if self.reloadRequired:
                self.paint_screen()
                self.reloadRequired = False
        self.cursor.quit()


# EOF
