from pathlib import Path
import tempfile
import subprocess
import time

from editor010_mcp.paths import resolve_editor_exe
from editor010_mcp.scriptlang import path_literal

exe = resolve_editor_exe()
djf = Path(r"d:\code\mfc9330cdw\downloads\firmware\blobs\LZ4279_R.djf")
# Also try a tiny copy
td = Path(tempfile.mkdtemp(prefix="editor010_mcp_open_"))
tiny = td / "tiny.bin"
tiny.write_bytes(djf.read_bytes()[:4096])

for label, path in [("tiny", tiny), ("full", djf)]:
    out = td / f"{label}.txt"
    src = "\n".join(
        [
            f"if (FileOpen({path_literal(path)}, false) < 0) Exit(-10);",
            f'local int h = FileNew("Text", true);',
            f'FPrintf(h, "size=%Ld\\n", FileSize());',
            # FileSize is for current file - need select data file first
            # Actually after FileNew, current is new file. Re-open logic:
            "Exit(0);",
        ]
    )
    # Better script
    src = "\n".join(
        [
            f"local int fi = FileOpen({path_literal(path)}, false);",
            "if (fi < 0) Exit(-10);",
            "FileSelect(fi);",
            f'local int h = FileNew("Text", true);',
            "FileSelect(fi);",
            f'FPrintf(h, "size=%Ld\\n", FileSize());',
            "FileSelect(h);",
            f"if (FileSave({path_literal(out)}) < 0) Exit(-3);",
            "Exit(0);",
        ]
    )
    script = td / f"{label}.1sc"
    script.write_text(src, encoding="utf-8", newline="\n")
    print("===", label, path.stat().st_size)
    t = time.time()
    try:
        p = subprocess.run(
            [str(exe), f"-script:{script.name}", "-noui", "-nowarnings", "-exitnoerrors"],
            cwd=str(td),
            capture_output=True,
            text=True,
            timeout=60,
        )
        print("dt", round(time.time() - t, 2), "exit", p.returncode, "out", out.read_text() if out.exists() else None)
    except subprocess.TimeoutExpired:
        print("TIMEOUT after", round(time.time() - t, 2))
        subprocess.run(["taskkill", "/F", "/IM", "010Editor.exe", "/T"], capture_output=True)
