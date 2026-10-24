"""010 Editor MCP server (stdio).

Tools wrap the official CLI so agents can compile/run Binary Templates and
Scripts without a GUI. Requires a licensed/installed copy of 010 Editor.
"""

from __future__ import annotations

from pathlib import Path

from fastmcp import FastMCP

from editor010_mcp import __version__
from editor010_mcp.paths import file_version, resolve_editor_exe
from editor010_mcp.runner import result_dict, run_010

mcp = FastMCP(
    name="010editor",
    instructions=(
        "Drive SweetScape 010 Editor headlessly: locate the install, run "
        "Binary Templates (.bt) and Scripts (.1sc) on files, and check exit "
        "codes. 010 does not concatenate adjacent C string literals — keep "
        "SPrintf format strings as a single literal. Template/script files "
        "are resolved by basename from their parent directory (cwd)."
    ),
)


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
            "hint": "Install 010 Editor or set EDITOR010_EXE to the binary path.",
        }
    return {
        "available": True,
        "exe": str(exe),
        "version": file_version(exe),
        "mcp_version": __version__,
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
    """Run a Binary Template (.bt) on a data file via 010 Editor CLI.

    Uses: 010editor <data> -template:<name>.bt -noui -nowarnings -<exit_mode>
    Working directory is the template's parent folder so -template: resolves.

    exit_mode:
      - exitnoerrors (default): process exits only if the template compiled
        and ran without error; non-zero exit means failure.
      - exit: always exit after the CLI action (weaker failure signal).

    Returns ok, exit_code, stdout/stderr, and the argv used.
    """
    try:
        r = run_010(
            data_file=Path(data_file),
            action="template",
            action_file=Path(template_file),
            action_args=template_args,
            timeout_sec=timeout_sec,
            exit_mode=exit_mode,
        )
        return result_dict(r)
    except (FileNotFoundError, ValueError, OSError) as e:
        return {
            "ok": False,
            "exit_code": -1,
            "error": str(e),
            "stdout": "",
            "stderr": "",
        }


@mcp.tool
def run_script(
    script_file: str,
    data_file: str | None = None,
    timeout_sec: float = 120.0,
    exit_mode: str = "exitnoerrors",
    script_args: list[str] | None = None,
) -> dict:
    """Run a 010 Editor Script (.1sc), optionally on a data file.

    Uses: 010editor [data] -script:<name>.1sc -noui -nowarnings -<exit_mode>
    Cwd is the script's parent directory.

    Scripts can call RunTemplate(\"foo.bt\") and Exit(n) for custom codes.
    """
    try:
        r = run_010(
            data_file=Path(data_file) if data_file else None,
            action="script",
            action_file=Path(script_file),
            action_args=script_args,
            timeout_sec=timeout_sec,
            exit_mode=exit_mode,
        )
        return result_dict(r)
    except (FileNotFoundError, ValueError, OSError) as e:
        return {
            "ok": False,
            "exit_code": -1,
            "error": str(e),
            "stdout": "",
            "stderr": "",
        }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
