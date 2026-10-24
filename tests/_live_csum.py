from pathlib import Path
import tempfile
import subprocess
import time

from editor010_mcp.paths import resolve_editor_exe
from editor010_mcp.scriptlang import path_literal

exe = resolve_editor_exe()
djf = Path(r"d:\code\mfc9330cdw\downloads\firmware\blobs\LZ4279_R.djf")
td = Path(tempfile.mkdtemp(prefix="editor010_mcp_c2_"))
out = td / "checksum.txt"
src = "\n".join(
    [
        "local char result[512];",
        "local int n = ChecksumAlgStr(CHECKSUM_MD5, result, 0, 0);",
        "if (n < 0) Exit(-1);",
        'local int h = FileNew("Text", true);',
        "if (h < 0) Exit(-2);",
        'FPrintf(h, "%s\\n", result);',
        "FileSelect(h);",
        f"local int rc = FileSave({path_literal(out)});",
        "if (rc < 0) Exit(-3);",
        "Exit(0);",
    ]
)
(td / "checksum.1sc").write_text(src, encoding="utf-8", newline="\n")
print(src)
t = time.time()
p = subprocess.run(
    [str(exe), str(djf), "-script:checksum.1sc", "-noui", "-nowarnings", "-exitnoerrors"],
    cwd=str(td),
    capture_output=True,
    text=True,
    timeout=120,
)
print("dt", round(time.time() - t, 2), "exit", p.returncode)
print("files", sorted(x.name for x in td.iterdir()))
print("out", out.exists(), out.read_text(encoding="utf-8") if out.exists() else None)
