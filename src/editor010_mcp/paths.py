"""Locate the 010 Editor executable across platforms."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

# Override: EDITOR010_EXE (preferred) or ZERO10_EXE / 010EDITOR_EXE.
_ENV_KEYS = ("EDITOR010_EXE", "ZERO10_EXE", "010EDITOR_EXE")

_WIN_CANDIDATES = (
    r"C:\Program Files\010 Editor\010Editor.exe",
    r"C:\Program Files (x86)\010 Editor\010Editor.exe",
)

_MAC_CANDIDATES = (
    "/Applications/010 Editor.app/Contents/MacOS/010 Editor",
    "/Applications/010Editor.app/Contents/MacOS/010 Editor",
)


def resolve_editor_exe() -> Path | None:
    """Return the 010 Editor binary path, or None if not found."""
    for key in _ENV_KEYS:
        raw = os.environ.get(key, "").strip().strip('"')
        if raw:
            p = Path(raw)
            if p.is_file():
                return p.resolve()

    for name in ("010editor", "010Editor", "010Editor.exe"):
        found = shutil.which(name)
        if found:
            return Path(found).resolve()

    candidates: list[str] = []
    if sys.platform == "win32":
        candidates.extend(_WIN_CANDIDATES)
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            candidates.append(
                str(Path(local) / "Programs" / "010 Editor" / "010Editor.exe")
            )
    elif sys.platform == "darwin":
        candidates.extend(_MAC_CANDIDATES)
    else:
        candidates.extend(
            (
                "/opt/010editor/010editor",
                "/usr/local/bin/010editor",
                str(Path.home() / "010editor" / "010editor"),
            )
        )

    for c in candidates:
        p = Path(c)
        if p.is_file():
            return p.resolve()
    return None


def file_version(exe: Path) -> str | None:
    """Best-effort product version (Windows PE resources only)."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class VS_FIXEDFILEINFO(ctypes.Structure):
            _fields_ = [
                ("dwSignature", wintypes.DWORD),
                ("dwStrucVersion", wintypes.DWORD),
                ("dwFileVersionMS", wintypes.DWORD),
                ("dwFileVersionLS", wintypes.DWORD),
                ("dwProductVersionMS", wintypes.DWORD),
                ("dwProductVersionLS", wintypes.DWORD),
                ("dwFileFlagsMask", wintypes.DWORD),
                ("dwFileFlags", wintypes.DWORD),
                ("dwFileOS", wintypes.DWORD),
                ("dwFileType", wintypes.DWORD),
                ("dwFileSubtype", wintypes.DWORD),
                ("dwFileDateMS", wintypes.DWORD),
                ("dwFileDateLS", wintypes.DWORD),
            ]

        size = ctypes.windll.version.GetFileVersionInfoSizeW(str(exe), None)
        if not size:
            return None
        buf = ctypes.create_string_buffer(size)
        if not ctypes.windll.version.GetFileVersionInfoW(str(exe), 0, size, buf):
            return None
        ptr = ctypes.c_void_p()
        length = wintypes.UINT()
        if not ctypes.windll.version.VerQueryValueW(
            buf, "\\", ctypes.byref(ptr), ctypes.byref(length)
        ):
            return None
        info = ctypes.cast(ptr, ctypes.POINTER(VS_FIXEDFILEINFO)).contents
        ms, ls = info.dwProductVersionMS, info.dwProductVersionLS
        return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
    except Exception:
        return None
