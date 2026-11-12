"""Reproduce the report font from the pinned Google Fonts source (offline input)."""
import argparse
import hashlib
from pathlib import Path

SOURCE_SHA256 = 'a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da'
OUTPUT_SHA256 = 'eeb06b8a64fd04a2744d95579db1571b51027cda61ed78c62e4b730791525461'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path, help='Pinned NotoSansSC[wght].ttf')
    parser.add_argument('output', type=Path, help='Output static regular TTF')
    args = parser.parse_args()
    if args.upstream.resolve() == args.output.resolve():
        parser.error('Keep the upstream input unchanged; choose another output path')
    if hashlib.sha256(args.upstream.read_bytes()).hexdigest() != SOURCE_SHA256:
        parser.error('Unexpected upstream font SHA256; no output written')
    import fontTools
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont
    if fontTools.__version__ != '4.61.1':
        parser.error('Reproducible build requires fonttools==4.61.1')
    font = TTFont(args.upstream, recalcTimestamp=False)
    instantiateVariableFont(font, {'wght': 400}, inplace=True, updateFontNames=True)
    assert len(font.getBestCmap()) == 30890 and ord('艏') in font.getBestCmap()
    import io
    output = io.BytesIO()
    font.save(output)
    data = output.getvalue()
    if hashlib.sha256(data).hexdigest() != OUTPUT_SHA256:
        raise RuntimeError('Unexpected output SHA256; no output written')
    args.output.write_bytes(data)
    print(f'{OUTPUT_SHA256}  {args.output}')


if __name__ == '__main__':
    main()
