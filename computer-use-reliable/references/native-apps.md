# Native (UIA-friendly) apps

Native Windows apps (Explorer, classic Win32 dialogs, Office, many utilities) expose a real UI Automation tree with stable, clickable elements. Work with the tree first; it is fast and index-based.

## Prefer element actions

- Use `click({ window, element_index })` — bounds are cached when the observation included a screenshot.
- Use `set_value({ window, element_index, value })` for editable fields that expose a value (text boxes). Verify by refreshing and reading the value back.
- Use `perform_secondary_action` for actions like `Raise`, `Expand`, `Collapse`, `Scroll Up/Down` when available.
- Prefer keyboard navigation (`Tab`, arrows, `Return`, `Escape`, `Alt+<key>`) over hunting pixels.

## Cached bounds rule

Element clicks need cached geometry. Always capture with `include_screenshot: true` before an element click; if you only need the tree, you may capture without a screenshot first, then re-capture with a screenshot before clicking. If a click reports "element N has no cached bounds", re-observe with a screenshot and retry once.

## When the tree is empty or wrong

- Some native apps render content through custom controls (owner-drawn) that expose little or nothing. Fall back to screenshots + `perceive.mjs` coordinates.
- If a modal appears and `get_window_state` does not show it, call `sky.list_windows()` to find the modal/owned window and capture it.

## Dragging and scrolling

- Use `sky.drag({ window, screenshotId, from_x, from_y, to_x, to_y })` for canvas/list reordering, with coordinates from the latest screenshot.
- Use `sky.scroll({ window, x, y, scrollX, scrollY })` from inside the pane you want to scroll; click the pane first if needed.
- These take window-relative coordinates from the observation that produced the screenshot.
