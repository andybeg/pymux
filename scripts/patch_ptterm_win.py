from __future__ import annotations

import importlib.util
from pathlib import Path


def _replace_or_raise(text: str, old: str, new: str, file_path: Path) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"Expected snippet not found in {file_path}: {old!r}")
    return text.replace(old, new, 1)


def patch_win32_py(base: Path) -> None:
    file_path = base / "backends" / "win32.py"
    file_path.write_text(
        """from concurrent.futures import Future
from threading import Thread
import asyncio

from winpty import PTY

from .base import Backend

__all__ = [
    "Win32Backend",
]


class Win32Backend(Backend):
    \"\"\"
    Terminal backend for Windows using pywinpty PTY API directly.
    \"\"\"

    def __init__(self):
        self.pty = PTY(120, 30)
        self.ready_f = Future()
        self._input_ready_callbacks = []
        self._buffer = []
        self._reader_enabled = False
        self._reader_started = False
        self.loop = None

    def add_input_ready_callback(self, callback):
        self._input_ready_callbacks.append(callback)
        if self._buffer and self._reader_enabled:
            callback()

    def read_text(self, amount):
        result = "".join(self._buffer)
        self._buffer = []
        return result

    def write_text(self, text):
        self.pty.write(text)

    def connect_reader(self):
        self._reader_enabled = True

    def disconnect_reader(self):
        self._reader_enabled = False

    @property
    def closed(self):
        return self.ready_f.done()

    def set_size(self, width, height):
        self.pty.set_size(width, height)

    def start(self):
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.get_event_loop_policy().get_event_loop()

        self.pty.spawn(r"C:\\windows\\system32\\cmd.exe")
        if not self._reader_started:
            self._reader_started = True
            Thread(target=self._reader_thread, daemon=True).start()

    def _reader_thread(self):
        while self.pty.isalive():
            data = self.pty.read(True)
            if data:
                self.loop.call_soon_threadsafe(self._on_data, data)

        self.loop.call_soon_threadsafe(self._mark_done)

    def _on_data(self, data):
        self._buffer.append(data)
        if self._reader_enabled:
            for cb in self._input_ready_callbacks:
                cb()

    def _mark_done(self):
        if not self.ready_f.done():
            self.ready_f.set_result(None)

    def kill(self):
        self.pty.cancel_io()

    def get_name(self):
        return "cmd.exe"

    def get_cwd(self):
        return
""",
        encoding="utf-8",
    )


