"""完全虚构的独立算例。首次冻结后禁止覆盖原输入。数值表只给测站值。"""
from pathlib import Path
import hashlib,json,math
import ezdxf
import numpy as np
from scipy.integrate import quad
from scipy.optimize import minimize_scalar
P=Path(__file__).resolve().parent
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,allow_nan=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def create(case):
 if case=='A':
  L,D,scale=28.8,2.75,1000
  xs=[0,2.4,5.6,9.6,14.4,19,23.2,26.4,L]; zs=[0,.42,1.05,1.78,2.26,D]
  def beam(x):return 3.05*(.17+.83*math.sin(math.pi*x/L))
  def flare(z):return .38+.62*math.sin(math.pi/2*z/D)
 else:
  L,D,scale=19.2,1.95,1
  xs=[0,1.8,4.2,7.2,10.0,13.2,15.8,17.9,L];zs=[0,.33,.67,1.1,1.54,D]
  def beam(x):
   u=x/L;return 2.45*(.11+.71*(1-u)+1.70*u*(1-u))
  def flare(z):
   u=z/D;return .23+.77*(1.35*u-.35*u*u)
 def y(x,z):return beam(x)*flare(z)
 idir=P/'inputs'/case;idir.mkdir(exist_ok=True);path=idir/'lines.dxf'
 if path.exists():raise FileExistsError(path)
 doc=ezdxf.new('R2013');doc.units=4;ms=doc.modelspace()
 for name,col in [('BORDER',8),('NOTES',7),('GRID',4),('TABLE',7),('SECTION',3)]:doc.layers.new(name,dxfattribs={'color':col})
 def txt(x,z,s,layer='NOTES',sz=2.5):
  return ms.add_text(s,dxfattribs={'height':sz,'layer':layer,'insert':(x,z)}).dxf.handle
 def line(x0,y0,x1,y1,layer):ms.add_line((x0,y0),(x1,y1),dxfattribs={'layer':layer})
 def rect(x,y,w,h,layer):ms.add_lwpolyline([(x,y),(x+w,y),(x+w,y+h),(x,y+h)],close=True,dxfattribs={'layer':layer})
 unit='mm' if scale==1000 else 'm'
 rect(0,0,520,300,'BORDER');txt(12,280,'SYNTHETIC RESEARCH / OFFSET SHEET '+case)
 h_unit=txt(12,271,'HALF-BREADTH UNIT: '+unit);h_frame=txt(12,263,'FRAME: X FORWARD, Y PORT, Z UP. ORIGIN: AFT TRANSOM / CENTERLINE / BASELINE.')
 h_sym=txt(12,255,'SYMMETRIC ABOUT CENTERLINE. TABLE VALUES ARE HALF-BREADTHS.')
 ox,oy=(24,211) if case=='A' else (56,214)
 dx,dy=37,9
 if case=='A':cols=[f'ST {x:g} m' for x in xs]; rows=[f'WL {z:g} m' for z in zs[::-1]]
 else:cols=[f'WL {z:g} m' for z in zs];rows=[f'ST {x:g} m' for x in xs[::-1]]
 n=len(cols);m=len(rows)
 for j in range(n+2):line(ox+j*dx-3,oy+6,ox+j*dx-3,oy-m*dy-3,'GRID')
 for i in range(m+2):line(ox-3,oy+6-i*dy,ox+(n+1)*dx-3,oy+6-i*dy,'GRID')
 txt(ox,oy,'OFFSETS','TABLE')
 for j,s in enumerate(cols,1):txt(ox+j*dx,oy,s,'TABLE')
 for i,s in enumerate(rows,1):txt(ox,oy-i*dy,s,'TABLE')
 data=[]
 for i in range(m):
  for j in range(n):
   x,z=(xs[j],zs[::-1][i]) if case=='A' else (xs[::-1][i],zs[j])
   value=y(x,z);display=f'{value*scale:.2f}' if scale==1000 else f'{value:.5f}'
   h=txt(ox+(j+1)*dx,oy-(i+1)*dy,display,'TABLE');data.append(dict(x_m=x,z_m=z,value_m=float(display)/scale,handle=h))
 # 独立图框中的站剖示意，与数值表无共享实体；不过度披露隐藏横剖点。
 for i,x in enumerate(xs[::2]):
  x0=28+86*i; sy=17; xy=[(x0+y(x,z)*sy,z*sy+49) for z in zs]
  ms.add_lwpolyline(xy,dxfattribs={'layer':'SECTION'});line(x0,46,x0,50+D*sy,'SECTION');txt(x0,40,f'SECTION {x:g}',sz=2)
 txt(14,16,'MOULDED OFFSETS / RESEARCH DRAWING / ISSUE 01')
 doc.saveas(path)
 profile={'source_sha256':sha(path),'symmetric':True,'frame':{'axes':'x-forward,y-port,z-up','source':'lines.dxf#'+h_frame},'table':{'row_labels':rows,'column_labels':cols,'station_axis':'columns' if case=='A' else 'rows','stations_m_by_label':{f'ST {x:g} m':x for x in xs},'heights_m_by_label':{f'WL {z:g} m':z for z in zs},'unit':unit,'source':'lines.dxf#'+h_unit,'layout':'Model','plane_z':0.0,'tolerance':0.8},'source':'lines.dxf','symmetry_source':'lines.dxf#'+h_sym}
 write(P/'witness'/(case+'.json'),profile)
 B=2*max(beam(0),beam(L),-minimize_scalar(lambda x:-beam(x),bounds=(0,L),method='bounded',options={'xatol':1e-13}).fun)
 hold=[{'x_m':L*(i+.341)/12,'z_m':D*(j+.317)/6,'half_breadth_m':y(L*(i+.341)/12,D*(j+.317)/6)} for i in range(12) for j in range(6)]
 Q=lambda fun,a,b:quad(fun,a,b,epsabs=1e-12,epsrel=1e-12)[0]
 secs=[{'x_m':L*u,'area_m2':2*beam(L*u)*Q(flare,0,D)} for u in [.079,.197,.311,.454,.586,.719,.827,.944]]
 I=Q(beam,0,L);J=Q(lambda x:x*beam(x),0,L)
 hydro=[{'draft_m':D*u,'volume_m3':2*I*Q(flare,0,D*u),'area_m2':2*I*flare(D*u),'lcb_m':J/I} for u in [.225,.492,.731,.898]]
 write(P/'truth'/(case+'.json'),{'L_m':L,'B_m':B,'D_m':D,'table':data,'held_out':hold,'sections':secs,'hydrostatics':hydro,'unit':unit,'synthetic':True})
if __name__=='__main__':
 for k in ['A','B']:create(k)
