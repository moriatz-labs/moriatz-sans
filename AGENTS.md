# Strawn Typeface Repository Guidance

Strawn is Moriatz Labs' canonical variable system typeface.

## Source and artifacts

- `scripts/build.py` is the source of truth for glyph construction, interpolation masters, metadata, packaged CSS, and specimen artwork.
- Keep the family original. Do not import, trace, rename, or derive outlines from third-party fonts.
- Preserve the tapered toothpick construction across all masters while keeping the Regular master dark enough for interface text.
- Commit the generated `dist/` files because Git and GitHub installs consume the package directly.
- Commit the generated Moriatz Labs PNG and SVG proofs.

## Quality

- Create a local virtual environment and install the exact versions in `requirements.txt`.
- Run `python scripts/build.py` followed by `python scripts/test_font.py`.
- Confirm the variable `wght` axis remains 100–700 with a default of 500 Dense.
- Visually inspect the Moriatz Labs proof after every glyph or interpolation change.

## Release

- Font software and sources remain under OFL-1.1.
- Tag releases with semantic versions.
- Attach the variable TTF, variable WOFF2, Fine, Signature, Dense, and Structural TTFs, manifests, and Moriatz Labs proof to each GitHub release.
