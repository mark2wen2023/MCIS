"""将注记、来源、CAD边界和空间约束组织为可追溯的关系图。"""
import hashlib
import json
import re
from collections import defaultdict
from .installation import array_evidence, project_section


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,
                                     separators=(",",":")).encode()).hexdigest()


def build(structures, drawings):
    nodes={}; edges={}; installations=[]; arrays=[]; chains=[]
    by_src={d["sha256"]:d["data"] for d in drawings}
    notes={}; cross=defaultdict(list)
    def node(kind,key,**attributes):
        ident=kind+"-"+digest(key)
        record=dict(id=ident,kind=kind,attributes=attributes)
        if ident in nodes and nodes[ident]!=record:raise ValueError("图谱实体标识冲突")
        nodes[ident]=record
        return ident
    def edge(a,b,relation,basis,refs):
        record={"from":a,"to":b,"relation":relation,"basis":basis,"evidence":sorted(set(refs))}
        edges[digest(record)]=record
    def entity(src,instance):
        return node("cad",[src,instance],source_sha256=src,instance=instance)
    for r in structures["observations"]:
        s,h=r["source_sha256"],r["instance"]; key=[s,h]; ref=entity(s,h)
        n=node("annotation",key,text=r["text"],source_sha256=s,instance=h,layout=r["layout"],anchor_wcs=r["anchor_wcs"])
        notes[s,h]=n
        edge(n,ref,"read_from","direct",[ref])
        for role in r["mentioned_types"]:
            edge(n,node("role",role,name=role),"mentions_type","direct",[ref])
        for kind,vals in [("dimension",r["dimensions"]),("section_spec",r["profiles"]),("deck_level",r["deck_levels"])]:
            for i,v in enumerate(vals):
                val=node(kind,[key,i],value=v)
                edge(n,val,"specifies_"+kind,"direct",[ref])
                if kind=="section_spec":
                    cross[("spec",v["family"],tuple(v["values"]),v["unit"])].append((s,n,ref))
        if r["identity"]:
            cross[("identifier",r["identity"])].append((s,n,ref))
        scope=array_evidence(r)
        if r["frame_ranges"] or r["repetition"]:
            arrays.append(dict(annotation=n,**scope))
            for frame in scope["explicit_frames"]:
                station=node("frame_reference",[s,frame],source_sha256=s,number=frame)
                edge(n,station,"names_frame","direct",[ref])
                if r["type"] in ("bulkhead","transverse_bulkhead","frame","deck"):
                    cross[("role_and_frame",r["type"],frame)].append((s,n,ref))
            for a,b in scope["intervals"]:
                edge(n,node("interval",[s,a,b],source_sha256=s,start=a,end=b),"applies_in_range","direct",[ref])
            for f in scope["inferred_frames"]:
                edge(n,node("frame_reference",[s,f],source_sha256=s,number=f),"inferred_repetition","derived",[ref])
        for j,l in enumerate(r["leaders"]):
            rr=[entity(s,k) for k in l["handles"]]
            leader=node("leader",[key,j],method=l["method"],tip_wcs=l["tip_wcs"])
            edge(n,leader,"annotation_leader","derived",[ref,*rr])
            for k in l["target_instances"]:
                target=entity(s,k)
                edge(leader,target,"touches_drawing_entity","derived",[*rr,target])
            for k,c in enumerate(l.get("local_cell_candidates",[])):
                cr=[entity(s,v) for v in c["boundary_handles"]]
                contour=node("contour",[key,j,k],points_wcs=c["contour_wcs"],tip_relation=c["tip_relation"])
                edge(leader,contour,"bounds_candidate","derived",[*rr,*cr])
                for v in cr:edge(contour,v,"bounded_by","derived",cr)
        if r["type"] in {"deck","bulkhead","transverse_bulkhead","longitudinal_bulkhead","frame","bracket","longitudinal","strong_beam","floor","plate","double_bottom_plate"}:
            reasons=[]
            if not r["leaders"]:reasons.append("leader_missing")
            if not any(l.get("local_cell_status")=="closed_local_candidate" for l in r["leaders"]):reasons.append("no_unique_verified_local_outline")
            if not any(v["kind"]=="thickness" for v in r["dimensions"]):reasons.append("plate_thickness_unknown")
            if r["modeling_status"]=="conflicting_dimensions":reasons.append("contradictory_dimensions")
            chains.append(dict(annotation=n,role=r["type"],leaders=[dict(handles=l["handles"],status=l.get("local_cell_status","unresolved")) for l in r["leaders"]],issues=reasons))
        # Preserve an installation instruction separately from the identification of either member.
        match=re.search(r"(?:对应\s*(.+?)\s*处设|(?:安装于|贴于|装于|位于|焊于|installed on)\s*(.{1,80}))",r["text"],re.I)
        if match:
            target=(match[1] or match[2]).strip()
            edge(n,node("installation_instruction",key,target_phrase=target,matched_component=None),
                 "names_support_condition","direct",[ref])
    for key,records in cross.items():
        if len({s for s,_,_ in records})<2:continue
        g=node("cross_sheet_candidate",key,criterion=list(key),instance_identity_verified=False)
        for _,n,ref in records:edge(n,g,"candidate_agreement","candidate",[ref])
    for m in structures["local_models"]:
        s,h=m["source_sha256"],m["instance"]; ref=entity(s,h)
        n=notes[s,h]
        refs=[entity(s,k) for k in [*m["leader"],*m["contour"]["boundary_handles"],*m["unit_evidence_handles"]]]
        geom=node("local_solid",m["id"],asset=m["asset"],asset_sha256=m["asset_sha256"],
                  thickness_m=m["modeled_thickness_m"],thickness_unit_basis=m["thickness_unit_basis"])
        edge(n,geom,"reconstructed_from_local_topology","derived",[ref,*refs])
        placement=project_section(by_src[s],m,nodes[n]["attributes"]["layout"])
        inst=node("installation",m["id"],**placement)
        evidence=[entity(s,k) for k in placement.get("evidence_handles",[])]
        edge(geom,inst,"has_installation_constraint","derived",[ref,*refs,*evidence])
        installations.append(dict(model_id=m["id"],node=inst,**placement))
    for r in structures["components"]:
        if r["geometry_status"]!="research_geometry_verified":continue
        rr=[entity(t["source_sha256"],t["part_handle"]) for t in r["sources"]]
        geom=node("registered_solid",r["id"],asset=r["asset"],asset_sha256=r["asset_sha256"],bounds_m=r["bounds_m"])
        for e in rr:edge(geom,e,"verified_against_projection","derived",rr)
        installations.append(dict(model_id=r["id"],node=geom,status="registered_research",basis="two_registered_projections"))
    return dict(version="4.1",engineering_approved=False,nodes=sorted(nodes.values(),key=lambda v:v["id"]),
                edges=[edges[k] for k in sorted(edges)],installations=installations,arrays=arrays,chains=chains)
