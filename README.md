# Strawn

Strawn is Moriatz Labs’ original variable typeface. Every letter is built from lean, tapered vectors inspired by a toothpick: pointed at the ends, dense through the body, and engineered to remain one recognisable voice from interface labels to oversized headlines.

Version 0.7 rebuilds the family as a production Latin type system. It adds optical spacing and kerning, stable advances across weight changes, GF Latin Core language coverage, combining-mark positioning, corrected OpenType metadata, and four named instances.

## Install

```sh
npm install @moriatz-labs/strawn
```

Load the variable family once at the application entry point:

```ts
import "@moriatz-labs/strawn";
```

```css
.strawn {
  font-family: "Strawn", sans-serif;
  font-weight: 500;
}
```

## Family

- Axis: Weight (`wght`), 100–700
- Default: 500 Dense
- Named instances: 100 Fine, 300 Signature, 500 Dense, 700 Structural
- Style: Upright
- Character set: GF Latin Core, 319 encoded characters
- OpenType features: `kern`, `mark`, `mkmk`, `ccmp`
- Web format: variable WOFF2
- Desktop formats: variable TTF plus four overlap-free static TTFs

The construction uses a 1,000-unit em, 720-unit cap height, 520-unit x-height, 720-unit ascenders, and −220-unit alphabetic descenders. Typographic metrics provide additional room for accents without changing those visible alignment zones.

## Build and verify

```sh
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python scripts/build.py
.venv\Scripts\python scripts/test_font.py
.venv\Scripts\python scripts/test_determinism.py
```

The source of truth is `scripts/build.py`. It owns the original glyph skeletons, taper construction, masters, metrics, OpenType layout features, metadata, packaged CSS, manifests, and specimen artwork.

## Upgrading to 0.7

Version 0.7 intentionally corrects sidebearings, advances, kerning, overshoots, and vertical bounds. Existing layouts can reflow. Test product navigation, dense controls, tables, and headline wrapping before replacing an earlier build.

## License

Strawn is licensed under the SIL Open Font License 1.1. See `OFL.txt`.
