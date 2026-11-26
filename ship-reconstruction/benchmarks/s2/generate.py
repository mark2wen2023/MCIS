"""独立生成合成 CAD 交换件并从创作记录导出真值，禁止读待测识别器。"""
from pathlib import Path
from math import radians,cos,sin
import argparse,json,hashlib
import ezdxf
from ezdxf.entities import factory,acad_table
from ezdxf.lldxf.extendedtags import ExtendedTags
P=Path(__file__).resolve().parent
CASES=[
 'plain','transpose','rot30','rot45','rot90','rot180','mirrorX','mirrorY','rot-mirror','irregular','nonuniform-grid','unit-mm','unit-cm','bilingual','mtext','ruled-polyline','thin-grid','no-grid','extra-note','block','block-rotate','nested-block','special-station','hole-and-zero','repeat-value','competing-values','dash','merged-value','native-table','two-tables','multi-drawing','section-polyline','waterline-spline','buttock-line','arc','bulge','capacity','arrangement','structure','control-valid','control-collinear','control-conflict','no-alignment','unknown-unit','paperspace','no-blank-fill']
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def native(doc,space,grid,xy,dx,dy):
 b=doc.blocks.new_anonymous_block('T')
 for i,row in enumerate(grid):
  for j,t in enumerate(row):
   if t:b.add_text(t,dxfattribs={'height':1.75,'insert':(j*dx,-i*dy)})
 h=doc.entitydb.next_handle();ts=[(0,'ACAD_TABLE'),(5,h),(330,space.layout_key),(100,'AcDbEntity'),(8,'0'),(100,'AcDbBlockReference'),(2,b.name),(10,xy[0]),(20,xy[1]),(30,0),(100,'AcDbTable'),(280,0),(342,None),(343,b.block_record_handle),(11,1),(21,0),(31,0),(90,0),(91,len(grid)),(92,len(grid[0]))]
 ts += [(141,dy) for _ in grid]+[(142,dx) for _ in grid[0]]
 for row in grid:
  for t in row:ts += [(171,1),(173,0),(174,0),(175,0),(176,0),(1,t)]
 raw=''.join(str(k)+'\n'+str(v)+'\n' for k,v in ts if v is not None)
 ent=factory.load(ExtendedTags.from_text(raw),doc);doc.entitydb.add(ent);space.add_entity(ent);return ent.dxf.handle
