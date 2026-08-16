---
name: prevent-sleep
description: Prevent the computer from sleeping while a long-running Codex task executes, and release the sleep-prevention request when the task ends. Use when the user asks to keep the machine awake during long work (builds, tests, batch jobs, code generation, data processing, downloads) or reports that the computer fell asleep mid-task. Also use for starting, stopping, or checking the status of this stay-awake hold.
---

# Prevent Sleep

Prevent system sleep during a long task and release it when the task ends. The bundled script uses the Windows `SetThreadExecutionState` API from a hidden helper process, so no power settings are modified and the request is released automatically when the helper exits.

## Quick Start

Run the script from this skill's directory (or pass its full path). Windows PowerShell 5.1 or later is required.

1. Start before the long work:

   ```powershell
   ./scripts/stay-awake.ps1 start
   ```

2. Do the task.
3. Stop when the task ends, success or failure:

   ```powershell
   ./scripts/stay-awake.ps1 stop
   ```

4. Verify (optional):

   ```powershell
   ./scripts/stay-awake.ps1 status
   ```

Always stop in a finally-style step; never leave a task without stopping. If a stop is missed, the holder self-releases when the Codex process exits or after `-MaxHours` (default 12 h), but explicit stop is the contract.

## Script Reference

`scripts/stay-awake.ps1` supports three commands:

- `start` - spawn a hidden holder process that calls `SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)`. Prints the holder PID and state-file path.
- `stop` - kill the holder; Windows releases the sleep request automatically on process exit. Cleans the state file.
- `status` - report whether a holder is active, with start time, flags, parent PID, and last heartbeat.

Parameters:

- `-Token <name>` - per-task identifier when several holds run concurrently (default `default`).
- `-MaxHours <n>` - watchdog timeout after which the holder exits even if the task is still running (default 12).
- `-PreventDisplaySleep` - also keep the display on (`ES_DISPLAY_REQUIRED`). Omit by default so the screen can still turn off.

The holder re-asserts the request every 60 s, monitors a parent Codex process when one exists, and writes a heartbeat to the state file so `status` can confirm liveness.

## Platform Fallbacks

The bundled script is Windows-only. On other platforms:

- macOS: `caffeinate -s` for sleep prevention, `caffeinate -d` to also prevent display sleep; stop with Ctrl+C or by killing the process.
- Linux: `systemd-inhibit --what=idle:sleep --why="long Codex task" <command>` to wrap the task.

Note: verifying holds with `powercfg /requests` requires an elevated prompt on Windows; prefer `status` for confirmation.
