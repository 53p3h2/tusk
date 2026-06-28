from __future__ import annotations

from rich.text import Text
from textual import on
from textual.message import Message
from textual.widgets import DataTable

from process.runner import ProcessInfo
from utils.helpers import ProcessStatus, STATUS_COLORS, format_duration


class ProcessSelected(Message):
    def __init__(self, process_id: int) -> None:
        super().__init__()
        self.process_id = process_id


class ProcessPanel(DataTable):
    class ProcessHighlighted(Message):
        def __init__(self, process_id: int) -> None:
            super().__init__()
            self.process_id = process_id

    def __init__(self, **kwargs) -> None:
        super().__init__(cursor_type="row", **kwargs)
        self._process_ids: dict[int, int] = {}

    def compose(self):
        yield from super().compose()

    def on_mount(self) -> None:
        self.add_columns("PID", "Command", "Status", "Runtime", "Exit", "CPU%", "Mem(MB)")

    def update_processes(self, processes: list[ProcessInfo], cpu_data: dict[int, float] | None = None, mem_data: dict[int, float] | None = None) -> None:
        cpu_data = cpu_data or {}
        mem_data = mem_data or {}

        existing_keys = set(self._process_ids.keys())
        new_keys = {p.id for p in processes}

        for p in processes:
            status_text = Text(p.status.value, style=STATUS_COLORS.get(p.status, ""))
            cpu = cpu_data.get(p.id, 0.0)
            mem = mem_data.get(p.id, 0.0)
            runtime = format_duration(p.runtime)
            exit_str = str(p.exit_code) if p.exit_code is not None else "-"

            if p.id in self._process_ids:
                row_idx = self._process_ids[p.id]
                try:
                    self.update_cell_at((row_idx, 0), str(p.pid or "-"))
                    self.update_cell_at((row_idx, 1), p.command[:40])
                    self.update_cell_at((row_idx, 2), status_text)
                    self.update_cell_at((row_idx, 3), runtime)
                    self.update_cell_at((row_idx, 4), exit_str)
                    self.update_cell_at((row_idx, 5), f"{cpu:.1f}")
                    self.update_cell_at((row_idx, 6), f"{mem:.1f}")
                except Exception:
                    pass
            else:
                row_idx = self.row_count
                self.add_row(
                    str(p.pid or "-"),
                    p.command[:40],
                    status_text,
                    runtime,
                    exit_str,
                    f"{cpu:.1f}",
                    f"{mem:.1f}",
                    key=str(p.id),
                )
                self._process_ids[p.id] = row_idx

        removed = existing_keys - new_keys
        for pid in removed:
            row_idx = self._process_ids.pop(pid, None)
            if row_idx is not None:
                try:
                    self.remove_row(row_idx)
                except Exception:
                    pass

    def get_selected_process_id(self) -> int | None:
        if self.cursor_row is None:
            return None
        for pid, row_idx in self._process_ids.items():
            if row_idx == self.cursor_row:
                return pid
        return None

    @on(DataTable.RowHighlighted)
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        pid = self.get_selected_process_id()
        if pid is not None:
            self.post_message(self.ProcessHighlighted(pid))
