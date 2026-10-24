"""Ephemeral .1sc jobs — the practical substitute for a missing plugin API.

Pattern:
  1. Stage the data file as ``*.bin`` in a temp dir (avoids Template auto-run
     on extensions like ``.djf``, and avoids ``FileOpen()`` which hangs under
     ``-noui`` on some 010 builds).
  2. Write a temporary Script; run ``010editor data.bin -script:job.1sc ...``.
  3. Read artifact files back into the MCP response.

Printf is not reliably captured on stdout under ``-noui`` — write result files.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from editor010_mcp.runner import RunResult, result_dict, run_010
from editor010_mcp.scriptlang import path_literal, write_text_result_snippet


def stage_data(data_file: Path, workdir: Path) -> Path:
    """Hardlink (or copy) ``data_file`` into ``workdir`` as ``<stem>.bin``."""
    data_file = data_file.resolve()
    if not data_file.is_file():
        raise FileNotFoundError(f"data file not found: {data_file}")
    staged = workdir / f"{data_file.stem}.bin"
    if staged.exists():
        staged.unlink()
    try:
        os.link(data_file, staged)
    except OSError:
        shutil.copyfile(data_file, staged)
    return staged


def run_script_source(
    source: str,
    *,
    data_file: Path | None = None,
    timeout_sec: float = 120.0,
    exit_mode: str = "exitnoerrors",
    keep_workdir: bool = False,
    script_args: list[str] | None = None,
    stage: bool = True,
) -> tuple[RunResult, Path]:
    """Write ``source`` to a temp ``.1sc``, run it, return (result, workdir).

    When ``data_file`` is set and ``stage`` is True, open a staged ``.bin``
    copy/hardlink via the CLI (recommended). Set ``stage=False`` to pass the
    original path on the CLI (may auto-run an associated Template).
    """
    td = Path(tempfile.mkdtemp(prefix="editor010_mcp_"))
    script = td / "job.1sc"
    body = source.rstrip() + "\n"
    if "Exit(" not in body:
        body += "Exit(0);\n"
    script.write_text(body, encoding="utf-8", newline="\n")

    open_path: Path | None = None
    if data_file is not None:
        data_file = data_file.resolve()
        open_path = stage_data(data_file, td) if stage else data_file

    r = run_010(
        data_file=open_path,
        action="script",
        action_file=script,
        action_args=script_args,
        timeout_sec=timeout_sec,
        exit_mode=exit_mode,
    )
    r.artifacts["workdir"] = str(td)
    r.artifacts["script"] = str(script)
    if open_path is not None:
        r.artifacts["staged_data"] = str(open_path)
    _ = keep_workdir
    return r, td


def run_template_export(
    data_file: Path,
    template_file: Path,
    *,
    fmt: str = "csv",
    expand_all: bool = False,
    timeout_sec: float = 180.0,
) -> dict:
    """Run a Binary Template and ExportCSV / ExportXML Template Results.

    ``expand_all`` defaults to False — ExpandAll on templates with huge byte
    arrays (multi‑MB ``uchar data[N]``) can hang or run for a very long time.
    """
    fmt = fmt.lower().strip()
    if fmt not in ("csv", "xml"):
        raise ValueError("fmt must be 'csv' or 'xml'")

    data_file = data_file.resolve()
    template_file = template_file.resolve()
    if not template_file.is_file():
        raise FileNotFoundError(f"template not found: {template_file}")

    td = Path(tempfile.mkdtemp(prefix="editor010_mcp_export_"))
    staged = stage_data(data_file, td)
    out = td / f"template_results.{fmt}"
    export_fn = "ExportCSV" if fmt == "csv" else "ExportXML"
    expand = "ExpandAll();\n" if expand_all else ""

    source = f"""// MCP: template export ({fmt})
