from pathlib import Path
import tempfile

from editor010_mcp.bridge import run_script_source
from editor010_mcp.scriptlang import path_literal

djf = Path(r"d:\code\mfc9330cdw\downloads\firmware\blobs\LZ4279_R.djf")
td = Path(tempfile.mkdtemp(prefix="editor010_mcp_hello_"))
out = td / "hello.txt"
src = "\n".join(
    [
        f"local int __mcp_out = FileNew(\"Text\", false);",
        f"FPrintf(__mcp_out, \"hello\\n\");",
        f"FileSelect(__mcp_out);",
        f"local int rc = FileSave({path_literal(out)});",
        "if (rc < 0) Exit(-3);",
        "Exit(0);",
    ]
)
print("SCRIPT:\n", src)
print("OUT", out)
r, w = run_script_source(src, data_file=djf, keep_workdir=True)
print("ok", r.ok, "exit", r.exit_code, "err", r.error)
print("artifacts", r.artifacts)
wd = Path(r.artifacts["workdir"])
print("workdir files", list(wd.iterdir()))
print("td files", list(td.iterdir()))
print("out exists", out.exists())
