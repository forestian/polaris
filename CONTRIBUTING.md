# Contributing to Polaris

Thank you for your interest in contributing.

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.13+ | [python.org](https://www.python.org/) |
| Node.js | 20+ | [nodejs.org](https://nodejs.org/) |
| Git | any | — |
| Windows | 10/11 64-bit | Runtime target (build works on Linux for syntax/UI only) |

Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Running in Development Mode

```bash
# Start the UI dev server (hot-reload)
cd ui && npm install && npm run dev

# In a separate terminal, run the backend pointing at the dev server
python polaris.py
```

## Building the EXE

```bash
# Validates VERSION / CHANGELOG sync, builds UI, runs PyInstaller
python build.py
# → dist/polaris.exe
```

Requires all entries in `requirements.txt` to be installed, including PyInstaller.

## Project Structure

```
polaris.py          # Entry point + public API surface
src/
  api/              # Feature modules (k8s, reports, …)
  k8s.py            # Kubernetes client helpers
  topology.py       # Topology graph builder
  tools.py          # k9s / kubectl helpers
  runtime.py        # pywebview window lifecycle
ui/
  src/              # React frontend (Vite)
packaging/          # PyInstaller spec
tests/              # Unit tests (pure-Python logic, no GUI)
```

## Pull Requests

1. Fork the repository and create a feature branch.
2. Keep changes focused — one concern per PR.
3. Make sure `python build.py --check` passes before opening a PR.
4. Describe what the PR does and why in the PR body.

Bug reports and feature requests are welcome via [GitHub Issues](https://github.com/forestian/polaris/issues).
