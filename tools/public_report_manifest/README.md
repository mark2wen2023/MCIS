# Local report-source preview

See ../../contracts/public-report-manifest-preview.md (repository root contracts directory) for the precise contract. This tool checks byte and declaration consistency only. It does not establish authenticity, public status, permission, semantic support, PDF validity or a correct page reference.

Run `python tools/public_report_manifest/manifest.py --manifest declaration.json --pdf report.pdf --output new-preview.json` from repository root. Test with pytest in this directory. No dependencies beyond Python standard library at runtime. Supported no-follow descriptor access is required; no unsafe fallback.

When you don't know publication date or printed page, use null rather than inventing a value. PDF page numbers are physical one-based page assertions, not inferred printed-page labels. Preserve conflicting evidence instead of silently correcting the manifest.
