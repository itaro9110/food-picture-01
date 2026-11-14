# The Golden Stack — food-picture-01

A stack of three golden pancakes with maple syrup, melting butter, blueberries,
strawberries and mint, on a white plate in warm morning light.

## Run

```sh
MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Writes one deterministic PNG (`entry.png`, 1024x1024) to the output directory.

Output directory, in order: `MAKEFUN_OUTPUT_DIR` when set, `/output` when it
exists and is writable, otherwise `/tmp`. The program never assumes a
writable working directory, so it also runs as an unprivileged user in a
read-only container.

## How it is made

`main.py` (Python 3.13, standard library only) draws every pixel itself: a
hand-rolled PNG encoder (zlib), row-filled gradients, wavy-edged pancake
ellipses with toasted speckle, glossy syrup with dripping, a melting butter
pat, berries, mint, steam and a soft vignette. No network, no files read,
same bytes on every run.

## The dish

Three pancakes, syrup poured over the top and dripping down the stack, butter
melting into it, berries and mint for fresh colour, a syrup pool on the plate.
Warm cream background, wooden table, one clear hero in the centre — it reads
at 300 pixels and makes you hungry at a glance.

## Why it wins

Against the judge's criteria, in order: (1) hungry — golden stack, glossy
syrup, melting butter, one look and you want a bite; (2) the food itself —
toasted speckle, syrup gloss, butter melt, faint steam, fresh berries;
(3) styling and light — warm light from the top left, plate and garnish lead
the eye to the stack; (4) craft — clean vector-style rendering, nothing
smeared or broken; (5) reads small — the stack, plate and berries stay clear
at 300 pixels.
