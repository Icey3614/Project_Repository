---
name: computer-use-reliable
description: "Reliable mouse/keyboard automation for Windows desktop apps using the Computer Use plugin. Use when automating any desktop app UI (clicking, typing, sending messages, submitting forms, navigating, scrolling, dragging, file dialogs) and you need dependable observe-act-verify workflows, or when Computer Use actions fail or behave unreliably: WebView/Electron apps with broken or shifting accessibility trees, buttons that ignore accessibility clicks, focus/typing quirks, stale element indexes, UI refresh lag, and post-action verification. Also use when the node_repl tool is not exposed and you need a fallback bridge, or when you need to locate UI controls from screenshots without image vision (color/shape/OCR perception)."
---

# Computer Use Reliable

## Overview

Computer Use can already perform anything a mouse and keyboard can do. This skill makes those actions *reliable*: it provides the observe → act → verify → recover loop, focus-safe input rules, element-vs-coordinate click decisions, a `node_repl` bridge fallback, and a screenshot-perception script for locating controls (color/shape/OCR) when the model cannot view images.

Always consult the Computer Use plugin's bundled docs for method signatures before starting: `docs/guidance.md` and `docs/api.md` next to its `SKILL.md`. This skill layers reliability rules on top.

## Core loop: Observe → Act → Verify → Recover

Never act on a stale observation. Element indexes, screenshot IDs, and coordinates are valid only for the window state that produced them.

1. **Observe**: capture window state. Use `get_window_state({ window, include_screenshot: false, include_text: true })` when you need the accessibility tree; add `include_screenshot: true` when you need geometry for coordinate clicks. A screenshot-backed capture caches element bounds; without it, element clicks may fail with "no cached bounds".
2. **Stop and inspect** the returned tree before choosing an element index.
3. **Act**: perform exactly one input action (click, type, key press).
4. **Verify**: immediately refresh state and confirm the action's effect using *semantic evidence* (input content, button enabled state, list preview, dialog closed), not just "no error".
5. **Recover**: if the effect did not happen, re-observe from scratch and apply the recovery rules in `references/troubleshooting.md`. Do not blindly retry the same action.

When input or refresh fails mid-way, the outcome is unknown: re-observe before retrying.

## Window selection

- Find the target with `sky.list_apps()` / `sky.list_windows()`. Select exactly one window; never reconstruct a window from guessed fields.
- If the app is running but missing a window, it may be minimized or hidden — use `list_windows()`. If absent, `launch_app` and refresh.
- Activate the window, then re-capture state. If an input call reports "point is over a non-target window", re-activate and retry once with a fresh observation.
- If a modal or secondary window is expected, list windows and capture that window.

## Perception: seeing the screen

Two perception channels, in this order:

1. **Accessibility tree** (`state.accessibility.tree`): fastest and index-based. Check `focused_element`, `selected_text`, `document_text` too.
2. **Screenshot** (`state.screenshots[0].url`): needed for coordinates, WebView buttons, and when the tree is empty or labels are unreliable.

If you can view screenshots directly, inspect them. If you cannot view images in this session, do not guess: save the screenshot to a file and run `scripts/perceive.mjs` to locate controls programmatically. See `references/perception.md`.

Save a screenshot from inside `node_repl`:

```js
const res = await fetch(state.screenshots[0].url);
const buf = Buffer.from(await res.arrayBuffer());
const { writeFileSync } = await import("node:fs");
writeFileSync(nodeRepl.cwd + "\\shot.png", buf);
```

## Input strategy

### Element click vs coordinate click

- **Element click** (`click({ window, element_index })`): prefer for native apps and tree elements that have cached bounds.
- **Coordinate click** (`click({ window, screenshotId, x, y })`): use when element click fails with "no cached bounds", when a control ignores accessibility clicks (common in WebView/Electron apps), or when you need pixel precision.
- If an element has no cached bounds, click its parent container instead, or switch to coordinates.

### Focus rules (the #1 cause of "typed but not sent")

- Before typing, confirm keyboard focus is actually in the editable surface. A click may succeed without focusing the editor.
- Check `state.accessibility.focused_element` after clicking. A focus of `RootWebArea` or an editor/input element usually means typing will land correctly. A focus of the window root (e.g. `0 窗口 ...`) often means the editor is *not* keyboard-focused.
- If focus is wrong, click the editable container again, try a coordinate click inside the input area, or navigate with `Tab`.
- `type_text` can insert text without granting keyboard focus. If a later key action (e.g., `Return` to send) depends on focus, verify focus first.
- After typing, refresh and verify the text is visible and dependent controls (e.g., a send button) became enabled.

### Keyboard and send actions

- Use `press_key` for controls (`Return`, `Tab`, `Escape`, arrows, chords). Do not embed control characters in typed strings.
- "Press Enter to submit/send" only works when the editor has real keyboard focus. Otherwise click the submit/send button by coordinates.
- Buttons in WebView apps often ignore element clicks — locate the button with `perceive.mjs` (color/shape/OCR) and coordinate-click it.

### UI refresh lag

Desktop apps (especially WebView-based ones) refresh their UI asynchronously. After a successful action, the tree may briefly show the old state. Wait ~1–2 seconds, re-observe, and verify with semantic evidence before concluding the action failed.

## Fallback: node_repl bridge

When the `node_repl` tool is not exposed in the session, use `scripts/bridge.mjs` to talk to the bundled Computer Use runtime directly. It auto-discovers `node_repl.exe`, handles the MCP handshake, answers "Allow Codex to use <app>?" approval prompts (only when the user explicitly requested the automation; use `--no-auto-approve` otherwise), and returns results as JSON. Run `node bridge.mjs --help` for usage.

Because each bridge call is a fresh process, write each cell self-contained: re-import `@oai/sky`, re-select the window by id, and act + verify inside one cell.

## References

- `references/webview-apps.md` — Electron/WebView/Chromium-embedded apps (QQ NT, WeChat, Slack, Discord, VS Code settings): when the tree lies, buttons ignore clicks, focus quirks.
- `references/native-apps.md` — UIA-friendly native apps: element clicks, `set_value`, keyboard navigation.
- `references/perception.md` — using `perceive.mjs` to locate controls from screenshots without image vision.
- `references/troubleshooting.md` — symptom → cause → fix table for common failures.
