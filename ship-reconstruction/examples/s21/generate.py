"""独立接口示例。生成明示平盖、对称、棱柱状船体的开发用 CAD。"""
from pathlib import Path
import sys
import json
import ezdxf
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import s2


def generate(case, dest):
    doc=ezdxf.new("R2013")
    layout=doc.modelspace()
    def text(x,y,s):
        layout.add_text(s,dxfattribs={"insert":(x,y),"height":1})
    for x in [0,16,32,48,64]: layout.add_line((x,0),(x,40))
    for y in [0,10,20,30,40]: layout.add_line((0,y),(64,y))
    text(2,35,"ST")
    for j,z in enumerate([0,1,2]):text(18+16*j,35,f"WL {z} m")
    for i,x in enumerate([0,3,6]):
        y=25-10*i
        text(2,y,f"ST {x} m")
        for j in range(3):text(18+16*j,y,"1.5")
    text(2,46,"OFFSET TABLE (m)")
    text(2,72,"HALF-BREADTH UNIT: m")
    text(2,52,"SYMMETRIC ABOUT CENTERLINE. TABLE VALUES ARE HALF-BREADTHS.")
    text(2,58,"OFFSET DOMAIN X 0 TO 6 Z 0 TO 2 M; FULL MOULDED HULL; FLAT CLOSURES")
    if case!="B":text(2,64,"FRAME: X FORWARD, Y PORT, Z UP. ORIGIN: AFT TRANSOM / CENTERLINE / BASELINE.")
    if case=="C":text(34.2,15.2,"1.9")
    dest.mkdir(parents=True,exist_ok=True)
    p=dest/"input.dxf"
    doc.saveas(p)
    g=s2.process(p,dest,None)
    (dest/"geometry.json").write_text(json.dumps(g,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
    return g

if __name__=="__main__":
    for case in "ABC":
        g=generate(case,Path(__file__).resolve().parent/case)
        print(case,g["modeling_admission"]["state"],g["validation"]["issues"])
