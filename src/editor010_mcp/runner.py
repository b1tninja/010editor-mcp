"""Headless 010 Editor CLI runner.

SweetScape docs:
  https://www.sweetscape.com/010editor/manual/CommandLine.htm

Key flags:
  -template:NAME.bt   run Binary Template (cwd or Templates dir)
  -script:NAME.1sc    run Script
  -noui               no splash / main window
  -nowarnings         suppress message boxes (needed for batch)
  -exit               always quit after CLI work
  -exitnoerrors       quit only if template/script compiled & ran cleanly

Exit codes: template/script may call Exit(n); otherwise 010 sets non-zero
on compile/run failure when using -exitnoerrors.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from editor010_mcp.paths import resolve_editor_exe


@dataclass
class RunResult:
    ok: bool
    exit_code: int
    exe: str
    cwd: str
    argv: list[str]
    stdout: str
    stderr: str
    error: str | None = None


def _require_exe() -> Path:
    exe = resolve_editor_exe()
    if exe is None:
        raise FileNotFoundError(
            "010 Editor not found. Install it, add it to PATH, or set "
            "EDITOR010_EXE to the 010Editor.exe (or 010editor) path."
        )
    return exe


def run_010(
    *,
    data_file: Path | None,
    action: str,
    action_file: Path,
    action_args: list[str] | None = None,
    timeout_sec: float = 120.0,
    exit_mode: str = "exitnoerrors",
) -> RunResult:
    """Run a template or script headlessly.

    Parameters
    ----------
    data_file:
        Binary/text file to open (required for templates; optional for some scripts).
    action:
        ``"template"`` or ``"script"``.
    action_file:
        Path to ``.bt`` or ``.1sc``. The basename is passed to ``-template:`` /
        ``-script:`` and the parent directory is used as cwd (010 resolves
        names from cwd or the configured Templates/Scripts directory).
    action_args:
        Optional args passed as ``-template:file.bt:(a,b)``.
    timeout_sec:
        Subprocess timeout.
    exit_mode:
        ``"exitnoerrors"`` (default, fail on compile/run errors) or ``"exit"``.
    """
    if action not in ("template", "script"):
        raise ValueError("action must be 'template' or 'script'")
    if exit_mode not in ("exit", "exitnoerrors"):
        raise ValueError("exit_mode must be 'exit' or 'exitnoerrors'")

    exe = _require_exe()
    action_file = action_file.resolve()
    if not action_file.is_file():
        raise FileNotFoundError(f"{action} file not found: {action_file}")

    if data_file is not None:
        data_file = data_file.resolve()
        if not data_file.is_file():
            raise FileNotFoundError(f"data file not found: {data_file}")

    name = action_file.name
    if action_args:
        joined = ",".join(action_args)
        flag = f"-{action}:{name}:({joined})"
    else:
        flag = f"-{action}:{name}"

    argv: list[str] = [str(exe)]
    if data_file is not None:
        argv.append(str(data_file))
    argv.extend([flag, "-noui", "-nowarnings", f"-{exit_mode}"])

    cwd = str(action_file.parent)
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        return RunResult(
            ok=False,
            exit_code=-1,
            exe=str(exe),
            cwd=cwd,
            argv=argv[1:],
            stdout=(e.stdout or "") if isinstance(e.stdout, str) else "",
            stderr=(e.stderr or "") if isinstance(e.stderr, str) else "",
            error=f"timed out after {timeout_sec}s",
        )

    return RunResult(
        ok=proc.returncode == 0,
        exit_code=proc.returncode,
        exe=str(exe),
        cwd=cwd,
        argv=argv[1:],
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
        error=None if proc.returncode == 0 else f"exit code {proc.returncode}",
    )


def result_dict(r: RunResult) -> dict:
    return {
        "ok": r.ok,
        "exit_code": r.exit_code,
        "exe": r.exe,
        "cwd": r.cwd,
        "argv": r.argv,
        "stdout": r.stdout.strip(),
        "stderr": r.stderr.strip(),
        "error": r.error,
    }
