# 010editor-mcp

MCP server for [SweetScape 010 Editor](https://www.sweetscape.com/010editor/) — run **Binary Templates** (`.bt`) and **Scripts** (`.1sc`) headlessly from an agent.

Requires a local 010 Editor install (this project does not redistribute 010 Editor).

## Tools

| Tool | Purpose |
|------|---------|
| `editor_status` | Locate `010Editor.exe` / `010editor` and report version |
| `run_template` | `010editor <file> -template:Foo.bt -noui -nowarnings -exitnoerrors` |
| `run_script` | Same for `.1sc` scripts (optional data file) |

CLI reference: [Command Line Parameters](https://www.sweetscape.com/010editor/manual/CommandLine.htm).

### Resolution rules

- Template/script **basename** is passed to `-template:` / `-script:`.
- **Working directory** is the parent of that `.bt` / `.1sc` (010 also searches its configured Templates/Scripts dirs).
- Prefer `exit_mode=exitnoerrors` so compile/run failures return a non-zero exit code.
- Override the binary with `EDITOR010_EXE` (full path).

### Template authoring tip

010 Editor **does not** concatenate adjacent C string literals. Keep `SPrintf` format strings as a **single** literal.

## Install

```bash
# clone
git clone https://github.com/b1tninja/010editor-mcp.git
cd 010editor-mcp
uv sync
```

Or:

```bash
pip install -e .
```

## Cursor / Claude Desktop config

Stdio MCP (example Cursor `mcp.json`):

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

After `pip install -e .`:

```json
{
  "mcpServers": {
    "010editor": {
      "command": "010editor-mcp"
    }
  }
}
```

## Manual CLI smoke test

```powershell
# from a directory that contains Brother_DJF.bt
& "C:\Program Files\010 Editor\010Editor.exe" `
  "D:\path\to\file.djf" `
  -template:Brother_DJF.bt `
  -noui -nowarnings -exitnoerrors
echo $LASTEXITCODE
```

## Related

- [010editor-reference](https://github.com/b1tninja/010editor-reference) — Binary Template / scripting docs skill
- [pfp](https://github.com/d0c-s4vage/pfp) — Python interpreter for a subset of `.bt` (no 010 license needed; incomplete vs full 010)

## License

MIT — see [LICENSE](LICENSE). 010 Editor is a commercial product of SweetScape Software; you need your own license to use this MCP against a real install.