def sheet(path,n,variant):
 doc=ezdxf.new('R2013');doc.units=4
 for lay in ['TEXT','GRID','CURVE','NOTES','CONTROL']:doc.layers.new(lay)
 ms=doc.modelspace();facts={'file':path.name,'variant':variant,'cells':[],'curves':[],'controls':[],'expected_classes':[]}
 def mt(space,t,pt,layer='TEXT',usemt=False):
  attrs={'layer':layer,'insert':pt}
  return (space.add_mtext(t,dxfattribs={'char_height':1.7,**attrs}) if usemt else space.add_text(t,dxfattribs={'height':1.7,**attrs})).dxf.handle
 def note(t,pt):return mt(ms,t,pt,'NOTES')
 category={'capacity':('capacity','TANK CAPACITY PLAN / 舱容图'),'arrangement':('arrangement','GENERAL ARRANGEMENT / 总布置图'),'structure':('structure','MIDSHIP STRUCTURAL ARRANGEMENT / 基本结构图'),'section-polyline':('section','BODY PLAN / 横剖面图'),'waterline-spline':('lines','LINES PLAN / 型线图'),'buttock-line':('lines','BUTTOCK PLAN / 纵剖线图'),'arc':('lines','LINES PLAN / 型线图'),'bulge':('lines','LINES PLAN / 型线图')}
 if variant in category:
  cat,title=category[variant];facts['expected_classes']=[cat];note(title,(12,160))
  if variant=='waterline-spline':
   e=ms.add_spline(fit_points=[(0,0),(7,3),(19,5),(33,2)],dxfattribs={'layer':'CURVE'});kind='SPLINE'
  elif variant=='arc':
   e=ms.add_arc((14,4),6,18,131,dxfattribs={'layer':'CURVE'});kind='ARC'
  elif variant=='bulge':
   e=ms.add_lwpolyline([(0,0,.18),(19,5,-.10),(41,1,0)],format='xyb',dxfattribs={'layer':'CURVE'});kind='LWPOLYLINE'
  elif variant=='buttock-line':
   e=ms.add_line((0,0),(28,2),dxfattribs={'layer':'CURVE'});kind='LINE'
  elif variant=='section-polyline':
   e=ms.add_polyline2d([(0,0),(2,1),(2.5,2.4),(2.7,4.)],dxfattribs={'layer':'CURVE'});kind='POLYLINE'
  else:e=None
  if e:facts['curves'].append({'handle':e.dxf.handle,'dxf_kind':kind})
  if variant=='capacity':note('TANK 01       VOLUME m3       CENTROID m',(18,102));note('TK1                5.2                    3.1',(18,80))
 elif variant.startswith('control-') or variant=='no-alignment':
  facts['expected_classes']=['lines'];note('LINES PLAN / 型线图',(12,160))
  ms.add_line((2,10),(75,70),dxfattribs={'layer':'CURVE'})
  marker=[(0,0),(2,2),(4,4),(6,6),(8,8)] if variant=='control-collinear' else [(0,0),(8,0),(0,5),(9,6),(4,3),(2,7)]
  if variant=='no-alignment':marker=[]
  for i,(x,y) in enumerate(marker):
   wx=65+2*x-.5*y;wy=15+.4*x+1.6*y;xyz=[float(x),0.,float(y)]
   if variant=='control-conflict' and i==len(marker)-1:xyz=[79.,0.,41.]
   h=mt(ms,f'CONTROL P{i} X={xyz[0]:g} Y=0 Z={xyz[2]:g} m',(wx,wy),'CONTROL');facts['controls'].append(dict(id='P'+str(i),source_xy=[wx,wy],target_xyz=xyz,handle=h))
  facts['alignment_target']='verified' if variant=='control-valid' else 'no_verified'
 else:
  note('TABLE OF OFFSETS / 型值表',(19,185));facts['expected_classes']=['offset_table']
  u='cm' if variant=='unit-cm' else 'mm' if variant=='unit-mm' or n%3==1 else 'm'
  if variant=='unknown-unit':u=None
  note('HALF-BREADTH UNIT: '+u if u else 'OFFSET VALUES: UNIT UNRECORDED',(19,175))
  note('STATION COORDINATES AND WATERLINE HEIGHTS IN m',(19,166))
  lay=doc.layouts.new('QA-SHEET') if variant=='paperspace' else ms
  angle={'rot30':30,'rot45':45,'rot90':90,'rot180':180,'rot-mirror':30,'block-rotate':45}.get(variant,0)
  c,s=cos(radians(angle)),sin(radians(angle));sx=-1 if variant in ('mirrorX','rot-mirror') else 1;sy=-1 if variant=='mirrorY' else 1
  def transform(x,y,ox,oy):return (ox+c*sx*x-s*sy*y,oy+s*sx*x+c*sy*y)
  def table(no,origin):
   ox,oy=origin;block=variant in ('block','block-rotate','nested-block');target=doc.blocks.new('OFFSET_FRAGMENT') if block else lay
   if block and variant=='nested-block':top=doc.blocks.new('OFFSET_ASSEMBLY');top.add_blockref(target.name,(0,0));lay.add_blockref(top.name,(ox,oy),dxfattribs={'rotation':angle})
   elif block:lay.add_blockref(target.name,(ox,oy),dxfattribs={'rotation':angle})
   pos=lambda x,y:(x,y) if block else transform(x,y,ox,oy)
   xs=[0.,2.5,5.75,10.25,15.3][:4+(n%2)];zs=[.2,.83,1.58,2.4] if variant=='irregular' else [0,.5,1.75][:2+(n%2)]
   if no:xs=[x+20 for x in xs]
   st=[f'ST {x:g} m' for x in xs];wl=[f'WL {z:g} m' for z in zs]
   if variant=='special-station':st[1]='ST 2½';xs[1]=2.5
   if variant=='bilingual':st=[f'站位 {x:g} m' for x in xs];wl=[f'水线 {z:g} m' for z in zs]
   transpose=variant=='transpose';cols=wl if transpose else st;rows=st if transpose else wl;xx=[0]+[29+24*j+(j*j*1.3 if variant=='nonuniform-grid' else 0) for j in range(len(cols))];yy=[0]+[-10-12*i-(i*i*.8 if variant=='nonuniform-grid' else 0) for i in range(len(rows))]
   grid=[['OFFSETS']+cols]+[[row]+['']*len(cols) for row in rows];pending=[];handles={}
   for i in range(len(rows)):
    for j in range(len(cols)):
     si,wi=(i,j) if transpose else (j,i);val=round(.25+.017*n+.11*si+.32*wi+.04*no,4);rf=u or 'm';f={'m':1,'cm':100,'mm':1000}[rf]
     text=f'{val*f:g}';status='numeric'
     if variant in ('hole-and-zero','no-blank-fill') and i==0 and j==0:text='';status='blank_unknown';val=None
     if variant=='hole-and-zero' and i==0 and j==1:text='0';status='zero';val=0.
     if variant=='dash' and i==0 and j==1:text='—';status='non_numeric';val=None
     if variant in ('repeat-value','competing-values') and (i,j)==(0,1):status='duplicate' if variant=='repeat-value' else 'conflict';val=val if status=='duplicate' else None
     if variant=='merged-value' and i==0 and j in (1,2):text='';status='merged_unknown';val=None
     grid[i+1][j+1]=text
     pending.append(dict(row=i,column=j,station_label=st[si],field_label=wl[wi],station_m=xs[si],level_m=zs[wi],status=status,value_m=val if u else None,unit=u,raw=text,source_xy=transform(xx[j+1],yy[i+1],ox,oy)))
   if variant=='native-table':
    h=native(doc,lay,grid,(ox,oy),24,12);facts['native_handle']=h
   else:
    for i,row in enumerate(grid):
     for j,t in enumerate(row):
      if t:handles[i,j]=[mt(target,t,pos(xx[j],yy[i]),usemt=variant=='mtext')]
      if variant in ('repeat-value','competing-values') and (i,j)==(1,2):
       handles[i,j].append(mt(target,t if variant=='repeat-value' else str(float(t)+123),pos(xx[j],yy[i])))
    def edge(a,b):
     at={'layer':'GRID','lineweight':13 if variant=='thin-grid' else -1};pa,pb=pos(*a),pos(*b)
     if variant=='ruled-polyline':target.add_lwpolyline([pa,pb],dxfattribs=at)
     else:target.add_line(pa,pb,dxfattribs=at)
    if variant!='no-grid':
     xx2=[x-2 for x in xx]+[xx[-1]+21];yy2=[y+5 for y in yy]+[yy[-1]-7]
     for k,x in enumerate(xx2):
      if variant=='merged-value' and k==3:
       edge((x,yy2[0]),(x,yy2[1]));edge((x,yy2[2]),(x,yy2[-1]))
      else:edge((x,yy2[0]),(x,yy2[-1]))
     for yv in yy2:edge((xx2[0],yv),(xx2[-1],yv))
   for cell in pending:cell['source_handles']=[h] if variant=='native-table' else handles.get((cell['row']+1,cell['column']+1),[])
   facts['cells'].extend(pending)
  table(0,(52,108))
  if variant=='two-tables':table(1,(250,108))
  if variant=='extra-note':mt(lay,'Revision 12 / label 40',(229,123),'NOTES')
  if variant=='thin-grid':note('TABLE LINEWEIGHT 0.13 mm',(48,130))
 doc.saveas(path)
 readback=ezdxf.readfile(path);issues=readback.audit();assert not issues.errors,(path,issues.errors)
 if 'native_handle' in facts:
  arr=acad_table.read_acad_table_content(readback.entitydb[facts['native_handle']]);assert len(arr)>2 and arr[0][0]=='OFFSETS'
 facts['sha256']=sha(path);return facts
def main():
 parser=argparse.ArgumentParser();parser.add_argument('destination',type=Path);a=parser.parse_args();d=a.destination;d.mkdir(exist_ok=True)
 out=[]
 for n,name in enumerate(CASES,1):
  cid=f'T{n:02}';case=d/'inputs'/cid;case.mkdir(parents=True,exist_ok=False);info=[]
  for m,v in enumerate(['plain','waterline-spline','arrangement'] if name=='multi-drawing' else [name]):
   info.append(sheet(case/(f'drawing-{m+1}.dxf'),n,v))
  out.append(dict(id=cid,scenario=name,files=info))
 save(d/'truth.json',out)
if __name__=='__main__':main()
