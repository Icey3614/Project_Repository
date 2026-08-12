# Clock

A real-time analog clock written in Python (tkinter), showing the current time
with hour, minute and second hands. A packaged Windows executable is generated
directly in this workspace as `Clock.exe`.

## Features

- Borderless window: no title bar or min/max/close buttons, the clock runs as
  a standalone dial that can be dragged anywhere. The background uses a
  transparent color key so only the circular dial is visible.
- Left-click the face: all three hands spin in random directions (each hand
  independently picks clockwise or counter-clockwise) for about 3 seconds,
  then land exactly on the current time with a smooth, seamless transition.
- Left-press and drag the face to move the clock anywhere on the screen.
- Right-click the face to open settings:
  - 12-hour or 24-hour dial;
  - Arabic or Roman numerals (24-hour mode always uses Arabic numerals);
  - dial color plus independent hour/minute/second hand colors, picked with
    the system color wheel;
  - dial size slider (360-640 px, default 480);
  - changes apply live for the current session only; every launch starts
    with the default configuration (no config file is written).
- Mechanical-watch details: a 7-segment weekday sub-dial (SUN-MON-...-SAT)
  on the left with a pointer to today, and a month/day window on the right.
- Optional circumscribed regular-polygon border (3-8 sides, e.g. triangle,
  square, pentagon ...): it rotates together with the hands on click and
  always stops with one side parallel to the bottom edge of the screen.
  Border color is configurable.
- The weekday sub-dial automatically takes a high-contrast color relative to
  the dial face when the face color is changed.
- Press `Esc` or use the Exit button in the settings window to quit.
- Custom clock icon in the taskbar button.

## Run from source

```powershell
python clock.py
```

## Build the .exe

Requires [PyInstaller](https://pyinstaller.org/):

```powershell
python -m pip install pyinstaller
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

The result is written to the parent folder (`..\Clock.exe`) so the repository
stays free of binary files.

## Version history

- `v1.0.0` — first release: real-time analog clock in a normal window.
- `v2.0.0` — borderless window, random spin animation on click, drag-to-move,
  settings window with 12/24-hour dial and Arabic/Roman numerals.
- `v3.0.0` — transparent dial (color-keyed background), color pickers for the
  dial and each hand, size control, weekday sub-dial and month/day window,
  taskbar icon, minimum size 360.
- `v3.1.0` — weekday sub-dial redesigned as seven dots (Monday on top) with a
  pointer and no divider lines, moved clear of the 9/10 numerals; month/day
  text now fits inside its window.
- `v3.2.x` — weekday dial enlarged, moved into the 10-11 sector, shorter
  contrasting red pointer, fine-tuned position.
- `v3.3.0` — optional circumscribed regular-polygon border (3-24 sides) that
  rotates with the spin animation, border color setting, weekday sub-dial
  auto-contrast with the dial face, sub-dial moved further inward.
- `v3.4.0` — fixes Roman numeral selection, smaller 24-hour and Roman
  numerals, border sides now chosen from a picker (3-8), manual/help button,
  auto-start on boot option, border color auto-contrasts with the dial.
