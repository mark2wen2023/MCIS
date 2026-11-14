# Citation occurrence export independent review

## RCO-D01 — PDF collapsed significant spaces in trace scalar values (fixed)

The initial implementation put JSON scalar display values into ordinary ReportLab Paragraph text. Actual PDF generation and `pdftotext -layout` readback changed `sentenceId="ID  two"` to `sentenceId="ID two"`, and `sourceRef="line  two  spaces"` to `sourceRef="line two spaces"`. This contradicted the exact declaration-preservation contract; DOCX was unaffected.

The implementation owner fixed trace-only JSON scalar display by encoding literal whitespace as Unicode escapes. Original report sentence text is unchanged. Independent PDF/DOCX file readback now JSON-decodes field values and verifies consecutive spaces, nonbreaking spaces, tab/newline and literal markup/quotes roundtrip exactly. The original freeze remains historical; r1 freeze is current.

No remaining blocking defect found within the reviewed exporter/trace scope. Occurrence markers are snapshot positions, not authenticated citation identity, original-source verification or semantic/factual approval. Tests do not establish model capability or visual fidelity in all readers.

Final independent result:20 independent tests and combined focused47/47 pass, zero skips; r1 freeze4/4 matches. RCO-D01 closed by repair and readback verification.
