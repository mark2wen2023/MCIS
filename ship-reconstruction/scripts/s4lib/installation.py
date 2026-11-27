"""基于同一二维视图内的原图约束表达局部安装位置。"""
import re
import numpy as np
from .notes import normalized


def array_evidence(note):
    explicit = sorted({v["start"] for v in note["frame_ranges"] if v["start"] == v["end"]})
    intervals = [[v["start"], v["end"]] for v in note["frame_ranges"] if v["start"] != v["end"]]
    rule = note.get("repetition")
    phase = None
    inferred = []
    # 起止肋号是构件适用区间。只有明确给出起始相位及步长才枚举。
    text = normalized(note.get("text", ""))
    match = re.search(r"(?:从|自|starting at)\s*(?:Fr\.?\s*|肋位\s*)(-?\d+)\s*(?:起|开始)?[,， ]*(?:每\s*(\d+)\s*肋距|every\s*(\d+)\s*frames?)", text, re.I)
    if match and len(intervals) == 1:
        start = int(match[1]); step = int(match[2] or match[3])
        lo, hi = intervals[0]
        if step > 0 and lo == start and hi >= lo and hi.is_integer() and (hi-lo)/step <= 5000:
            phase = start
            inferred = [v for v in range(start, int(hi)+1, step) if v not in explicit]
    return dict(explicit_frames=explicit, intervals=intervals, rule=rule, phase=phase,
                inferred_frames=inferred, materialized_instances=[])


def project_section(data, model, layout):
    frame = model["frame_attachment"]
    missing = dict(status="local_only",ship_y_m=None,signed_thickness_direction=None)
    if not frame:
        return dict(**missing,reason="no_coincident_frame_edge")
    grid = frame["grid_handles"]; labels = frame["label_handles"]
    scope = labels[0].rpartition("/")[0]
    def same(row):
        return row["layout"] == layout and row["instance"].rpartition("/")[0] == scope
    texts = {t["instance"]: t for t in data["texts"] if same(t)}
    lines = {c["instance"]: np.array(c["samples"])[:, :2] for c in data["curves"]
             if same(c) and c["type"] == "LINE" and len(c["samples"]) == 2}
    if any(k not in texts for k in labels) or any(k not in lines for k in grid+frame["boundary_handles"]):
        return dict(**missing,reason="source_controls_missing")
    origin = lines[grid[0]].mean(axis=0)
    # Unequal tick lengths may displace their midpoints in the view normal.
    direction = np.array(texts[labels[-1]]["p"][:2])-texts[labels[0]]["p"][:2]
    if not np.linalg.norm(direction):
        return dict(**missing,reason="degenerate_grid")
    u = direction/np.linalg.norm(direction)
    if float(texts[labels[-1]]["text"]) < float(texts[labels[0]]["text"]): u=-u
    v = np.array([-u[1],u[0]])
    pitch = abs((lines[grid[-1]].mean(axis=0)-origin)@u /
                (float(texts[labels[-1]]["text"])-float(texts[labels[0]]["text"])))
    tol=max(1e-8,pitch*1e-5)
    hull=np.asarray(model["contour"]["contour_wcs"]); center=hull.mean(axis=0)
    xs=lines[frame["boundary_handles"][0]]@u
    xf=xs.mean()
    titles=[t for t in texts.values() if re.search(r"纵.*剖|侧视|longitudinal section|profile view",normalized(t["text"]),re.I)
            and abs((np.array(t["p"][:2])-center)@u)<pitch*12
            and abs((np.array(t["p"][:2])-center)@v)<pitch*14]
    bl=[t for t in texts.values() if re.fullmatch(r"B\.?\s*L\.?|基线|baseline",t["text"].strip(),re.I)]
    sols=[]
    for edge in frame["boundary_handles"]:
        for end in lines[edge]:
            z0=end@v
            segments=sorted((min(seg@u),max(seg@u),h) for h,seg in lines.items()
                            if max(abs(seg@v-z0))<=tol and np.ptp(seg@u)>tol)
            # BL labels must touch the same connected chain through the supported edge.
            chains=[]
            for a,b,h in segments:
                if chains and a<=chains[-1][1]+tol:
                    chains[-1][1]=max(chains[-1][1],b); chains[-1][2].append(h)
                else: chains.append([a,b,[h]])
            for left,right,handles in chains:
                if not left<=xf<=right: continue
                nearby=[t for t in bl if abs(np.array(t["p"][:2])@v-z0)<=t["height"]*.6
                        and left-t["height"]<=np.array(t["p"][:2])@u<=right+t["height"]]
                lefts=[t for t in nearby if np.array(t["p"][:2])@u<xf-tol]
                rights=[t for t in nearby if np.array(t["p"][:2])@u>xf+tol]
                if len(lefts)!=1 or len(rights)!=1:continue
                # Restrict section titles to the same side of BL as the part.
                ts=[t for t in titles if (np.array(t["p"][:2])@v-z0)*(center@v-z0)>0]
                if len(ts)!=1:continue
                sign=np.sign(np.array(ts[0]["p"][:2])@v-z0)
                sol=dict(status="partial_xz",frame_number=frame["frame_number"],
                         vertices_dx_z_m=(np.column_stack((hull@u-xf,(hull@v-z0)*sign))*model["scale"]["m_per_drawing_unit"]).tolist(),
                         ship_y_m=None,signed_thickness_direction=None,ship_x_origin_m=None,
                         height_convention="from_BL_towards_labelled_section",
                         evidence_handles=sorted(set([edge,*handles,*grid,*labels,*model["scale"]["handles"],
                                                      lefts[0]["instance"],rights[0]["instance"],ts[0]["instance"]])))
                if sol not in sols:sols.append(sol)
    return sols[0] if len(sols)==1 else dict(**missing,reason="missing_or_ambiguous_view_and_baseline")
