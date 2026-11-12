# Report font

`NotoSansSC-Regular.ttf` is a static weight-400 instance of the official Google Fonts Noto Sans SC variable font. All 30,890 upstream Unicode mappings are retained; this is not a report-specific subset. The complete SIL Open Font License 1.1 is in `OFL-NotoSansSC.txt`. Upstream copyright and font metadata are retained. The upstream Reserved Font Name is `Source`; the family used here is `Noto Sans SC`.

## Source and reproducibility

Pinned source: https://github.com/google/fonts/tree/a85815a42757630ce188fdad368c2dfc444d4773/ofl/notosanssc

Download `NotoSansSC[wght].ttf` from that revision. Its SHA256 must be:
`a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da`.

Use Python with `fonttools==4.61.1` in a build-only environment:

```sh
python tools/build-report-font.py '/path/to/NotoSansSC[wght].ttf' fonts/NotoSansSC-Regular.ttf
```

The script verifies input/output hashes, instantiates `wght=400`, updates style names and preserves the upstream timestamp. It never edits the original input. Output is 10,595,932 bytes, SHA256:
`eeb06b8a64fd04a2744d95579db1571b51027cda61ed78c62e4b730791525461`.

This replaces the previous incomplete font (2,534,228 bytes), which could not render the maritime character `艏` (U+824F). No public report text is modified. PDF export embeds only the used glyph subset, not the entire font. DOCX requests `Noto Sans SC`; recipient systems need the font or a suitable CJK fallback. Microsoft Word pagination is not guaranteed by Linux rendering tests.

## Regression

Run from `service/` with the service environment:

```sh
.venv/bin/python -m pytest -q tests/test_reports_font_coverage.py
.venv/bin/python -m pytest -q tests/test_reports*
```

The tests use the actual production font and fresh public-case reports, checking glyph coverage, PDF text extraction, provenance review/missing-data markers, and Draft state. Poppler `pdftotext` is required as in the existing export tests. Manual rendering remains necessary to check visual layout.
