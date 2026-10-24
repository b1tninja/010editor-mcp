from pathlib import Path
import tempfile
import subprocess

from editor010_mcp.paths import resolve_editor_exe
from editor010_mcp.scriptlang import c_string

exe = resolve_editor_exe()
assert exe
td = Path(tempfile.mkdtemp(prefix="editor010_mcp_dbg2_"))
out = td / "hello.txt"
# Pre-create marker so we know the dir is writable from Python
(td / "marker.txt").write_text("pyok", encoding="utf-8")

# Use doubled backslashes like SweetScape docs
win_path = str(out.resolve()).replace("\\", "\\\\")
src = f"""
local int h = FileNew("Text", true);
FPrintf(GetFileNum(), "hello-from-010\\n");
local int rc = FileSave("{win_path}");
if (rc < 0) Exit(-3);
Exit(0);
"""
script = td / "job.1sc"
script.write_text(src, encoding="utf-8", newline="\n")
print("script path", script)
print(src)
argv = [str(exe), f"-script:{script.name}", "-noui", "-nowarnings", "-exitnoerrors"]
print("argv", argv)
proc = subprocess.run(argv, cwd=str(td), capture_output=True, text=True, timeout=60)
print("exit", proc.returncode, "stdout", repr(proc.stdout), "stderr", repr(proc.stderr))
print("files after:", sorted(p.name for p in td.iterdir()))
print("hello exists", out.exists(), out.stat().st_size if out.exists() else None)
