"""从设计方程出独立 CAD 与证据映射，冻结后不再改动。"""
import hashlib,json,math
from pathlib import Path
import ezdxf
import numpy as np
from forms import FORMS,vertical,width

ROOT=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def make_doc():
    doc=ezdxf.new('R2013');doc.units=6
    for name in ['CURVE','TEXT','GRID','REFERENCE']:doc.layers.add(name)
    return doc
def note(m,t,x,y,h=1.35):
    return m.add_text(t,dxfattribs={'layer':'TEXT','height':h,'insert':(x,y)}).dxf.handle
def line(m,a,b,layer='GRID'):
    return m.add_line(a,b,dxfattribs={'layer':layer}).dxf.handle
def write_doc(doc,folder,name):
    path=folder/name;doc.saveas(path)
    check=ezdxf.readfile(path).audit()
    if check.errors or check.fixes:raise ValueError(name,len(check.errors),len(check.fixes))
    return name,sha(path)

def table(form,side,folder):
    doc=make_doc();m=doc.modelspace()
    unit={'A':'mm','B':'cm','C':'m'}[form.code];fac={'mm':1000,'cm':100,'m':1}[unit]
    note(m,'TABLE OF OFFSETS / 型值表',3,68)
    note(m,'HALF-BREADTH UNIT: '+unit,3,63)
    note(m,'Port/starboard half-breadths are magnitudes; Y positive to port. X forward, Z up.',3,58)
    note(m,'PORT AND STARBOARD SYMMETRIC' if form.code!='C' else f'{side.upper()} half breadth',3,53)
    xx=[form.length*f for f in form.station_fractions];zz=list(form.drafts)
    st=[f'ST {x:.6g} m' for x in xx];wl=[f'WL {z:.6g} m' for z in zz]
    tr=form.code=='B'
    cols,rows=(wl,st) if tr else (st,wl)
    x0,y0,dx,dy=4.,40.,19.,8.
    for j in range(len(cols)+2):line(m,(x0+j*dx,y0),(x0+j*dx,y0-dy*(1+len(rows))))
    for i in range(len(rows)+2):line(m,(x0,y0-i*dy),(x0+dx*(1+len(cols)),y0-i*dy))
    def cell(i,j,text):return note(m,text,x0+dx*j+2,y0-dy*i-4.5)
    cell(0,0,'ST / WL')
    for j,t in enumerate(cols,1):cell(0,j,t)
    for i,t in enumerate(rows,1):cell(i,0,t)
    out=[]
    for i,x in enumerate(xx):
        for j,z in enumerate(zz):
            r,c=(i+1,j+1) if tr else (j+1,i+1);v=width(form,x,z,side)
            if abs(v)<1e-9:v=0.
            text=format(v*fac,'.8f').rstrip('0').rstrip('.') or '0'
            status='zero' if v==0 else 'numeric';hs=[]
            if form.code=='C' and side=='starboard' and (i,j)==(7,1):status='blank_unknown';v=None
            else:
                hs.append(cell(r,c,text))
                if form.code=='B' and (i,j)==(3,1):
                    hs.append(cell(r,c,format(v*fac+16.5,'.7f')));status='conflict';v=None
            out.append(dict(station_m=x,level_m=z,side=side,status=status,value_m=v,handles=hs,station_label=st[i],field_label=wl[j]))
    name,h=write_doc(doc,folder,f'offsets-{side}.dxf')
    return dict(file=name,sha256=h,cells=out,curves=[],controls=[])

def make_curves(form,folder):
    doc=make_doc();m=doc.modelspace();curves=[];controls=[]
    note(m,'LINES PLAN / 型线图 | BODY PLAN | WATERLINE PLAN',3,18)
    for i,f in enumerate(form.station_fractions[1:-1],1):
        x=f*form.length;k,top=vertical(form,f);dy=top-k;bx,by=65*i,55.
        block=doc.blocks.new('SECTION_'+str(i));ins=m.add_blockref(block.name,(bx,by));ih=ins.dxf.handle
        note(block,f'BODY PLAN / 横剖面图 | ST {x:.7g} m',-15,24)
        scales=3.
        for j,(y,z) in enumerate([(-5.,0),(5.,0),(-5.,5.),(5.,5.),(.7,1.2)]):
            h=note(block,f'CONTROL V{j} X={x:.9g} Y={y:g} Z={z:g} m',scales*y,scales*z)
            controls.append(dict(instance=ih+'/'+h,paper=[bx+scales*y,by+scales*z],point=[x,y,z],frame=ih))
        for side,sg in [('port',1.),('starboard',-1.)]:
            maxw=width(form,x,top,side)
            if form.code=='A':
                s=block.add_spline(degree=2,dxfattribs={'layer':'CURVE'})
                s.set_open_rational([(0,k*scales),(sg*maxw*scales,k*scales),(sg*maxw*scales,top*scales)],[1.,2**-.5,1.],degree=2)
            else:
                levels=[0,.25,.66,1.] if form.code=='B' else np.linspace(0,1,81)**2
                pts=[(sg*scales*width(form,x,k+dy*t,side),scales*(k+dy*t)) for t in levels]
                s=block.add_lwpolyline(pts,dxfattribs={'layer':'CURVE'})
            curves.append(dict(instance=ih+'/'+s.dxf.handle,handle=s.dxf.handle,source_kind=s.dxftype(),view='YZ',station_m=x,side=side))
    # 每条水线在独立图块投影 XY；签名控制点给出固定 Z，不借用剖面控制。
    for j,z in enumerate(form.drafts):
        b=doc.blocks.new('PLAN_'+str(j));bx,by=0.,-65.*(j+1);rr=2.
        ih=m.add_blockref(b.name,(bx,by)).dxf.handle
        note(b,f'WATERLINE PLAN / 半宽水线图 | WL {z:g} m',0,16)
        for n,(x,y) in enumerate([(0,-6.),(form.length,-6.),(0,6.),(form.length,6.),(.38*form.length,.3)]):
            h=note(b,f'CONTROL W{n} X={x:.8g} Y={y:g} Z={z:g} m',rr*x,rr*y)
            controls.append(dict(instance=ih+'/'+h,paper=[bx+rr*x,by+rr*y],point=[x,y,z],frame=ih))
        for side,sg in [('port',1.),('starboard',-1.)]:
            pts=[(rr*f*form.length,sg*rr*width(form,f*form.length,z,side)) for f in np.linspace(0,1,201)]
            e=b.add_lwpolyline(pts,dxfattribs={'layer':'CURVE'})
            curves.append(dict(instance=ih+'/'+e.dxf.handle,handle=e.dxf.handle,source_kind=e.dxftype(),view='XY',level_m=z,side=side))
    name,h=write_doc(doc,folder,'lines.dxf')
    return dict(file=name,sha256=h,cells=[],curves=curves,controls=controls)

if __name__=='__main__':
    dest=ROOT/'casebook';dest.mkdir(exist_ok=False)
    out=[]
    for form in FORMS:
        folder=dest/'inputs'/form.code;folder.mkdir(parents=True)
        files=[table(form,side,folder) for side in (['port','starboard'] if form.code=='C' else ['port'])]
        files.append(make_curves(form,folder));out.append(dict(case=form.code,files=files))
    save(dest/'source-truth.json',out)
