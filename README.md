# 010editor-mcp

MCP server for [SweetScape 010 Editor](https://www.sweetscape.com/010editor/).

## There is no plugin API

SweetScape [KB1015](https://www.sweetscape.com/support/kb/kb1015.html):

> At this time there is no API available for integration of 010 Editor with other programs.

This MCP does **not** load a DLL into 010. It automates what *does* exist:

| Layer | Mechanism | Docs |
|-------|-----------|------|
| **CLI** | `-template:`, `-script:`, `-replace:`, `-compare:`, `-goto:`, `-select:`, `-save:`, `-noui`, `-exitnoerrors`, … | [CommandLine.htm](https://www.sweetscape.com/010editor/manual/CommandLine.htm) |
| **Script bridge** | Ephemeral `.1sc` + result files (`ExportCSV`, `ExportXML`, `FileSave`, `FPrintf`, `FindAll`, `RunTemplate`, …) | [FuncInterface](https://www.sweetscape.com/010editor/manual/FuncInterface.htm) · [FuncIO](https://www.sweetscape.com/010editor/manual/FuncIO.htm) · [FuncTools](https://www.sweetscape.com/010editor/manual/FuncTools.htm) |
| **Python fallbacks** | `hashlib` checksums, byte extract, simple find — when headless 010 is a poor fit | — |
| **Reverse DLL** | Scripts/Templates `#link` *out* to your DLL (010 → you) | [ScriptDLL](https://www.sweetscape.com/010editor/manual/ScriptDLL.htm) |

Resource: `010editor://capabilities`

## Tools

| Tool | Backend |
|------|---------|
| `editor_status` | Locate install (`plugin_api: false`) |
| `run_template` | 010 CLI — validate `.bt` |
| `run_template_export` | Script bridge — `RunTemplate` + `ExportCSV`/`ExportXML` |
| `run_script` / `run_script_source` | 010 CLI / ephemeral `.1sc` |
| `checksum_file` | Python `hashlib` (MD5/SHA*) |
| `find_in_file` | Python scan (default) or 010 `FindAll` (`engine=010`) |
| `extract_range` | Python slice (`FileSaveRange` hangs under `-noui`) |
| `replace_in_file` | CLI `-replace:` |
| `compare_files` | CLI `-compare:` |
| `open_in_gui` | Non-blocking UI launch |
| `run_raw_cli` | Arbitrary argv escape hatch |

## Headless pitfalls (learned the hard way)

1. **No adjacent C string literals** in `.bt` / `.1sc` — keep `SPrintf` formats as one string.
2. **`Printf` ≠ stdout** under `-noui` — write `FileSave` / `ExportCSV` / `FPrintf` artifacts.
3. **Windows paths in scripts** must use doubled backslashes (`"D:\\temp\\a.txt"`). Forward slashes can make `FileSave` return success without creating the file.
4. **`FileOpen()` from a script can hang** under `-noui`. Prefer opening the data file on the CLI. Stage as `*.bin` (hardlink/copy) to avoid Template auto-run on extensions like `.djf`.
5. **`ExpandAll` + huge `uchar data[N]`** can hang / explode — `run_template_export` defaults `expand_all=false`.
6. **`FileSaveRange` hangs** under `-noui` on tested builds — extract via Python.
7. **010 is single-instance** — hung CLI processes block later runs. This server kills the child on timeout.
8. **Large-file opens** under `-noui` have been observed to hang on some installs; prefer Python tools or `open_in_gui` for multi‑MB blobs when headless stalls.

## Install

```bash
git clone https://github.com/b1tninja/010editor-mcp.git
cd 010editor-mcp
uv sync
```

## Cursor `mcp.json`

```json
{
  "mcpServers": {
    "010editor": {
      "command": "uv",
      "args": ["--directory", "D:/code/010editor-mcp", "run", "010editor-mcp"],
      "env": {
        "EDITOR010_EXE": "C:\\Program Files\\010 Editor\\010Editor.exe"
      }
    }
  }
}
```

## Related

- [010editor-reference](https://github.com/b1tninja/010editor-reference) — Binary Template / scripting docs
- [pfp](https://github.com/d0c-s4vage/pfp) — Python `.bt` subset (no 010 license)

## License

MIT — see [LICENSE](LICENSE). 010 Editor is commercial software from SweetScape; you need your own license.
