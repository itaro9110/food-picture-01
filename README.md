# The Golden Stack

A procedural picture of the best-looking breakfast: three golden pancakes
with maple syrup, melting butter, blueberries, strawberry halves and mint,
on a white plate in warm morning light. Made for the make.fun
food-picture-01 competition.

## Run

```sh
python3 main.py
```

The program writes `entry.png` (1024x1024, deterministic) to
`$MAKEFUN_OUTPUT_DIR` when set, otherwise to `/output` when that
directory exists and is writable, otherwise to `/tmp`. It never
defaults to a relative folder: the grader runs the entry as an
unprivileged user in a read-only container where only `/tmp` is
writable, so a relative output directory would crash the run.

## Verified

- `python3 -m py_compile main.py` passes.
- Two runs produce byte-identical PNGs (211,788 bytes, 1024x1024).
- A run as user `nobody` from a read-only directory with no
  `MAKEFUN_OUTPUT_DIR` set exits 0 and writes the same bytes to `/tmp`.

## How it is drawn

Everything is computed in pure Python 3.13 standard library code — no
images, no fonts, no network. A small soft-edged rasteriser (`Canvas`)
paints the scene back to front: cream wall and wooden table with a
vignette, the plate, three hand-offset pancakes with toasted speckles,
a glossy syrup cap with drips, a melting butter pat, berries, mint and
faint steam. A fixed seed keeps every run byte-identical.

## Files

- `main.py` — the whole entry: rasteriser, scene and PNG encoder
- `LICENSE` — MIT
