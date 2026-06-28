from __future__ import annotations

from pathlib import Path

from textual import on
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, Static

from process.manager import ProcessManager
from process.runner import LogLine
from process.monitor import MonitorSnapshot, ResourceMonitor
from ui.log_viewer import LogViewer
from ui.process_panel import ProcessPanel
from ui.resource_panel import ResourcePanel


class SaveLogScreen(ModalScreen[str]):
    DEFAULT_CSS = """
    SaveLogScreen {
        align: center middle;
    }
    SaveLogScreen > Vertical {
        width: 60;
        height: auto;
        border: thick $primary;
        padding: 1 2;
        background: $surface;
    }
    """

    def __init__(self, process_id: int, default_name: str) -> None:
        super().__init__()
        self.process_id = process_id
        self.default_name = default_name

    def compose(self):
        yield Vertical(
            Label(f"Save log for process {self.process_id}"),
            Input(value=self.default_name, id="save-path"),
            Label("Press Enter to save, Escape to cancel", classes="dim"),
            id="save-dialog",
        )

    @on(Input.Submitted, "#save-path")
    def on_submit(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class NewTaskScreen(ModalScreen[str]):
    DEFAULT_CSS = """
    NewTaskScreen {
        align: center middle;
    }
    NewTaskScreen > Vertical {
        width: 70;
        height: auto;
        border: thick $primary;
        padding: 1 2;
        background: $surface;
    }
    NewTaskScreen Input {
        width: 100%;
    }
    """

    def compose(self):
        yield Vertical(
            Label("New Task", classes="dialog-title"),
            Input(placeholder="Enter command...", id="cmd-input"),
            Label("Press Enter to run, Escape to cancel", classes="dim"),
            id="new-task-dialog",
        )

    def on_mount(self) -> None:
        self.query_one("#cmd-input", Input).focus()

    @on(Input.Submitted, "#cmd-input")
    def on_submit(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class SudoPasswordScreen(ModalScreen[str | None]):
    DEFAULT_CSS = """
    SudoPasswordScreen {
        align: center middle;
    }
    SudoPasswordScreen > Vertical {
        width: 70;
        height: auto;
        border: thick $primary;
        padding: 1 2;
        background: $surface;
    }
    """

    def __init__(self, command: str) -> None:
        super().__init__()
        self.command = command

    def compose(self):
        yield Vertical(
            Label(f"Sudo password required for:", classes="dialog-title"),
            Label(f"  {self.command}"),
            Input(placeholder="Enter password...", id="sudo-password", password=True),
            Label("Enter to confirm, Escape to skip (command may fail)", classes="dim"),
            id="sudo-password-dialog",
        )

    def on_mount(self) -> None:
        self.query_one("#sudo-password", Input).focus()

    @on(Input.Submitted, "#sudo-password")
    def on_submit(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class Dashboard(Vertical):
    BINDINGS = [
        Binding("n", "new_task", "New Task"),
        Binding("s", "stop_process", "Stop"),
        Binding("r", "restart_process", "Restart"),
        Binding("d", "remove_process", "Remove"),
        Binding("ctrl+s", "save_log", "Save Log"),
        Binding("q", "quit", "Quit"),
    ]

    DEFAULT_CSS = """
    Dashboard {
        height: 1fr;
    }
    #main-area {
        height: 1fr;
        layout: horizontal;
    }
    #process-panel {
        width: 55%;
        min-width: 40;
        border: solid $primary;
        height: 1fr;
    }
    #log-viewer {
        width: 45%;
        min-width: 30;
        border: solid $accent;
        height: 1fr;
    }
    #resource-panel {
        width: 100%;
        height: auto;
        min-height: 5;
        border: solid $secondary;
        dock: bottom;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.manager = ProcessManager()
        self.monitor = ResourceMonitor(interval=1.5)
        self._selected_process_id: int | None = None

    def compose(self):
        yield Header(show_clock=True)
        with Horizontal(id="main-area"):
            yield ProcessPanel(id="process-panel")
            yield LogViewer(id="log-viewer")
        yield ResourcePanel(id="resource-panel")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_process_list()
        self.set_interval(1.0, self._refresh_process_list)
        self.monitor.set_update_callback(self._on_monitor_update)
        self.monitor.start()

    def _refresh_process_list(self) -> None:
        panel = self.query_one("#process-panel", ProcessPanel)
        procs = self.manager.get_all_processes()
        snap = self.monitor.snapshot

        cpu_data: dict[int, float] = {}
        mem_data: dict[int, float] = {}
        for pid, ps in snap.processes.items():
            cpu_data[pid] = ps.cpu_percent
            mem_data[pid] = ps.memory_mb

        panel.update_processes(procs, cpu_data, mem_data)

    def _on_monitor_update(self, snap: MonitorSnapshot) -> None:
        rp = self.query_one("#resource-panel", ResourcePanel)
        rp.snapshot = snap

    def action_new_task(self) -> None:
        self.app.push_screen(NewTaskScreen(), self._handle_new_task)

    def _handle_new_task(self, command: str | None) -> None:
        if command is None:
            return
        cmd = command.strip()
        if not cmd:
            return
        if cmd.startswith("sudo ") or cmd == "sudo":
            self._sudo_cmd = cmd
            self.app.push_screen(SudoPasswordScreen(cmd), self._handle_sudo_task)
        else:
            self._start_process(cmd, None)

    def _handle_sudo_task(self, password: str | None) -> None:
        cmd = self._sudo_cmd
        self._sudo_cmd = None
        self._start_process(cmd, password)

    def _start_process(self, cmd: str, password: str | None) -> None:
        viewer = self.query_one("#log-viewer", LogViewer)

        def on_output_line(pid: int, ll: LogLine) -> None:
            if pid == self._selected_process_id:
                viewer.append_line(ll.text)

        process_id = self.manager.add_process(cmd, on_output_line=on_output_line, password=password)
        info = self.manager.get_process(process_id)
        if info and info.pid:
            self.monitor.track_process(process_id, info.pid, info.start_time)
        self._refresh_process_list()

    @on(ProcessPanel.ProcessHighlighted)
    def on_process_highlighted(self, event: ProcessPanel.ProcessHighlighted) -> None:
        self._selected_process_id = event.process_id
        info = self.manager.get_process(event.process_id)
        if info:
            viewer = self.query_one("#log-viewer", LogViewer)
            viewer.show_log(info)

    def action_stop_process(self) -> None:
        pid = self._get_selected_id()
        if pid is not None:
            self.manager.stop_process(pid)
            self.monitor.untrack_process(pid)
            self._refresh_process_list()

    def action_restart_process(self) -> None:
        pid = self._get_selected_id()
        if pid is not None:
            new_id = self.manager.restart_process(pid)
            if new_id:
                info = self.manager.get_process(new_id)
                if info and info.pid:
                    self.monitor.track_process(new_id, info.pid, info.start_time)
            self.monitor.untrack_process(pid)
            self._refresh_process_list()

    def action_remove_process(self) -> None:
        pid = self._get_selected_id()
        if pid is not None:
            self.monitor.untrack_process(pid)
            self.manager.remove_process(pid)
            self._refresh_process_list()
            viewer = self.query_one("#log-viewer", LogViewer)
            viewer.clear()

    def action_save_log(self) -> None:
        pid = self._get_selected_id()
        if pid is None:
            return
        info = self.manager.get_process(pid)
        if not info:
            return
        default_name = f"process_{pid}_log.txt"
        self.app.push_screen(SaveLogScreen(pid, default_name), self._handle_save_log)

    def _handle_save_log(self, path: str | None) -> None:
        if path is None:
            return
        pid = self._get_selected_id()
        if pid is None:
            return
        self.manager.save_log(pid, path)

    def action_quit(self) -> None:
        self.monitor.stop()
        for proc in self.manager.get_all_processes():
            self.manager.stop_process(proc.id)
        self.app.exit()

    def _get_selected_id(self) -> int | None:
        if self._selected_process_id is not None:
            return self._selected_process_id
        panel = self.query_one("#process-panel", ProcessPanel)
        return panel.get_selected_process_id()