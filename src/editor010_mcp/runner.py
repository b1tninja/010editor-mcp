"""010 Editor CLI runner.

Official docs: https://www.sweetscape.com/010editor/manual/CommandLine.htm

SweetScape [KB1015](https://www.sweetscape.com/support/kb/kb1015.html): there is
**no external plugin / COM / IPC API**. Automation is CLI + Scripts/Templates.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
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
    artifacts: dict[str, str] = field(default_factory=dict)


def require_exe() -> Path:
    exe = resolve_editor_exe()
    if exe is None:
        raise FileNotFoundError(
            "010 Editor not found. Install it, add it to PATH, or set "
            "EDITOR010_EXE to the 010Editor.exe (or 010editor) path."
        )
    return exe


def _action_flag(action: str, action_file: Path, action_args: list[str] | None) -> str:
    name = action_file.name
    if action_args:
        return f"-{action}:{name}:({','.join(action_args)})"
    return f"-{action}:{name}"


def run_cli(
    *,
    args: list[str],
    cwd: str | Path | None = None,
    timeout_sec: float = 120.0,
    headless: bool = True,
    exit_mode: str | None = "exitnoerrors",
    wait: bool = True,
) -> RunResult:
    """Run 010 Editor with arbitrary CLI arguments (after the exe path).

    When ``headless`` is True, appends ``-noui -nowarnings`` and ``-<exit_mode>``
    if ``exit_mode`` is set. When ``wait`` is False, starts the process and
    returns immediately (for GUI open).
    """
    if exit_mode is not None and exit_mode not in ("exit", "exitnoerrors"):
        raise ValueError("exit_mode must be 'exit', 'exitnoerrors', or None")

    exe = require_exe()
    argv: list[str] = [str(exe), *args]
    if headless:
        argv.extend(["-noui", "-nowarnings"])
        if exit_mode:
            argv.append(f"-{exit_mode}")

    work = str(Path(cwd).resolve()) if cwd else str(Path.cwd())

    if not wait:
        try:
            subprocess.Popen(argv, cwd=work)  # noqa: S603
        except OSError as e:
            return RunResult(
                ok=False,
                exit_code=-1,
                exe=str(exe),
                cwd=work,
                argv=argv[1:],
                stdout="",
                stderr="",
                error=str(e),
            )
        return RunResult(
            ok=True,
            exit_code=0,
            exe=str(exe),
            cwd=work,
            argv=argv[1:],
            stdout="",
            stderr="",
            error=None,
        )

    # 010 Editor is effectively single-instance: a hung process blocks later
    # CLI runs. Always kill the child on timeout.
    try:
        proc = subprocess.Popen(
            argv,
            cwd=work,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as e:
        return RunResult(
            ok=False,
            exit_code=-1,
            exe=str(exe),
            cwd=work,
            argv=argv[1:],
            stdout="",
            stderr="",
            error=str(e),
        )

    try:
        stdout, stderr = proc.communicate(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except Exception:
            stdout, stderr = "", ""
        return RunResult(
            ok=False,
            exit_code=-1,
            exe=str(exe),
            cwd=work,
            argv=argv[1:],
            stdout=stdout or "",
            stderr=stderr or "",
            error=f"timed out after {timeout_sec}s (process killed)",
        )

    return RunResult(
        ok=proc.returncode == 0,
        exit_code=proc.returncode if proc.returncode is not None else -1,
        exe=str(exe),
        cwd=work,
        argv=argv[1:],
        stdout=stdout or "",
        stderr=stderr or "",
        error=None if proc.returncode == 0 else f"exit code {proc.returncode}",
    )


def run_010(
    *,
    data_file: Path | None,
    action: str,
    action_file: Path,
    action_args: list[str] | None = None,
    timeout_sec: float = 120.0,
    exit_mode: str = "exitnoerrors",
    extra_args: list[str] | None = None,
) -> RunResult:
    """Run a template or script headlessly (basename + parent-dir cwd)."""
    if action not in ("template", "script"):
        raise ValueError("action must be 'template' or 'script'")

    action_file = action_file.resolve()
    if not action_file.is_file():
        raise FileNotFoundError(f"{action} file not found: {action_file}")

    args: list[str] = []
    if data_file is not None:
        data_file = data_file.resolve()
        if not data_file.is_file():
            raise FileNotFoundError(f"data file not found: {data_file}")
        args.append(str(data_file))
    if extra_args:
        args.extend(extra_args)
    args.append(_action_flag(action, action_file, action_args))

    return run_cli(
        args=args,
        cwd=action_file.parent,
        timeout_sec=timeout_sec,
        headless=True,
        exit_mode=exit_mode,
        wait=True,
    )


def result_dict(r: RunResult) -> dict:
    d = {
        "ok": r.ok,
        "exit_code": r.exit_code,
        "exe": r.exe,
        "cwd": r.cwd,
        "argv": r.argv,
        "stdout": r.stdout.strip(),
        "stderr": r.stderr.strip(),
        "error": r.error,
    }
    if r.artifacts:
        d["artifacts"] = r.artifacts
    return d
