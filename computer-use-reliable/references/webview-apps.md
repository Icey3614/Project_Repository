# WebView / Electron / Chromium-embedded apps

Apps that render UI inside a browser engine (QQ NT, WeChat, Slack, Discord, VS Code settings, many new "NT" versions of Chinese apps) have predictable automation quirks. Recognize them by a `RootWebArea` document in the accessibility tree, or by the app showing no useful native controls.

## The tree is a hint, not ground truth

- Element indexes shift on every state capture and after any UI change.
- Labels come and go: the same input container may be `组 <ContactName>` in one capture and anonymous `组` in the next. Never hardcode indexes or labels.
- Text content inside the editor is often reported late or in a different child node than expected.
- Locate controls dynamically: parse the tree and find elements by their *relationship* to a stable anchor. Example: the chat input is "the last group/text element immediately before the send button"; the send button is "the button whose name contains 发送/Send/Submit".

## Buttons ignore accessibility clicks

WebView buttons frequently ignore `click({ element_index })` (UIA invoke). Symptoms: the call succeeds but nothing happens.

- Re-verify state after the click. If nothing changed, switch to a **coordinate click**:
  1. Capture state with `include_screenshot: true`.
  2. Locate the button with `scripts/perceive.mjs` (color/shape/OCR).
  3. `sky.click({ window, screenshotId, x, y })` at the button center.

## Focus and typing quirks

- `type_text` inserts text into whatever has *insertion* focus, but the app may not treat it as *keyboard* focus. A later `press_key` (e.g., `Return` to send) then does nothing.
- After clicking into an input, check `focused_element`:
  - `RootWebArea` or an editor/input element → keyboard focus is in the document; typing and Enter will work.
  - Window root (`0 窗口 ...`) → focus is not in the editor. Click the editable container again, coordinate-click inside the input area, or press `Tab` until the editor shows focus.
- If the input has leftover text, clear deterministically: click the input, press `End`, then `BackSpace` repeatedly, then re-type. `Control_L+a` + `Delete` often does nothing in WebView editors.
- `set_value` generally fails on WebView editors ("element is not settable"). Use click-to-focus + `type_text` instead.

## Submit / send reliably

- Prefer clicking the send/submit button by coordinates (see above).
- If you press Enter instead, it only works with real keyboard focus in the editor.
- After sending, the send button should disable and the input should clear. Those are your verification signals.

## Refresh lag

- After actions, WebView UIs update asynchronously. The tree may show stale state for 1–2 seconds.
- Wait briefly (a `await new Promise(r => setTimeout(r, 1200))` inside node_repl), re-observe, then verify with semantic evidence (list preview changed, input cleared, button disabled).
- Do not treat "tree still shows old state" as failure and repeat the action — you may duplicate the side effect (e.g., send the message twice).

## Verified example: QQ NT send message

1. Find the QQ window, activate it, capture state with screenshot + text.
2. In the tree, find the send button index (button containing 发送). The input container is the group/text element just before it.
3. Click the input container (element click), refresh, verify `focused_element` indicates the document/editor.
4. Clear leftovers (`End` + `BackSpace` x N), type the message, refresh, verify the text is present and the send button became enabled.
5. Send: coordinate-click the send button (locate it via `perceive.mjs` blue-button heuristic if needed) OR press `Return` if focus is confirmed.
6. Verify: input cleared, send button disabled, session/conversation list preview shows the message.
