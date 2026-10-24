from pathlib import Path
import tempfile
import time
import subprocess

from editor010_mcp.paths import resolve_editor_exe

exe = resolve_editor_exe()
djf = Path(r"d:\code\mfc9330cdw\downloads\firmware\blobs\LZ4279_R.djf")
td = Path(tempfile.mkdtemp(prefix="editor010_mcp_orig_"))
(td / "exit.1sc").write_text("Exit(0);\n", encoding="utf-8", newline="\n")

# Original path
t = time.time()
try:
    p = subprocess.run(
        [str(exe), str(djf), "-script:exit.1sc", "-noui", "-nowarnings", "-exitnoerrors"],
        cwd=str(td),
        capture_output=True,
        text=True,
        timeout=20,
    )
    print("orig", "dt", round(time.time() - t, 2), "exit", p.returncode)
except subprocess.TimeoutExpired:
    print("orig TIMEOUT", round(time.time() - t, 2))
    subprocess.run(["taskkill", "/F", "/IM", "010Editor.exe", "/T"], capture_output=True)
    time.sleep(1)

# Same size random file in downloads folder
rnd = djf.parent / "_mcp_random.bin"
rnd.write_bytes(djf.read_bytes())  # same size
t = time.time()
try:
    p = subprocess.run(
        [str(exe), str(rnd), "-script:exit.1sc", "-noui", "-nowarnings", "-exitnoerrors"],
        cwd=str(td),
        capture_output=True,
        text=True,
        timeout=20,
    )
    print("random", "dt", round(time.time() - t, 2), "exit", p.returncode)
except subprocess.TimeoutExpired:
    print("random TIMEOUT", round(time.time() - t, 2))
    subprocess.run(["taskkill", "/F", "/IM", "010Editor.exe", "/T"], capture_output=True)

# cleanup
try:
    rnd.unlink()
except OSError:
    pass