RunTemplate({path_literal(template_file)}, true);
{expand}{export_fn}({path_literal(out)});
Exit(0);
"""
    script = td / "export.1sc"
    script.write_text(source, encoding="utf-8", newline="\n")

    r = run_010(
        data_file=staged,
        action="script",
        action_file=script,
        timeout_sec=timeout_sec,
        exit_mode="exitnoerrors",
    )
    payload = result_dict(r)
    payload["workdir"] = str(td)
    payload["export_path"] = str(out)
    payload["staged_data"] = str(staged)
    if out.is_file():
        text = out.read_text(encoding="utf-8", errors="replace")
        max_chars = 200_000
        payload["export_text"] = text if len(text) <= max_chars else text[:max_chars]
        payload["export_truncated"] = len(text) > max_chars
        payload["export_bytes"] = out.stat().st_size
        payload["ok"] = r.ok
    else:
        payload["ok"] = False
        if not payload.get("error"):
            payload["error"] = f"{export_fn} did not create {out}"
    return payload


_HASHLIB_ALGOS = {
    "MD5": "md5",
    "SHA1": "sha1",
    "SHA256": "sha256",
    "SHA384": "sha384",
    "SHA512": "sha512",
    "CHECKSUM_MD5": "md5",
    "CHECKSUM_SHA1": "sha1",
    "CHECKSUM_SHA256": "sha256",
    "CHECKSUM_SHA384": "sha384",
    "CHECKSUM_SHA512": "sha512",
}


def run_checksum(
    data_file: Path,
    *,
    algorithm: str = "CHECKSUM_SHA256",
    start: int = 0,
    size: int = 0,
    timeout_sec: float = 120.0,
) -> dict:
    """Hash a file range.

    Uses Python ``hashlib`` for MD5/SHA* (reliable; large files under 010
    ``-noui`` have been observed to hang on open). Pass ``engine=\"010\"`` via
    the MCP tool for CRC/Adler through ChecksumAlgStr when needed.
    """
    import hashlib

    _ = timeout_sec
    data_file = data_file.resolve()
    if not data_file.is_file():
        raise FileNotFoundError(f"data file not found: {data_file}")
    key = algorithm.strip().upper()
    if not key.startswith("CHECKSUM_") and key not in _HASHLIB_ALGOS:
        key = f"CHECKSUM_{key}"
    # Allow bare names too
    hashlib_name = _HASHLIB_ALGOS.get(key) or _HASHLIB_ALGOS.get(key.replace("CHECKSUM_", ""))
    if hashlib_name is None:
        raise ValueError(
            f"Unsupported algorithm {algorithm!r} for the Python engine. "
            "Use MD5/SHA1/SHA256/SHA384/SHA512, or run_script_source with "
            "ChecksumAlgStr for CRC/Adler/etc."
        )
    file_size = data_file.stat().st_size
    if start < 0 or size < 0:
        raise ValueError("start and size must be non-negative")
    if start > file_size:
        raise ValueError(f"start {start} beyond file size {file_size}")
    nbytes = file_size - start if size == 0 else min(size, file_size - start)
    h = hashlib.new(hashlib_name)
    with data_file.open("rb") as f:
        f.seek(start)
        remaining = nbytes
        while remaining:
            chunk = f.read(min(1024 * 1024, remaining))
            if not chunk:
                break
            h.update(chunk)
            remaining -= len(chunk)
    return {
        "ok": True,
        "exit_code": 0,
        "error": None,
        "algorithm": key if key.startswith("CHECKSUM_") else f"CHECKSUM_{key}",
        "digest": h.hexdigest().upper(),
        "start": start,
        "size": nbytes,
        "method": "hashlib",
    }


def _parse_find_pattern(pattern: str) -> bytes:
    """Parse a simple 010-style pattern: plain text, or ``FFD8,h`` hex bytes."""
    p = pattern.strip()
    if p.lower().endswith(",h"):
        hexpart = p[:-2].replace(" ", "")
        return bytes.fromhex(hexpart)
    return p.encode("utf-8")


def run_find(
    data_file: Path,
    pattern: str,
    *,
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
    """Find pattern hits.

    Default ``engine=\"python\"`` does a fast byte scan (plain text or ``,h`` hex).
    ``engine=\"010\"`` uses FindAll (wildcards/regex) via a staged script bridge —
    note that opening multi‑MB files under ``-noui`` can hang on some installs.
    """
    _ = (whole_word, dir_down, timeout_sec)
    data_file = data_file.resolve()
    if not data_file.is_file():
        raise FileNotFoundError(f"data file not found: {data_file}")

    if engine == "010":
        return _run_find_010(
            data_file,
            pattern,
            match_case=match_case,
            whole_word=whole_word,
            method=method,
            dir_down=dir_down,
            start=start,
            size=size,
            max_hits=max_hits,
            timeout_sec=timeout_sec,
        )

    if method not in (0,):
        raise ValueError("Python engine only supports method=0; use engine='010' for wildcards/regex")

    needle = _parse_find_pattern(pattern)
    if not match_case and not pattern.strip().lower().endswith(",h"):
        # case-insensitive text: scan lowercased
        data = data_file.read_bytes()
        region = data[start : start + size if size else None]
        hay = region.lower()
        ndl = needle.lower()
    else:
        data = data_file.read_bytes()
        region = data[start : start + size if size else None]
        hay = region
        ndl = needle

    hits: list[dict] = []
    pos = 0
    while len(hits) < max_hits:
        i = hay.find(ndl, pos)
        if i < 0:
            break
        hits.append({"start": start + i, "size": len(ndl)})
        pos = i + 1
    # count all for total (cap scan effort for huge files by reusing find loop)
    total = len(hits)
    if len(hits) == max_hits:
        while True:
            i = hay.find(ndl, pos)
            if i < 0:
                break
            total += 1
            pos = i + 1
            if total > max_hits + 100_000:
                break

    return {
        "ok": True,
        "exit_code": 0,
        "error": None,
        "pattern": pattern,
        "hit_count_total": total,
        "hits": hits,
        "hits_truncated": total > len(hits),
        "method": "python",
    }


def _run_find_010(
    data_file: Path,
    pattern: str,
    *,
    match_case: bool,
    whole_word: bool,
    method: int,
    dir_down: bool,
    start: int,
    size: int,
    max_hits: int,
    timeout_sec: float,
) -> dict:
    from editor010_mcp.scriptlang import c_string

    td = Path(tempfile.mkdtemp(prefix="editor010_mcp_find_"))
    staged = stage_data(data_file, td)
    out = td / "find.txt"
    mc = "true" if match_case else "false"
    ww = "true" if whole_word else "false"
    d = 1 if dir_down else 0
    source = f"""// MCP: FindAll
