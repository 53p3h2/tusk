# TUSK, a TUI process manager

A terminal-based process manager for running and managing multiple shell commands concurrently.

Built with [Textual](https://textual.textualize.io/) and [psutil](https://github.com/giampaolo/psutil).

## Features

- Run and manage multiple shell commands concurrently
- Side-by-side layout: process list (left) and live log viewer (right)
- Real-time stdout/stderr streaming
- System resource monitoring: CPU, memory, and per-process usage
- Start, stop, restart, and remove processes
- Sudo password support via masked input modal
- Save process logs to file
- Color-coded log output (errors in red, warnings in yellow)

## Requirements

- Python 3.10+
- Linux / macOS (uses `/bin/sh`)

## Installation

```bash
# Clone the repository
git clone https://github.com/53p3h2/tusk.git && cd tusk

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

## Usage

```bash
python3 app.py
```

### Key Bindings

| Key | Action |
|---|---|
| `n` | New task — enter a shell command to run |
| `s` | Stop the selected process |
| `r` | Restart the selected process |
| `d` | Remove the selected process from the list |
| `Ctrl+s` | Save the selected process's log to a file |
| `q` | Quit |

### Running Commands

1. Press `n` to open the command prompt modal.
2. Type any shell command (e.g., `ping 8.8.8.8`, `tail -f /var/log/syslog`).
3. Press Enter to run it — the process appears in the left panel with live output on the right.
4. Navigate the process list with arrow keys; the log viewer updates to show the selected process's output in real time.

### Sudo Commands

If the command starts with `sudo`, a password prompt appears automatically. Enter the password (masked input) and press Enter. Press Escape to skip — the command will run without sudo privileges and likely fail.

### Saving Logs

Select a process and press `Ctrl+s`. Enter a file path in the dialog and press Enter.

### Resource Monitor

The bottom panel shows system CPU%, memory usage, and per-process CPU/memory stats. It polls every 1.5 seconds using psutil.

## Architecture

```
tusk/
├── app.py                  # Entry point
├── requirements.txt        # Dependencies (textual, psutil)
├── process/
│   ├── runner.py           # Async subprocess execution, stdout/stderr streaming
│   ├── manager.py          # Process collection management (add/remove/restart)
│   └── monitor.py          # System and per-process resource monitoring
├── ui/
│   ├── dashboard.py        # Main layout, keyboard bindings, modal screens
│   ├── process_panel.py    # Process list table (DataTable)
│   ├── log_viewer.py       # Live log display with color-coded output
│   └── resource_panel.py   # CPU/memory stats display
└── utils/
    ├── helpers.py           # Status enum, formatting utilities
    └── logger.py            # Logging setup
```

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| [textual](https://textual.textualize.io/) | >= 0.40.0 | Terminal UI framework |
| [psutil](https://github.com/giampaolo/psutil) | >= 5.9.0 | System and process monitoring |
