from pathlib import Path

from editor010_mcp.bridge import run_checksum, run_extract_range, run_find


def test_checksum_and_find(tmp_path: Path):
    p = tmp_path / "a.bin"
    p.write_bytes(b"xxProgramOKyyProgramOK")
    c = run_checksum(p, algorithm="MD5")
    assert c["ok"] and len(c["digest"]) == 32
    f = run_find(p, "ProgramOK")
    assert f["ok"] and f["hit_count_total"] == 2
    assert f["hits"][0]["start"] == 2
    h = run_find(p, "50726F67,h")  # "Prog"
    assert h["ok"] and h["hit_count_total"] >= 1
    out = tmp_path / "slice.bin"
    e = run_extract_range(p, out, 2, 9)
    assert e["ok"] and out.read_bytes() == b"ProgramOK"
