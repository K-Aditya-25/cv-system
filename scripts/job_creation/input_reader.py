from __future__ import annotations

import sys, termios, tty

from .constants import CTRL_Q, PASTE_END_MARKER
from .errors import InteractiveQuit

def read_multiline_input(prompt: str, end_marker: str = PASTE_END_MARKER) -> str:
    print(prompt)
    print(
        f"Paste text below, then type {end_marker} on its own line and press Enter. "
        "Press Ctrl-Q to exit."
    )
    if sys.stdin.isatty():
        return read_multiline_input_from_tty(end_marker)

    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if CTRL_Q in line:
            raise InteractiveQuit()
        if line.strip() == end_marker:
            break
        lines.append(line)
    return "\n".join(lines).strip()


def read_multiline_input_from_tty(end_marker: str) -> str:
    fd = sys.stdin.fileno()
    original_attrs = termios.tcgetattr(fd)
    attrs = termios.tcgetattr(fd)
    if hasattr(termios, "IXON"):
        attrs[0] &= ~termios.IXON
    if hasattr(termios, "IXOFF"):
        attrs[0] &= ~termios.IXOFF
    lines: list[str] = []
    current_line: list[str] = []

    try:
        termios.tcsetattr(fd, termios.TCSADRAIN, attrs)
        tty.setcbreak(fd)
        while True:
            char = sys.stdin.read(1)
            if char == CTRL_Q:
                print("^Q")
                raise InteractiveQuit()
            if char in ("\r", "\n"):
                line = "".join(current_line)
                print()
                if line.strip() == end_marker:
                    break
                lines.append(line)
                current_line = []
                continue
            if char in ("\x7f", "\b"):
                if current_line:
                    current_line.pop()
                    print("\b \b", end="", flush=True)
                continue
            if char == "\x03":
                raise KeyboardInterrupt()
            current_line.append(char)
            print(char, end="", flush=True)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, original_attrs)

    return "\n".join(lines).strip()

