from pathlib import Path
import tempfile
import subprocess
import time

from editor010_mcp.paths import resolve_editor_exe
from editor010_mcp.scriptlang import path_literal

exe = resolve_editor_exe()
td = Path(tempfile.mkdtemp(prefix="editor010_mcp_min_"))
out = td / "hi.txt"
src = "\n".join(
    [
        'local int h = FileNew("Text", true);',
        'FPrintf(h, "ok\\n");',
        "FileSelect(h);",
        f"if (FileSave({path_literal(out)}) < 0) Exit(-3);",
        "Exit(0);",
    ]
)
(td / "job.1sc").write_text(src, encoding="utf-8", newline="\n")
print("td", td)
t = time.time()
p = subprocess.run(
    [str(exe), "-script:job.1sc", "-noui", "-nowarnings", "-exit"],
    cwd=str(td),
    capture_output=True,
    text=True,
    timeout=30,
)
print("dt", round(time.time() - t, 2), "exit", p.returncode)
print("out", out.read_text(encoding="utf-8") if out.exists() else None)
