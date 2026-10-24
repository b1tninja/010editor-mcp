"""010 Editor MCP server (stdio).

There is **no** SweetScape plugin / COM API
(https://www.sweetscape.com/support/kb/kb1015.html). This server automates
010 via:

1. Official CLI flags (CommandLine.htm)
2. Generated Scripts (.1sc) that call Interface / I/O / Tool functions and
   write result files (ExportCSV, ExportXML, FileSaveRange, ChecksumAlgStr, …)

Requires a licensed local install of 010 Editor.
"""

from __future__ import annotations

from pathlib import Path

from fastmcp import FastMCP

from editor010_mcp import __version__
from editor010_mcp import bridge
from editor010_mcp.paths import file_version, resolve_editor_exe
from editor010_mcp.runner import result_dict, run_010, run_cli

mcp = FastMCP(
    name="010editor",
    instructions=(
        "Automate SweetScape 010 Editor. There is no external plugin API — "
        "use these tools (CLI + script bridge). Prefer run_template_export to "
        "get Template Results as CSV/XML. Prefer run_script_source for custom "
        "Interface/I/O/Tool function sequences; always write results with "
        "FileSave/ExportCSV/FPrintf (Printf is not captured from -noui). "
        "010 does not concatenate adjacent C string literals. "
        "Docs: CommandLine.htm, FuncInterface.htm, FuncIO.htm, FuncTools.htm; "
        "KB1015 confirms no integration API."
    ),
)

_CAPABILITIES = """# 010 Editor MCP — automation model

## Hard limit (SweetScape KB1015)
There is **no** external API / plugin SDK / COM automation for 010 Editor.
Third parties cannot load a DLL *into* 010 as a host plugin.
Scripts/Templates can call *out* to DLLs via `#link` (reverse direction).

## What this MCP uses instead
1. **CLI** — `-template:`, `-script:`, `-replace:`, `-compare:`, `-goto:`,
   `-select:`, `-save:`, `-import:`, `-noui`, `-nowarnings`, `-exit` /
   `-exitnoerrors` (see CommandLine.htm).
2. **Script bridge** — generate ephemeral `.1sc`, run headlessly, read
   artifact files. Key result APIs: `ExportCSV`, `ExportXML`, `FileSave`,
   `FileSaveRange`, `FPrintf`, `ChecksumAlgStr`, `FindAll`, `RunTemplate`.

## Authoring tips
- Keep `SPrintf` format strings as a **single** literal (no C adjacent-string concat).
- Windows paths inside `.1sc` strings: use `/` or doubled `\\\\`.
- `Exit(n)` becomes process `%ERRORLEVEL%` / exit code with `-exitnoerrors`.
"""


@mcp.resource("010editor://capabilities")
def capabilities_resource() -> str:
    """Describe how MCP talks to 010 (no plugin API)."""
    return _CAPABILITIES


def _err(e: BaseException) -> dict:
    return {
        "ok": False,
        "exit_code": -1,
        "error": str(e),
        "stdout": "",
        "stderr": "",
    }


@mcp.tool
def editor_status() -> dict:
    """Report whether 010 Editor is installed and which binary would be used.

    Override discovery with env EDITOR010_EXE (full path to 010Editor.exe /
    010editor). Also accepts ZERO10_EXE or 010EDITOR_EXE.
    """
    exe = resolve_editor_exe()
    if exe is None:
        return {
            "available": False,
            "exe": None,
            "version": None,
            "mcp_version": __version__,
            "integration": "cli+script-bridge",
            "plugin_api": False,
            "hint": "Install 010 Editor or set EDITOR010_EXE. See KB1015 — no plugin API.",
        }
    return {
        "available": True,
        "exe": str(exe),
        "version": file_version(exe),
        "mcp_version": __version__,
        "integration": "cli+script-bridge",
        "plugin_api": False,
        "hint": None,
    }


@mcp.tool
def run_template(
    data_file: str,
    template_file: str,
    timeout_sec: float = 120.0,
    exit_mode: str = "exitnoerrors",
    template_args: list[str] | None = None,
) -> dict:
    """Compile/run a Binary Template (.bt) on a data file (smoke / validate).

    Does not return Template Results — use run_template_export for CSV/XML.
    """
    try:
        return result_dict(
            run_010(
                data_file=Path(data_file),
                action="template",
                action_file=Path(template_file),
                action_args=template_args,
                timeout_sec=timeout_sec,
                exit_mode=exit_mode,
            )
        )
    except (FileNotFoundError, ValueError, OSError) as e:
        return _err(e)


