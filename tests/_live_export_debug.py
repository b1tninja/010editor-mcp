from pathlib import Path
import tempfile
import subprocess
import time

from editor010_mcp.paths import resolve_editor_exe
from editor010_mcp.scriptlang import path_literal

exe = resolve_editor_exe()
td = Path(tempfile.mkdtemp(prefix="editor010_mcp_exp_"))
tiny = td / "tiny.bin"
tiny.write_bytes(bytes(range(256)))
csv = td / "out.csv"
bt = td / "tiny.bt"
bt.write_text(
    "BigEndian();\ntypedef struct { uchar magic[4]; uint32 len; } HDR;\nHDR h;\n",
    encoding="utf-8",
    newline="\n",
)
src2 = f"""
RunTemplate({path_literal(bt)}, true);
ExportCSV({path_literal(csv)});
Exit(0);
"""
s2 = td / "export.1sc"
s2.write_text(src2, encoding="utf-8", newline="\n")
t0 = time.time()
proc = subprocess.run(
    [str(exe), str(tiny), f"-script:{s2.name}", "-noui", "-nowarnings", "-exitnoerrors"],
    cwd=str(td),
    capture_output=True,
    text=True,
    timeout=60,
)
print("export exit", proc.returncode, "dt", round(time.time() - t0, 2))
print("csv", csv.exists(), csv.stat().st_size if csv.exists() else None)
if csv.exists():
    print(csv.read_text(encoding="utf-8", errors="replace")[:500])
