from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Callable

import psutil

logger = logging.getLogger("process_manager.monitor")


@dataclass
class ProcessStats:
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    runtime: float = 0.0


@dataclass
class SystemStats:
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_gb: float = 0.0
    memory_total_gb: float = 0.0


@dataclass
class MonitorSnapshot:
    system: SystemStats = field(default_factory=SystemStats)
    processes: dict[int, ProcessStats] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.monotonic)


class ResourceMonitor:
    def __init__(self, interval: float = 1.0) -> None:
        self.interval = interval
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._snapshot = MonitorSnapshot()
        self._on_update: Callable[[MonitorSnapshot], None] | None = None
        self._tracked_pids: dict[int, int] = {}
        self._process_start_times: dict[int, float] = {}

    def set_update_callback(self, callback: Callable[[MonitorSnapshot], None]) -> None:
        self._on_update = callback

    def track_process(self, process_id: int, pid: int, start_time: float) -> None:
        self._tracked_pids[process_id] = pid
        self._process_start_times[process_id] = start_time
        try:
            p = psutil.Process(pid)
            p.cpu_percent()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    def untrack_process(self, process_id: int) -> None:
        self._tracked_pids.pop(process_id, None)
        self._process_start_times.pop(process_id, None)

    @property
    def snapshot(self) -> MonitorSnapshot:
        return self._snapshot

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.get_event_loop().create_task(self._monitor_loop())
        logger.info("Resource monitor started (interval=%.1fs)", self.interval)

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Resource monitor stopped")

    async def _monitor_loop(self) -> None:
        psutil.cpu_percent(interval=0)
        while self._running:
            try:
                snap = self._take_snapshot()
                self._snapshot = snap
                if self._on_update:
                    self._on_update(snap)
            except Exception:
                logger.exception("Error in monitor snapshot")
            await asyncio.sleep(self.interval)

    def _take_snapshot(self) -> MonitorSnapshot:
        system = SystemStats(
            cpu_percent=psutil.cpu_percent(interval=0),
        )
        mem = psutil.virtual_memory()
        system.memory_percent = mem.percent
        system.memory_used_gb = mem.used / (1024**3)
        system.memory_total_gb = mem.total / (1024**3)

        procs: dict[int, ProcessStats] = {}
        now = time.monotonic()
        for process_id, pid in self._tracked_pids.items():
            ps = ProcessStats()
            try:
                p = psutil.Process(pid)
                ps.cpu_percent = p.cpu_percent()
                ps.memory_mb = p.memory_info().rss / (1024**2)
                start = self._process_start_times.get(process_id, now)
                ps.runtime = now - start
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                ps.cpu_percent = 0.0
                ps.memory_mb = 0.0
            procs[process_id] = ps

        return MonitorSnapshot(system=system, processes=procs)
