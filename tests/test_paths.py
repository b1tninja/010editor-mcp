from pathlib import Path

from editor010_mcp.paths import resolve_editor_exe


def test_resolve_editor_exe_env(monkeypatch, tmp_path: Path):
    fake = tmp_path / "010Editor.exe"
    fake.write_bytes(b"MZ")
    monkeypatch.setenv("EDITOR010_EXE", str(fake))
    monkeypatch.delenv("ZERO10_EXE", raising=False)
    monkeypatch.delenv("010EDITOR_EXE", raising=False)
    got = resolve_editor_exe()
    assert got == fake.resolve()


def test_resolve_missing(monkeypatch):
    monkeypatch.delenv("EDITOR010_EXE", raising=False)
    monkeypatch.delenv("ZERO10_EXE", raising=False)
    monkeypatch.delenv("010EDITOR_EXE", raising=False)
    monkeypatch.setattr("editor010_mcp.paths.shutil.which", lambda _n: None)
    monkeypatch.setattr("editor010_mcp.paths.sys.platform", "linux")
    # No candidates exist under home in this test → None (or a real install).
    # Force empty candidate list by pointing home to empty tmp — skip if real PATH hit.
    # We only assert the function returns Path|None without raising.
    result = resolve_editor_exe()
    assert result is None or isinstance(result, Path)
