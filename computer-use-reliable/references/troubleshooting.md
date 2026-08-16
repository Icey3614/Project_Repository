# Troubleshooting: symptom → cause → fix

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `element N has no cached bounds` | Observation had no screenshot, or state changed | Re-observe with `include_screenshot: true`; click the parent container; or use a coordinate click |
| Click succeeds but nothing happens | WebView button ignores UIA clicks; or clicked the wrong element | Re-verify state; coordinate-click the real button (locate with `perceive.mjs`) |
| `coordinate input geometry is unavailable` | Stale/empty geometry cache | Re-capture state (screenshot) and retry once with the fresh observation |
| Typed text does not appear | Editor not focused | Click the editable container, verify `focused_element` shows `RootWebArea`/editor; coordinate-click inside the input; retry typing |
| `set_value` fails: "not settable" | WebView contenteditable | Use click-to-focus + `type_text` instead |
| Enter does not submit/send | Keyboard focus is not in the editor (type_text ≠ keyboard focus) | Click the editor for real focus first; or coordinate-click the send button |
| Pressing Ctrl+A + Delete does not clear input | WebView editor ignores select-all | Click input, press `End`, then `BackSpace` repeatedly |
| Action seems to have no effect, then double effect later | UI refresh lag; you retried too early | Wait 1–2 s, re-observe, verify semantic evidence before repeating |
| Send button still enabled / input not cleared after send | Send actually failed, or tree is stale | Re-observe after a short delay; check conversation/session list preview; coordinate-click send |
| App missing from `list_apps()` | App not running, or no targetable window | `launch_app` by id or exe path; refresh; or use `list_windows()` for minimized/hidden windows |
| Approval prompt ("Allow Codex to use ...?") | Computer Use confirmation flow | User must approve in-app; in bridge mode auto-approve only when the user explicitly requested the automation |
| Input reports "point is over a non-target window" | Window occluded / not foreground | `activate_window`, refresh state, retry once |
| Expected modal not visible in state | Modal is a separate window | `sky.list_windows()`, capture the modal window |
| Screenshot analysis finds nothing | Color tolerance wrong, or OCR unavailable | Widen tolerance; use `--list-colors`; check OCR cache/network; fall back to accessibility tree |
| Bridge: `node_repl.exe` not found | Runtime path changed | Set `NODE_REPL_EXE` env var or pass `--exe`; report the exact error |
| Bridge: "MCP client does not support form elicitation" | Handshake missing capability | Re-run with the bundled client (it sets `elicitation` capability); do not hand-write a different client |
| Bridge call times out | Long operation or stale kernel | Pass `--timeout-ms 120000`; re-run; if repeated, reset the kernel (`js_reset`) |

## General recovery rules

- After any failure, **re-observe from scratch** — never reuse indexes/coordinates/screenshot IDs from a failed attempt.
- If `list_apps`/`list_windows` times out: wait 2 s, retry once; if it fails again, report that the Computer Use helper may have failed.
- If the desktop is locked, stop and ask the user to unlock.
- If a window binding is lost, recover with `sky.get_window({ id, app })` from an earlier returned window, or re-list.
- If an action's outcome is unknown (input call threw or refresh failed), treat the state as unknown and re-observe before retrying.
