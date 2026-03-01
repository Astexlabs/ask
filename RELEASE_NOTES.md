# Release notes

## v0.2.1 (Beta)

- **Improved escape-character handling** — Better catching and sanitization of escape characters in user input and generated commands.
- **Improved command recognition** — More reliable parsing and recognition of natural-language queries.

---

## v0.1.1 (Beta) — First version

**This is a beta release.** We’re still refining things; feedback and bug reports are welcome.

### What’s in this release

- **Natural-language CLI** — Describe what you want to do in plain English and get suggested shell commands.
- **Local mode (offline)** — Works without API keys using a built-in parser for queries like “find python files from the last hour” or “search for TODO in js files.”
- **Optional LLM backends** — Use OpenAI, Google Gemini, Ollama, or Azure OpenAI for richer suggestions (requires API key or local Ollama).
- **Interactive and one-shot** — Run `ask` for a prompt, or `ask 'your query'` for a direct query.
- **Command picker** — Choose from up to three suggested commands; copy or run them.
- **Recent history** — `ask --recent` to see recently run commands and results.
- **Config and setup** — `ask --setup` and `ask --config` to configure provider, keys, and options (stored in `~/.askrc`).
- **Python 3.9+** — Supported on Linux, macOS, and Windows.

### Install

```bash
pip install ask
```

### Quick start

```bash
ask --setup    # configure provider (or use default local mode)
ask            # interactive
ask 'find all .py files modified in the last 24 hours'
```

---

*Report issues and ideas on [GitHub](https://github.com/dtnewman/ask).*