@mcp.tool
def run_template_export(
    data_file: str,
    template_file: str,
    fmt: str = "csv",
    expand_all: bool = False,
    timeout_sec: float = 180.0,
) -> dict:
    """Run a Binary Template and export Template Results via ExportCSV/ExportXML.

    Returns export_text (possibly truncated), export_path, and run metadata.
    expand_all defaults to False (ExpandAll can hang on huge uchar arrays).
    """
    try:
        return bridge.run_template_export(
            Path(data_file),
            Path(template_file),
            fmt=fmt,
            expand_all=expand_all,
            timeout_sec=timeout_sec,
        )
    except (FileNotFoundError, ValueError, OSError) as e:
        return _err(e)


@mcp.tool
def run_script(
    script_file: str,
    data_file: str | None = None,
    timeout_sec: float = 120.0,
    exit_mode: str = "exitnoerrors",
    script_args: list[str] | None = None,
) -> dict:
    """Run an on-disk 010 Editor Script (.1sc), optionally on a data file."""
    try:
        return result_dict(
            run_010(
                data_file=Path(data_file) if data_file else None,
                action="script",
                action_file=Path(script_file),
                action_args=script_args,
                timeout_sec=timeout_sec,
                exit_mode=exit_mode,
            )
        )
    except (FileNotFoundError, ValueError, OSError) as e:
        return _err(e)


@mcp.tool
def run_script_source(
    source: str,
    data_file: str | None = None,
    timeout_sec: float = 120.0,
    exit_mode: str = "exitnoerrors",
    script_args: list[str] | None = None,
) -> dict:
    """Run inline .1sc source (written to a temp file).

    Use Interface/I/O/Tool functions; write any agent-visible results to files
    (ExportCSV, FileSave, FPrintf). Printf is not captured under -noui.
    Appends Exit(0); if missing. On failure, workdir is kept for inspection.
    """
    try:
        r, _td = bridge.run_script_source(
            source,
            data_file=Path(data_file) if data_file else None,
            timeout_sec=timeout_sec,
            exit_mode=exit_mode,
            script_args=script_args,
        )
        return result_dict(r)
    except (FileNotFoundError, ValueError, OSError) as e:
        return _err(e)


@mcp.tool
def checksum_file(
    data_file: str,
    algorithm: str = "SHA256",
    start: int = 0,
    size: int = 0,
    timeout_sec: float = 120.0,
) -> dict:
    """Compute a checksum/hash with 010's ChecksumAlgStr (Tool Functions).

    algorithm: SHA256, MD5, SHA1, CRC32, … or full CHECKSUM_* constant name.
    Optional start/size select a local-coordinate range (0/0 = whole file).
    """
    try:
        return bridge.run_checksum(
            Path(data_file),
            algorithm=algorithm,
            start=start,
            size=size,
            timeout_sec=timeout_sec,
        )
    except (FileNotFoundError, ValueError, OSError) as e:
        return _err(e)


@mcp.tool
def find_in_file(
    data_file: str,
    pattern: str,
    match_case: bool = True,
    whole_word: bool = False,
    method: int = 0,
    dir_down: bool = True,
    start: int = 0,
    size: int = 0,
    max_hits: int = 500,
    timeout_sec: float = 120.0,
    engine: str = "python",
) -> dict:
    """Find pattern hits. Default engine=python (plain text or 'FFD8,h' hex).

    engine='010' uses FindAll (wildcards/regex via method=1/2). Large-file
    opens under -noui can hang on some installs — prefer python when possible.
    """
    try:
        return bridge.run_find(
            Path(data_file),
            pattern,
            match_case=match_case,
            whole_word=whole_word,
            method=method,
            dir_down=dir_down,
            start=start,
            size=size,
            max_hits=max_hits,
            timeout_sec=timeout_sec,
            engine=engine,
        )
    except (FileNotFoundError, ValueError, OSError) as e:
        return _err(e)


@mcp.tool
def extract_range(
    data_file: str,
    out_file: str,
    start: int,
    size: int,
    timeout_sec: float = 120.0,
) -> dict:
    """Extract a byte range with FileSaveRange into out_file."""
    try:
        return bridge.run_extract_range(
            Path(data_file),
            Path(out_file),
            start,
            size,
            timeout_sec=timeout_sec,
        )
    except (FileNotFoundError, ValueError, OSError) as e:
        return _err(e)


