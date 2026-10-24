"""Helpers for generating 010 Editor Script (.1sc) source."""

from __future__ import annotations

from pathlib import Path


def path_for_string(path: str | Path) -> str:
    """Path text as it should appear *inside* a 010 string literal.

    SweetScape requires doubled backslashes on Windows (``C:\\\\temp\\\\a.txt``
    in source → ``C:\\temp\\a.txt`` at runtime). Forward-slash paths can make
    ``FileSave`` return success without creating the file — avoid them.
    """
    return str(Path(path).resolve()).replace("\\", "\\\\").replace('"', '\\"')


def c_string(s: str) -> str:
    """Quote an arbitrary value as a 010/C string literal."""
    out = ['"']
    for ch in s:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif ord(ch) < 0x20:
            out.append(f"\\x{ord(ch):02X}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def path_literal(path: str | Path) -> str:
    """Full quoted path literal for FileSave / ExportCSV / FileOpen, etc."""
    return f'"{path_for_string(path)}"'


def write_text_result_snippet(out_path: str | Path, format_and_args: str) -> str:
    """Return .1sc lines that write formatted text to ``out_path`` then close it.

    ``format_and_args`` is the body after ``FPrintf(GetFileNum(),`` e.g.
    ``\"%s\\n\", result``.
    """
    return "\n".join(
        [
            'local int __mcp_out = FileNew("Text", true);',
            'if (__mcp_out < 0) { Warning("FileNew failed"); Exit(-2); }',
            f"FPrintf(__mcp_out, {format_and_args});",
            "FileSelect(__mcp_out);",
            f"if (FileSave({path_literal(out_path)}) < 0) {{ Warning(\"FileSave failed\"); Exit(-3); }}",
            "FileClose();",
        ]
    )
