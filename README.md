# Strawn

Strawn is Moriatz Labs' original variable system typeface. Its letterforms are assembled from tapered geometric strokes: deliberately skeletal, technical, and "toothpick" in character, but dark enough to remain crisp at interface sizes.

Moriatz uses Strawn as its complete typographic voice across interface controls, body copy, headings, code, data, and brand moments. Version 0.6 strengthens mixed-case recognition with cap-line ascenders, full-depth descenders, a two-storey `a`, lower `b` and `d` bowls, and clearer `e`, `f`, `g`, and `Q` constructions.

## Install

```sh
npm install moriatz-sans
```

Load the variable font once at the application entry point:

```ts
import "moriatz-sans";
```

```css
.display-type {
  font-family: "Strawn", sans-serif;
  font-variation-settings: "wght" 500;
  letter-spacing: 0.08em;
}
```

## Family

- Axis: Weight (`wght`), 100–700, default 500 Dense
- Style: Upright
- Character set: printable Basic Latin plus core display punctuation
- Web format: WOFF2 variable font
- Desktop formats: variable TTF and Regular TTF

Lowercase letters use a 520-unit x-height, 680-unit ascenders, and −180-unit descenders. Capitals retain the 720-unit cap height, so mixed-case names and sentences remain distinct without reading as mismatched miniature capitals.

## Build

```sh
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python scripts/build.py
.venv\Scripts\python scripts/test_font.py
```

The source of truth is `scripts/build.py`: glyph skeletons, interpolation masters, metrics, metadata, packaging CSS, and the specimen artwork are generated reproducibly from that file.

## License

Strawn is licensed under the SIL Open Font License 1.1. See `OFL.txt`.