@mcp.tool
def replace_in_file(
    data_file: str,
    find_value: str,
    replace_value: str,
    save: bool = True,
    timeout_sec: float = 120.0,
) -> dict:
    """CLI -replace:<find>:<replace> (see CommandLine.htm escape codes).

    Examples: find_value='apple', replace_value='orange';
    hex: find_value='0D0A,h', replace_value='0A,h'.
    Append flags on replace_value (e.g. match-case via documented \\m codes).
    If save is True, also passes -save so the file is written back.
    """
    try:
        p = Path(data_file).resolve()
        if not p.is_file():
            raise FileNotFoundError(f"data file not found: {p}")
        rep = f"-replace:{find_value}:{replace_value}"
        args = [str(p), rep]
        if save:
            args.append("-save")
        return result_dict(
            run_cli(args=args, cwd=p.parent, timeout_sec=timeout_sec)
        )
    except (FileNotFoundError, ValueError, OSError) as e:
        return _err(e)


@mcp.tool
def compare_files(
    file_a: str,
    file_b: str,
    options: str = "",
    timeout_sec: float = 180.0,
) -> dict:
    """CLI binary compare: -compare:A::B[::options].

    options escape codes (CommandLine.htm): \\b byte-by-byte, \\i ignore case,
    \\xXXX max lookahead, \\nXXX min match, \\zaXXX/\\zbXXX size limits, etc.
    Comparison UI results are not exported; for structured diffs use
    run_script_source calling Compare() + FPrintf.
    """
    try:
        a = Path(file_a).resolve()
        b = Path(file_b).resolve()
        if not a.is_file():
            raise FileNotFoundError(f"file_a not found: {a}")
        if not b.is_file():
            raise FileNotFoundError(f"file_b not found: {b}")
        flag = f"-compare:{a}::{b}"
        if options:
            flag += f"::{options}"
        return result_dict(run_cli(args=[flag], cwd=a.parent, timeout_sec=timeout_sec))
    except (FileNotFoundError, ValueError, OSError) as e:
        return _err(e)


@mcp.tool
def open_in_gui(
    data_file: str | None = None,
    template_file: str | None = None,
    script_file: str | None = None,
    goto: str | None = None,
    select: str | None = None,
    line: int | None = None,
) -> dict:
    """Launch 010 Editor with a UI (not headless) — for interactive inspection.

    Optional: -template: / -script: (run on open), -goto:, -select:start:size, -line:.
    Does not wait for the process to exit.
    """
    try:
        args: list[str] = []
        cwd: Path | None = None
        if data_file:
            p = Path(data_file).resolve()
            if not p.is_file():
                raise FileNotFoundError(f"data file not found: {p}")
            args.append(str(p))
            cwd = p.parent
        if goto:
            args.append(f"-goto:{goto}")
        if select:
            args.append(f"-select:{select}")
        if line is not None:
            args.append(f"-line:{line}")
        if template_file:
            t = Path(template_file).resolve()
            if not t.is_file():
                raise FileNotFoundError(f"template not found: {t}")
            args.append(f"-template:{t.name}")
            cwd = t.parent
        if script_file:
            s = Path(script_file).resolve()
            if not s.is_file():
                raise FileNotFoundError(f"script not found: {s}")
            args.append(f"-script:{s.name}")
            cwd = s.parent
        return result_dict(
            run_cli(
                args=args,
                cwd=cwd,
                headless=False,
                exit_mode=None,
                wait=False,
            )
        )
    except (FileNotFoundError, ValueError, OSError) as e:
        return _err(e)


@mcp.tool
def run_raw_cli(
    args: list[str],
    cwd: str | None = None,
    headless: bool = True,
    exit_mode: str | None = "exitnoerrors",
    timeout_sec: float = 180.0,
    wait: bool = True,
) -> dict:
    """Escape hatch: pass argv tokens after 010Editor.exe (advanced).

    Example args: ['D:/f.bin', '-goto:0x100', '-select:0x100:0x20', '-template:X.bt']
    When headless, -noui -nowarnings and -exit_mode are appended automatically.
    """
    try:
        return result_dict(
            run_cli(
                args=args,
                cwd=cwd,
                timeout_sec=timeout_sec,
                headless=headless,
                exit_mode=exit_mode,
                wait=wait,
            )
        )
    except (FileNotFoundError, ValueError, OSError) as e:
        return _err(e)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
