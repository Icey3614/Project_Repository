# Perception without image vision

Some sessions/models cannot view screenshots directly. When that is the case, do not guess pixel positions from memory. Use `scripts/perceive.mjs` to turn a screenshot into structured data: component bounding boxes by color, and OCR text with coordinates.

## Workflow

1. Capture the window state and save the screenshot to a file (see SKILL.md "Perception" section).
2. Run `perceive.mjs` on that file:

```bash
node scripts/perceive.mjs --info shot.png
node scripts/perceive.mjs --find-color 18,183,245 --tolerance 40 shot.png
node scripts/perceive.mjs --ocr chi_sim+eng shot.png
```

3. Read the returned JSON: `color` items and `ocr` items each have `x`, `y`, `width`, `height`, and `centerX`/`centerY` in screenshot (= window) coordinates.
4. Click with those coordinates: `sky.click({ window, screenshotId, x: item.centerX, y: item.centerY })` using the screenshot id from the same observation.

## Choosing a color for --find-color

- Blue primary buttons (send/submit): try `18,183,245` (QQ NT blue) or `13,110,253` (Bootstrap blue), then widen tolerance.
- Green primary buttons: `16,185,129` or `40,167,69`.
- Red destructive buttons: `220,53,69` / `239,68,68`.
- If unsure, sample the theme: run `--find-color` with a wide region and `--list-colors` to see dominant colors, or use OCR to read the button text first and take its bounding box.

Sample pixel colors from a screenshot without perception scripts (PowerShell + .NET):

```powershell
Add-Type -AssemblyName System.Drawing
$bmp = [System.Drawing.Bitmap]::FromFile("shot.png")
$c = $bmp.GetPixel(800, 600); "$($c.R),$($c.G),$($c.B)"
```

## OCR notes

- Language packs download on first use (network required) and cache under `%LOCALAPPDATA%\computer-use-reliable\tessdata`.
- Common languages: `eng`, `chi_sim` (Simplified Chinese), `chi_tra` (Traditional).
- OCR gives words with bounding boxes — useful for locating buttons by their label ("发送", "Send", "OK").
- Small UI text (buttons, badges) often OCRs poorly at normal window sizes (low confidence or garbled characters). For filled colored buttons, prefer `--find-color`; use OCR mainly for larger labels, headers, and confirmation text.
- If OCR fails (no network, slow, garbled), fall back to color/shape detection.

## Combining signals

- Prefer OCR text boxes for labeled controls.
- Use color/shape detection for icon-only controls (send arrow, search icon).
- Cross-check the accessibility tree: element names often confirm what the screenshot shows.
- When multiple candidates match, prefer the one with the most pixels, or the one inside the expected region (`--region x,y,w,h`).
