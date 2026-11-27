"""从原始图纸重建结构证据图，并保留S4可独立读取的局部几何。"""
import json
from s4_structure import main
from s4lib.evidence_graph import build,digest


def output(drawings, structures, dest):
    graph=build(structures,drawings)
    graph["structures_content_sha256"]=digest(structures)
    (dest/"evidence-graph.json").write_text(json.dumps(graph,ensure_ascii=False,allow_nan=False,indent=2))


if __name__=="__main__":
    raise SystemExit(main(extension=output))
