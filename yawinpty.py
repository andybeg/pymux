"""
Compatibility shim for projects expecting the old ``yawinpty`` package.

`ptterm` imports:
    from yawinpty import Pty, SpawnConfig

This module maps that API to `pywinpty` (`winpty` module).
"""
from __future__ import unicode_literals

try:
    from winpty.cywinpty import Agent as _Agent
except Exception as e:
    raise ImportError(
        "Cannot import winpty backend required for yawinpty compatibility. "
        "Install pywinpty==0.5.1 and Microsoft Visual C++ 2015-2022 "
        "Redistributable (x64). Original error: %s" % (e,)
    )


class SpawnConfig(object):
    class flag(object):
        auto_shutdown = 0

    def __init__(self, _flags=0, cmdline='cmd.exe'):
        self.cmdline = cmdline


class Pty(object):
    def __init__(self, cols=120, rows=30):
        # Use low-level Agent API. Unlike `winpty.PTY`, this does not open the
        # named pipes eagerly, which matches what `ptterm` expects.
        self._pty = _Agent(cols, rows)

    def conin_name(self):
        return self._pty.conin_pipe_name

    def conout_name(self):
        return self._pty.conout_pipe_name

    def set_size(self, width, height):
        self._pty.set_size(width, height)

    def spawn(self, spawn_config):
        cmdline = getattr(spawn_config, 'cmdline', 'cmd.exe')
        return self._pty.spawn(cmdline)

    def close(self):
        # Agent has no explicit close() API in this pywinpty version.
        pass