TFindResults r = FindAll({c_string(pattern)}, {mc}, {ww}, {int(method)}, 0.0, {d}, {int(start)}, {int(size)});
local int h = FileNew("Text", true);
if (h < 0) Exit(-2);
local int i;
local int limit = r.count;
if (limit > {int(max_hits)}) limit = {int(max_hits)};
FPrintf(h, "count=%d\\n", r.count);
for (i = 0; i < limit; i++)
    FPrintf(h, "%Ld,%Ld\\n", r.start[i], r.size[i]);
FileSelect(h);
if (FileSave({path_literal(out)}) < 0) Exit(-3);
FileClose();
Exit(0);
"""
    script = td / "find.1sc"
    script.write_text(source, encoding="utf-8", newline="\n")
    r = run_010(
        data_file=staged,
        action="script",
        action_file=script,
        timeout_sec=timeout_sec,
    )
    payload = result_dict(r)
    payload["workdir"] = str(td)
    payload["pattern"] = pattern
    payload["staged_data"] = str(staged)
    payload["method"] = "010"
    hits: list[dict] = []
    total = None
    if out.is_file():
        lines = out.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in lines:
            if line.startswith("count="):
                try:
                    total = int(line.split("=", 1)[1])
                except ValueError:
                    total = None
                continue
            if "," in line:
                a, b = line.split(",", 1)
                try:
                    hits.append({"start": int(a.strip()), "size": int(b.strip())})
                except ValueError:
                    hits.append({"start": a.strip(), "size": b.strip()})
        payload["hit_count_total"] = total
        payload["hits"] = hits
        payload["hits_truncated"] = total is not None and total > len(hits)
    else:
        payload["ok"] = False
        if not payload.get("error"):
            payload["error"] = "find result file missing"
    return payload


def run_extract_range(
    data_file: Path,
    out_file: Path,
    start: int,
    size: int,
    *,
    timeout_sec: float = 120.0,
) -> dict:
    """Extract ``size`` bytes at offset ``start`` into ``out_file`` (pure Python).

    ``FileSaveRange`` has been observed to hang under ``-noui``; extraction
    does not need the editor.
    """
    _ = timeout_sec
    data_file = data_file.resolve()
    out_file = out_file.resolve()
    if not data_file.is_file():
        raise FileNotFoundError(f"data file not found: {data_file}")
    if start < 0 or size < 0:
        raise ValueError("start and size must be non-negative")
    file_size = data_file.stat().st_size
    if start > file_size:
        raise ValueError(f"start {start} beyond file size {file_size}")
    nbytes = min(size, file_size - start)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with data_file.open("rb") as src, out_file.open("wb") as dst:
        src.seek(start)
        remaining = nbytes
        while remaining:
            chunk = src.read(min(1024 * 1024, remaining))
            if not chunk:
                break
            dst.write(chunk)
            remaining -= len(chunk)
    return {
        "ok": True,
        "exit_code": 0,
        "error": None,
        "out_file": str(out_file),
        "start": start,
        "size": size,
        "out_bytes": out_file.stat().st_size,
        "method": "python",
    }
