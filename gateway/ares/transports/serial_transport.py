"""USB serial transport: one reader thread per COM port, NDJSON both ways.

The gateway learns which node lives on which port from the first valid message it sees
there, so ports can be listed in any order on the command line."""
from __future__ import annotations

import asyncio
import json
import threading
import time

import serial  # pyserial

from .base import Transport


class SerialTransport(Transport):
    name = "serial"

    def __init__(self, ports: list[str], baud: int = 115200) -> None:
        super().__init__()
        self.ports = ports
        self.baud = baud
        self._handles: dict[str, serial.Serial] = {}
        self._port_of_node: dict[str, str] = {}
        self._threads: list[threading.Thread] = []
        self._running = False

    async def start(self, loop: asyncio.AbstractEventLoop) -> None:
        await super().start(loop)
        self._running = True
        for port in self.ports:
            try:
                handle = serial.Serial(port, self.baud, timeout=1)
            except serial.SerialException as exc:  # pragma: no cover - hardware
                print(f"[serial] cannot open {port}: {exc}")
                continue
            self._handles[port] = handle
            thread = threading.Thread(target=self._reader, args=(port, handle), daemon=True)
            thread.start()
            self._threads.append(thread)
            print(f"[serial] listening on {port} @ {self.baud}")

    async def stop(self) -> None:
        self._running = False
        for handle in self._handles.values():
            try:
                handle.close()
            except Exception:
                pass

    def nodes(self) -> list[str]:
        return list(self._port_of_node)

    def _reader(self, port: str, handle: serial.Serial) -> None:
        buffer = b""
        while self._running:
            try:
                chunk = handle.readline()
            except Exception:
                time.sleep(0.5)
                continue
            if not chunk:
                continue
            buffer += chunk
            if not buffer.endswith(b"\n"):
                continue
            line = buffer.decode("utf-8", errors="replace").strip()
            buffer = b""
            if not line.startswith("{"):
                # boot logs and debug prints from the board are ignored
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            node_id = msg.get("node_id")
            if node_id and self._port_of_node.get(node_id) != port:
                self._port_of_node[node_id] = port
                print(f"[serial] node {node_id} is on {port}")
            if self.loop is not None:
                asyncio.run_coroutine_threadsafe(self._deliver(msg, f"serial:{port}"), self.loop)

    async def send(self, node_id: str, msg: dict) -> bool:
        port = self._port_of_node.get(node_id)
        handle = self._handles.get(port) if port else None
        if handle is None:
            return False
        line = (json.dumps(msg, separators=(",", ":")) + "\n").encode("utf-8")
        try:
            handle.write(line)
            return True
        except Exception as exc:  # pragma: no cover - hardware
            print(f"[serial] write to {node_id} failed: {exc}")
            return False
