from pathlib import Path

from editor010_mcp.scriptlang import c_string, path_literal


def test_c_string_escapes():
    assert c_string('a"b\\c') == '"a\\"b\\\\c"'


def test_path_literal_doubles_backslashes(tmp_path: Path):
    f = tmp_path / "sub" / "x.bin"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(b"x")
    lit = path_literal(f)
    resolved = str(f.resolve())
    assert lit.startswith('"') and lit.endswith('"')
    # Every single backslash in the real path becomes two in the source literal.
    expected_inner = resolved.replace("\\", "\\\\")
    assert lit == f'"{expected_inner}"'
