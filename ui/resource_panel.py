from __future__ import annotations

from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from process.monitor import MonitorSnapshot


class ResourcePanel(Widget):
    DEFAULT_CSS = """
    ResourcePanel {
        height: auto;
        min-height: 5;
        border: solid $secondary;
        padding: 0 1;
    }
    """

    snapshot: reactive[MonitorSnapshot | None] = reactive(None)

    def compose(self):
        yield Static("CPU: --  Mem: --", id="system-stats")
        yield Static("--/-- GB", id="system-mem")
        yield Static("Processes:", id="process-stats-header")
        yield Static("", id="process-stats-body")

    def watch_snapshot(self, snap: MonitorSnapshot | None) -> None:
        if snap is None:
            return
        self.query_one("#system-stats", Static).update(
            f"CPU: {snap.system.cpu_percent:5.1f}%  "
            f"Mem: {snap.system.memory_percent:4.1f}%"
        )
        self.query_one("#system-mem", Static).update(
            f"{snap.system.memory_used_gb:.1f}/{snap.system.memory_total_gb:.1f} GB"
        )
        header = self.query_one("#process-stats-header", Static)
        body = self.query_one("#process-stats-body", Static)
        if not snap.processes:
            header.update("Processes:")
            body.update("  (none)")
            return
        header.update(f"Processes ({len(snap.processes)}):")
        lines = []
        for pid, ps in snap.processes.items():
            lines.append(
                f"  PID {pid:>6}  CPU: {ps.cpu_percent:5.1f}%  "
                f"Mem: {ps.memory_mb:7.1f} MB"
            )
        body.update("\n".join(lines))
