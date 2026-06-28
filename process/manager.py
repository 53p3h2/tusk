from __future__ import annotations

import asyncio
import logging
from typing import Callable

from process.runner import LogLine, ProcessInfo, ProcessRunner
from utils.helpers import ProcessStatus

logger = logging.getLogger("process_manager.manager")


class ProcessManager:
    def __init__(self) -> None:
        self._next_id: int = 1
        self._runners: dict[int, ProcessRunner] = {}
        self._processes: dict[int, ProcessInfo] = {}
        self._on_update: Callable[[], None] | None = None

    def set_update_callback(self, callback: Callable[[], None]) -> None:
        self._on_update = callback

    def _notify(self) -> None:
        if self._on_update:
            self._on_update()

    def add_process(
        self,
        command: str,
        on_output_line: Callable[[int, LogLine], None] | None = None,
        password: str | None = None,
    ) -> int:
        process_id = self._next_id
        self._next_id += 1

        def on_output(pid: int, log_line: "LogLine") -> None:
            self._notify()
            if on_output_line:
                on_output_line(pid, log_line)

        def on_exit(pid: int, exit_code: int | None) -> None:
            self._notify()

        runner = ProcessRunner(process_id, command, on_output=on_output, on_exit=on_exit, password=password)
        info = runner.start()
        self._runners[process_id] = runner
        self._processes[process_id] = info
        self._notify()
        logger.info("Added process %d: %s", process_id, command)
        return process_id

    def stop_process(self, process_id: int) -> None:
        runner = self._runners.get(process_id)
        if runner:
            runner.stop()
            info = self._processes.get(process_id)
            if info and info.status == ProcessStatus.RUNNING:
                info.status = ProcessStatus.TERMINATED
            self._notify()
            logger.info("Stopped process %d", process_id)

    def restart_process(self, process_id: int) -> int | None:
        old_info = self._processes.get(process_id)
        if not old_info:
            return None
        self.stop_process(process_id)
        new_id = self.add_process(old_info.command)
        logger.info("Restarted process %d as %d", process_id, new_id)
        return new_id

    def remove_process(self, process_id: int) -> None:
        self.stop_process(process_id)
        self._runners.pop(process_id, None)
        self._processes.pop(process_id, None)
        self._notify()
        logger.info("Removed process %d", process_id)

    def get_process(self, process_id: int) -> ProcessInfo | None:
        return self._processes.get(process_id)

    def get_all_processes(self) -> list[ProcessInfo]:
        return list(self._processes.values())

    def save_log(self, process_id: int, path: str) -> None:
        info = self._processes.get(process_id)
        if not info:
            return
        with open(path, "w") as f:
            f.write(f"Command: {info.command}\n")
            f.write(f"Status: {info.status.value}\n")
            f.write(f"Exit Code: {info.exit_code}\n")
            f.write(f"Runtime: {info.runtime:.1f}s\n")
            f.write("-" * 60 + "\n")
            for line in info.log_lines:
                f.write(line.text + "\n")
        logger.info("Saved log for process %d to %s", process_id, path)