def patch_win32_pipes_py(base: Path) -> None:
    file_path = base / "backends" / "win32_pipes.py"
    text = file_path.read_text(encoding="utf-8")

    text = _replace_or_raise(
        text,
        "ERROR_BROKEN_PIPE = 109\n",
        "ERROR_BROKEN_PIPE = 109\nERROR_PIPE_BUSY = 231\nWAIT_TIMEOUT_MS = 5000\n",
        file_path,
    )

    text = _replace_or_raise(
        text,
        "        self.handle = windll.kernel32.CreateFileW(\n"
        "            pipe_name, GENERIC_READ, 0, None, OPEN_EXISTING, FILE_FLAG_OVERLAPPED, None\n"
        "        )\n"
        "\n"
        "        if self.handle == INVALID_HANDLE_VALUE:\n"
        "            error_code = windll.kernel32.GetLastError()\n"
        "            raise Exception(\"Invalid pipe handle. Error code=%r.\" % error_code)\n",
        "        self.handle = self._open_pipe(pipe_name)\n",
        file_path,
    )

    text = _replace_or_raise(
        text,
        "        self._event = windll.kernel32.CreateEventA(\n"
        "            None,  # Default security attributes.\n"
        "            BOOL(True),  # Manual reset event.\n"
        "            BOOL(True),  # initial state = signaled.\n"
        "            None,  # Unnamed event object.\n"
        "        )\n"
        "        self._overlapped.hEvent = self._event\n",
        "        self._event = windll.kernel32.CreateEventA(\n"
        "            None,  # Default security attributes.\n"
        "            BOOL(True),  # Manual reset event.\n"
        "            BOOL(True),  # initial state = signaled.\n"
        "            None,  # Unnamed event object.\n"
        "        )\n"
        "        self._event = HANDLE(self._event)\n"
        "        self._overlapped.hEvent = self._event\n",
        file_path,
    )

    text = _replace_or_raise(
        text,
        "        # Start reader coroutine.\n        ensure_future(self._async_reader())\n",
        "        # Start reader coroutine.\n        ensure_future(self._async_reader())\n\n"
        "    def _open_pipe(self, pipe_name):\n"
        "        while True:\n"
        "            handle = windll.kernel32.CreateFileW(\n"
        "                pipe_name,\n"
        "                GENERIC_READ,\n"
        "                0,\n"
        "                None,\n"
        "                OPEN_EXISTING,\n"
        "                FILE_FLAG_OVERLAPPED,\n"
        "                None,\n"
        "            )\n"
        "\n"
        "            if handle != INVALID_HANDLE_VALUE:\n"
        "                return handle\n"
        "\n"
        "            error_code = windll.kernel32.GetLastError()\n"
        "            if error_code == ERROR_PIPE_BUSY:\n"
        "                if not windll.kernel32.WaitNamedPipeW(pipe_name, DWORD(WAIT_TIMEOUT_MS)):\n"
        "                    raise Exception(\"Invalid pipe handle. Error code=%r.\" % error_code)\n"
        "                continue\n"
        "\n"
        "            raise Exception(\"Invalid pipe handle. Error code=%r.\" % error_code)\n",
        file_path,
    )

    text = _replace_or_raise(
        text,
        "        def ready() -> None:\n"
        "            get_event_loop().remove_win32_handle(self._event)\n"
        "            f.set_result(None)\n"
        "\n"
        "        get_event_loop().add_win32_handle(self._event, ready)\n",
        "        def ready() -> None:\n"
        "            get_event_loop().remove_win32_handle(self._event)\n"
        "            f.set_result(None)\n"
        "\n"
        "        if isinstance(self._event, int):\n"
        "            self._event = HANDLE(self._event)\n"
        "\n"
        "        get_event_loop().add_win32_handle(self._event, ready)\n",
        file_path,
    )

    text = _replace_or_raise(
        text,
        "        self.handle = windll.kernel32.CreateFileW(\n"
        "            pipe_name, GENERIC_WRITE, 0, None, OPEN_EXISTING, 0, None\n"
        "        )\n"
        "\n"
        "        if self.handle == INVALID_HANDLE_VALUE:\n"
        "            error_code = windll.kernel32.GetLastError()\n"
        "            raise Exception(\"Invalid stdin handle code=%r\" % error_code)\n",
        "        self.handle = self._open_pipe(pipe_name)\n\n"
        "    def _open_pipe(self, pipe_name):\n"
        "        while True:\n"
        "            handle = windll.kernel32.CreateFileW(\n"
        "                pipe_name,\n"
        "                GENERIC_WRITE,\n"
        "                0,\n"
        "                None,\n"
        "                OPEN_EXISTING,\n"
        "                0,\n"
        "                None,\n"
        "            )\n"
        "\n"
        "            if handle != INVALID_HANDLE_VALUE:\n"
        "                return handle\n"
        "\n"
        "            error_code = windll.kernel32.GetLastError()\n"
        "            if error_code == ERROR_PIPE_BUSY:\n"
        "                if not windll.kernel32.WaitNamedPipeW(pipe_name, DWORD(WAIT_TIMEOUT_MS)):\n"
        "                    raise Exception(\"Invalid stdin handle code=%r\" % error_code)\n"
        "                continue\n"
        "\n"
        "            raise Exception(\"Invalid stdin handle code=%r\" % error_code)\n",
        file_path,
    )

    file_path.write_text(text, encoding="utf-8")


def patch_process_py(base: Path) -> None:
    file_path = base / "process.py"
    text = file_path.read_text(encoding="utf-8")

    text = _replace_or_raise(
        text,
        "from asyncio import get_event_loop\n",
        "",
        file_path,
    )
    text = _replace_or_raise(
        text,
        "        self.loop = get_event_loop()\n",
        "",
        file_path,
    )

    file_path.write_text(text, encoding="utf-8")


def main() -> None:
    spec = importlib.util.find_spec("ptterm")
    if spec is None or spec.origin is None:
        raise RuntimeError("ptterm is not installed in the current environment.")

    ptterm_base = Path(spec.origin).parent
    patch_win32_py(ptterm_base)
    patch_process_py(ptterm_base)
    print(f"Patched ptterm in: {ptterm_base}")


if __name__ == "__main__":
    main()
