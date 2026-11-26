"""Map located CAD cells to offset observations, preserving the existing review boundary."""

from copy import deepcopy
import math
import re

from .offset_semantics import normalize_row
from .offset_validation import validate_offsets


def offsets_for_review(
    table,
    *,
    station_axis,
    stations_m_by_label,
    heights_m_by_label,
    unit,
    mapping_source,
):
    """Return observations ready for prepare_offset_samples, without issuing approvals.

    The caller must supply the axis meaning, SI station/height coordinates,
    raw breadth unit, and a traceable source for that mapping. The XY table
    frame describes the paper layout; it never defines the ship coordinate frame.
    """
    if table.get("review") != "pending" or table.get("lofting_authorized") is not False:
        raise ValueError("pending table candidate required")
    if table.get("issues") != [] or not table.get("cells") or not table.get("frame"):
        raise ValueError("unresolved table evidence")
    if station_axis not in ("row", "column") or unit not in ("mm", "m"):
        raise ValueError("explicit station axis and supported breadth unit required")
    if not isinstance(mapping_source, dict) or not all(
        isinstance(mapping_source.get(k), str) and mapping_source[k].strip()
        for k in ("document_id", "locator")
    ):
        raise ValueError("mapping source reference required")
    document = table.get("document")
    doc_id = document.get("sha256") if isinstance(document, dict) else None
    if not isinstance(doc_id, str) or not re.fullmatch(r"[0-9A-Fa-f]{64}", doc_id):
        raise ValueError(
            "source drawing fingerprint must be 64 hexadecimal SHA-256 characters"
        )
    height_axis = "column" if station_axis == "row" else "row"
    indexed = {(cell[station_axis], cell[height_axis]): cell for cell in table["cells"]}

    def order(mapping, axis):
        if not isinstance(mapping, dict) or set(mapping) != {
            c[axis] for c in table["cells"]
        }:
            raise ValueError("mapping must cover exactly the located header labels")
        values = list(mapping.values())
        if not all(type(v) in (float, int) and math.isfinite(v) for v in values) or len(
            set(values)
        ) != len(values):
            raise ValueError("axis coordinates must be distinct finite numbers")
        return sorted(mapping, key=mapping.get)

    stations = order(stations_m_by_label, station_axis)
    heights = order(heights_m_by_label, height_axis)
    if len(indexed) != len(table["cells"]) or len(indexed) != len(stations) * len(
        heights
    ):
        raise ValueError("incomplete or duplicate cell coordinates")
    xs = [stations_m_by_label[s] for s in stations]
    zs = [heights_m_by_label[h] for h in heights]
    rows = []
    for height, z in zip(heights, zs):
        cells = [indexed[s, height] for s in stations]
        source_cells = []
        for c in cells:
            texts = c["texts"]
            if c["status"] == "blank_unknown" and not texts:
                source_cells.append(None)
            elif (
                c["status"] == "numeric_text"
                and len(texts) == 1
                and c["numeric_lexeme"] == texts[0]["raw_text"].strip()
            ):
                source_cells.append(
                    {"text": texts[0]["raw_text"], "handle": texts[0]["handle"]}
                )
            else:
                raise ValueError("cell has unresolved or inconsistent source text")
        locator = "drawing header " + str(cells[0][height_axis + "_header"]["handle"])
        observations = normalize_row(source_cells, xs, z, unit, doc_id, locator)
        for observation, cell in zip(observations, cells):
            observation["source"].update(
                {
                    "mapping_source": deepcopy(mapping_source),
                    "station_axis": station_axis,
                    "breadth_unit": unit,
                    "table_frame": deepcopy(table["frame"]),
                    "table_cell": deepcopy(
                        {
                            k: cell[k]
                            for k in (
                                "row",
                                "column",
                                "texts",
                                "row_header",
                                "column_header",
                                "local_bounds",
                                "boundary_segments",
                            )
                        }
                    ),
                }
            )
        rows.extend(observations)
    diagnostics = validate_offsets(rows)
    return {
        "rows": rows,
        "issues": [],
        "diagnostics": diagnostics,
        "stations_m": xs,
        "heights_m": zs,
        "drawing_issues": list(table.get("source_issues", [])),
        "review": "pending",
        "candidate_complete": not any(
            diagnostics[k] for k in ("missing_rows", "conflicting_rows", "invalid_rows")
        ),
        "lofting_authorized": False,
    }
