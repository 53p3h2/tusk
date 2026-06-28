from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Callable

from utils.helpers import ProcessStatus

logger = logging.getLogger("process_manager.runner")


@dataclass
class LogLine:
    text: str
    stream: str  # "stdout" or "stderr"

    def __str__(self) -> str:
        return self.text


@dataclass
class ProcessInfo:
    id: int
    command: str
    status: ProcessStatus = ProcessStatus.RUNNING
    pid: int | None = None
    start_time: float = field(default_factory=time.monotonic)
    end_time: float | None = None
    exit_code: int | None = None
    log_lines: list[LogLine] = field(default_factory=list)

    @property
    def runtime(self) -> float:
        end = self.end_time if self.end_time is not None else time.monotonic()
        return end - self.start_time


class ProcessRunner:
    def __init__(
        self,
        process_id: int,
        command: str,
        on_output: Callable[[int, LogLine], None] | None = None,
        on_exit: Callable[[int, int | None], None] | None = None,
        password: str | None = None,
    ):
        self.process_id = process_id
        self.command = command
        self.on_output = on_output
        self.on_exit = on_exit
        self.password = password
        self._process: asyncio.subprocess.Process | None = None
        self._task: asyncio.Task[None] | None = None

    async def _read_stream(
        self,
        stream: asyncio.StreamReader | None,
        tag: str,
        info: ProcessInfo,
    ) -> None:
        if stream is None:
            return
        while True:
            line_bytes = await stream.readline()
            if not line_bytes:
                break
            line = line_bytes.decode("utf-8", errors="replace").rstrip("\n\r")
            log_line = LogLine(text=line, stream=tag)
            info.log_lines.append(log_line)
            if self.on_output:
                self.on_output(self.process_id, log_line)

    async def run(self) -> ProcessInfo:
        info = ProcessInfo(id=self.process_id, command=self.command)
        try:
            stdin_pipe = self.password is not None
            cmd = self.command
            if self.password:
                if cmd.startswith("sudo "):
                    cmd = "sudo -S" + cmd[4:]
                elif cmd == "sudo":
                    cmd = "sudo -S"

            self._process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE if stdin_pipe else asyncio.subprocess.DEVNULL,
            )
            info.pid = self._process.pid
            logger.info("Started process %d (pid=%d): %s", self.process_id, info.pid, cmd)

            if self.password and self._process.stdin:
                self._process.stdin.write((self.password + "\n").encode())
                await self._process.stdin.drain()
                self._process.stdin.close()
                self.password = None

            await asyncio.gather(
                self._read_stream(self._process.stdout, "stdout", info),
                self._read_stream(self._process.stderr, "stderr", info),
            )

            await self._process.wait()
            info.exit_code = self._process.returncode
            if info.exit_code == 0:
                info.status = ProcessStatus.COMPLETED
            else:
                info.status = ProcessStatus.FAILED
            logger.info(
                "Process %d exited with code %d (%s)",
                self.process_id,
                info.exit_code,
                info.status.value,
            )

        except asyncio.CancelledError:
            info.status = ProcessStatus.TERMINATED
            logger.info("Process %d was terminated", self.process_id)
        except Exception as exc:
            info.status = ProcessStatus.FAILED
            info.log_lines.append(LogLine(text=f"Error: {exc}", stream="stderr"))
            logger.exception("Process %d failed unexpectedly", self.process_id)
        finally:
            info.end_time = time.monotonic()
            if self.on_exit:
                self.on_exit(self.process_id, info.exit_code)
        return info

    def start(self) -> ProcessInfo:
        """Kick off the process run as a background task. Returns a stub ProcessInfo."""
        import functools

        info = ProcessInfo(id=self.process_id, command=self.command)
        self._task = asyncio.get_event_loop().create_task(self._run_and_store(info))
        return info

    async def _run_and_store(self, info: ProcessInfo) -> None:
        result = await self.run()
        info.status = result.status
        info.pid = result.pid
        info.exit_code = result.exit_code
        info.end_time = result.end_time
        info.log_lines = result.log_lines
        info.start_time = result.start_time

    def stop(self) -> None:
        if self._process and self._process.returncode is None:
            self._process.terminate()
            try:
                self._process.kill()
            except ProcessLookupError:
                pass

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.returncode is None
