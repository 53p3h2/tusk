from __future__ import annotations

import re

from rich.text import Text
from textual.widgets import RichLog

from process.runner import LogLine, ProcessInfo


class LogViewer(RichLog):
    DEFAULT_CSS = """
    LogViewer {
        border: solid $accent;
        min-height: 8;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.wrap = True
        self.highlight = False
        self.markup = False

    def show_log(self, process_info: ProcessInfo) -> None:
        self.clear()
        if not process_info.log_lines:
            self.write(Text("(no output)", style="dim"))
            return
        for line in process_info.log_lines:
            self._write_line(line.text)

    def append_line(self, text: str) -> None:
        self._write_line(text)

    def _write_line(self, text: str) -> None:
        error_patterns = [
            r"error",
            r"fatal",
            r"panic",
            r"exception",
            r"traceback",
            r"failed",
            r"permission denied",
            r"no such file",
        ]
        styled = Text(text)
        lower = text.lower()
        for pat in error_patterns:
            if re.search(pat, lower):
                styled.stylize("bold red")
                break
        else:
            if "warning" in lower or "warn" in lower:
                styled.stylize("yellow")
        self.write(styled)

    def save_to_file(self, path: str, process_info: ProcessInfo) -> None:
        with open(path, "w") as f:
            f.write(f"Command: {process_info.command}\n")
            f.write(f"Status: {process_info.status.value}\n")
            f.write(f"Exit Code: {process_info.exit_code}\n")
            f.write("-" * 60 + "\n")
            for line in process_info.log_lines:
                f.write(line.text + "\n")
