"""独立作者生成的虚构结构详图，真值在绘图时记录，不从被测程序反推。"""
from dataclasses import dataclass
import hashlib,json,math
from pathlib import Path
import ezdxf
from ezdxf.enums import TextEntityAlignment
from ezdxf.math import Vec3
P=Path(__file__).resolve().parent
def save(path,obj):path.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
@dataclass(frozen=True)
class Item:
 name:str; role:str; spec:str=''; thickness:float|None=None; frames:tuple|None=None; expected:str='supported'
F=lambda n,r,s='',t=None,fr=None,e='supported':Item(n,r,s,t,fr,e)
CASES=[
 ('甲板板厚',F('主甲板','deck','',9)),('外板板厚',F('舷侧外板','shell_plate','',11)),('半角型材',F('普通肋骨','frame','L 75×50×6')),('等边角钢',F('舱壁扶强材','stiffener','L 63×63×5')),
 ('扁钢纵骨',F('船底纵骨','longitudinal','FB 100×8')),('球扁钢',F('甲板纵骨','longitudinal','HP 120×7')),('T型强横梁',F('强横梁','strong_beam','T 180×8+90×10')),
 ('水密横舱壁',F('水密横舱壁','transverse_bulkhead','',7,(18,18))),('纵舱壁',F('纵舱壁','longitudinal_bulkhead','',8,(12,30))),('内底板',F('内底板','double_bottom_plate','',10)),
 ('厚度未注',F('主甲板','deck',e='unknown_thickness')),('型材尺寸缺项',F('甲板纵骨','longitudinal','FB 90×?',e='incomplete_section')),('板材范围',F('舷侧外板','shell_plate','',12,(14,27))),
 ('MTEXT分行',F('横舱壁','transverse_bulkhead','',9,(17,17))),('斜置文字',F('普通肋骨','frame','L 70×45×5')),('90度视图',F('主甲板','deck','',7)),
 ('镜像插入',F('船底纵骨','longitudinal','FB 85×7')),('嵌套图块',F('扶强材','stiffener','L 60×40×5')),('重复块不同插入',F('普通肋骨','frame','L 65×45×6')),
 ('板厚冲突',F('主甲板','deck','',None,None,'conflicting_thickness')),('邻近不相关注记',F('内底板','double_bottom_plate',e='unknown_thickness')),
 ('重复同值',F('主甲板','deck','',8)),('双箭头一注',F('甲板纵骨','longitudinal','FB 90×8')),('缺失箭头',F('普通肋骨','frame','L 80×50×6',e='unbound_target')),
 ('落点两线相交',F('舷侧外板','shell_plate','',10,None,'ambiguous_target')),('双折引线',F('舱壁扶强材','stiffener','FB 70×7')),('折线代引线',F('甲板板','deck','',8)),
 ('英文甲板',F('MAIN DECK','deck','',8)),('英文肋骨',F('WEB FRAME','frame','L 85x55x8')),('组合跨图同版',F('内底板','double_bottom_plate','',9)),
 ('同件跨版冲突',F('主甲板','deck',e='revisions_separate')),('肋位负号',F('纵舱壁','longitudinal_bulkhead','',7,(-3,9))),('阵列说明',F('纵骨','longitudinal','FB 90×8',None,(4,28))),
 ('变间距',F('强横梁','strong_beam','T 150×7+80×9',None,(8,20))),('图纸空间',F('主甲板','deck','',10)),('有单位小数',F('甲板板','deck','',7.5)),
 ('英寸单位',F('主甲板','deck','',9.525)),('双层结构不同规格',F('内底板','double_bottom_plate','',8)),('孤立厚度',F('横舱壁','transverse_bulkhead',e='orphan_size')),
 ('旧图层线型',F('甲板纵骨','longitudinal','HP 100×6')),('双语注记',F('横舱壁 / TRANSVERSE BULKHEAD','transverse_bulkhead','',7)),
 ('舱室未注容积',F('压载舱','tank',e='unknown_volume')),
 ('有数无单位',F('主甲板','deck',e='unbound_unit')),('材料明注',F('横舱壁','transverse_bulkhead','',8)),('材料未注',F('横舱壁','transverse_bulkhead','',7)),
 ('只有单根肋位号',F('肋骨','frame','L 80×50×6',None,(23,23))),('明确开口舱室',F('货舱','compartment',e='unknown_volume')),
 ('离图孤线',F('扶强材','stiffener','FB 82×6',e='unbound_target')),
]
def make(folder,cid,label,item,sheet=0):
 d=ezdxf.new('R2013');d.units=4
 for layer in ['STEEL','ANNOT','LEADERS','GRID','TITLE']:d.layers.add(layer)
 m=d.modelspace();target=m
 def text(space,message,xy,layer='ANNOT',rot=0,multi=False):
    if multi:return space.add_mtext(message,dxfattribs={'insert':xy,'char_height':2.5,'rotation':rot,'layer':layer})
    return space.add_text(message,dxfattribs={'height':2.5,'insert':xy,'rotation':rot,'layer':layer})
 def shape(space,points):
    return space.add_lwpolyline(points,dxfattribs={'layer':'STEEL'})
 text(m,'SHIP STRUCTURAL DETAILS / 船体结构详图',(0,130),'TITLE')
 text(m,'Drawing unit: mm / 图形单位 mm',(0,122),'TITLE')
 dwgid=f'SD-{cid}-{sheet+1}';text(m,f'图号 {dwgid}  REV '+('B' if label=='同件跨版冲突' and sheet else 'A'),(0,115),'TITLE')
 if label in ['组合跨图同版','同件跨版冲突']:text(m,f'详见 SD-{cid}-{2 if sheet==0 else 1}  编号 PL-16',(0,108),'TITLE')
 if label=='图纸空间':
    target=d.layouts.new('PAGE');text(target,'STRUCTURAL DETAIL / 结构详图',(0,100),'TITLE')
 blocks=label in ['嵌套图块','镜像插入','重复块不同插入','90度视图']
 if blocks:target=d.blocks.new('TYP_DETAIL')
 locs=[(0.,0.)] if not blocks else ([(20,18),(165,33)] if label=='重复块不同插入' else [(32,17)])
 target1=shape(target,[(0,0),(50,0),(100,0)]);tip=(50.,0.);hm=[target1.dxf.handle]
 if label=='落点两线相交':hm.append(shape(target,[(50,-16),(50,21)]).dxf.handle)
 if label=='双箭头一注':hm.append(shape(target,[(0,-12),(120,-12)]).dxf.handle)
 if label=='双层结构不同规格':
    other=shape(target,[(0,-20),(100,-20)]);t2=text(target,'外底板 t=12 mm',(88,-35));l2=target.add_leader([(60,-20),(75,-32),(87,-32)],dxfattribs={'layer':'LEADERS'});l2.dxf.annotation_handle=t2.dxf.handle
 h=8 if label=='板厚冲突' else (8 if label=='同件跨版冲突' and not sheet else (10 if label=='同件跨版冲突' else item.thickness))
 parts=[item.name]
 if item.spec:parts.append(item.spec)
 if h is not None:
    size=(f't={h:g} mm' if label not in ['外板板厚','英文甲板','英寸单位','有单位小数'] else {'外板板厚':f'δ={h:g} mm','英文甲板':f'THICKNESS {h:g} mm','英寸单位':'THK 3/8 in','有单位小数':f'厚 {h/10:g} cm'}[label])
    parts.append(size)
 if item.frames:parts.append('FR '+str(item.frames[0])+('～'+str(item.frames[1]) if item.frames[0]!=item.frames[1] else ''))
 if label=='有数无单位':parts.append('t=8')
 if label=='材料明注':parts.append('材质 AH36')
 if label=='阵列说明':parts.append('7 道 @ 580 mm')
 if label=='变间距':parts.append('FR 8–14 @ 510 mm; FR 14–20 @ 620 mm')
 if label=='舱室未注容积':parts.append('TANK No. 4P')
 if label in ['组合跨图同版','同件跨版冲突']:parts.append('PL-16')
 raw=('\\P' if label=='MTEXT分行' else '  ').join(parts)
 ann=text(target,raw,(93,28),rot=33 if label=='斜置文字' else 0,multi=label=='MTEXT分行')
 leaders=[]
 if label!='缺失箭头':
    chain=[(50.,-7.) if label=='离图孤线' else tip,(76,32),(91,32)]
    if label=='双折引线':chain=[tip,(63,19),(74,19),(80,32),(91,32)]
    if label=='折线代引线':
        leaders.append(target.add_lwpolyline(chain,dxfattribs={'layer':'LEADERS'}).dxf.handle)
        target.add_solid([tip,(52.6,1.9),(51.6,2.6)],dxfattribs={'layer':'LEADERS'})
    else:
        e=target.add_leader(chain,dxfattribs={'layer':'LEADERS'});e.dxf.annotation_handle=ann.dxf.handle;leaders.append(e.dxf.handle)
    if label=='双箭头一注':
        e=target.add_leader([(50,-12),(80,32),(91,32)],dxfattribs={'layer':'LEADERS'});e.dxf.annotation_handle=ann.dxf.handle;leaders.append(e.dxf.handle)
 more=[];unrelated=[]
 if label in ['板厚冲突','重复同值']:
    moretext=text(target,item.name+(' t=12 mm' if label=='板厚冲突' else ' t=8 mm'),(84,44));more.append(moretext.dxf.handle)
    e=target.add_leader([tip,(78,46),(83,46)],dxfattribs={'layer':'LEADERS'});e.dxf.annotation_handle=moretext.dxf.handle;leaders.append(e.dxf.handle)
 if label in ['孤立厚度','邻近不相关注记']:unrelated.append(text(target,'t = 28 mm' if label=='孤立厚度' else '舷侧外板 t=28 mm',(91,-30)).dxf.handle)
 if label=='旧图层线型':target1.dxf.layer='0';ann.dxf.layer='0'
 instances=[]
 for off in locs:
    path=[]; transforms=[]
    if blocks:
        inner=target;inner_ins=None
        if label=='嵌套图块':
            outer=d.blocks.new('SHEET_DETAIL');inner_ins=outer.add_blockref(inner.name,(4,-6));inner=outer
        inst=m.add_blockref(inner.name,off,dxfattribs={'rotation':90 if label=='90度视图' else 0,'xscale':-1 if label=='镜像插入' else 1});path=[inst.dxf.handle]
        if inner_ins:path.append(inner_ins.dxf.handle);transforms.append(inner_ins.matrix44())
        transforms.append(inst.matrix44())
    w=Vec3(*( (50.,-7.) if label=='离图孤线' else tip),0)
    for M in transforms:w=M.transform(w)
    instances.append(dict(insert_path=path,expected_primary_tip_wcs=[w.x,w.y,0],text_instances=['/'.join(path+[a]) for a in [ann.dxf.handle,*more]],leader_instances=['/'.join(path+[a]) for a in leaders],target_instances=['/'.join(path+[a]) for a in hm]))
 docname=f'sheet-{sheet+1}.dxf';path=folder/docname;d.saveas(path);audit=ezdxf.readfile(path).audit()
 if audit.errors or audit.fixes:raise ValueError(cid,len(audit.errors),len(audit.fixes),[(x.code,x.message) for x in audit.fixes])
 return dict(file=docname,sha256=sha(path),layout='PAGE' if label=='图纸空间' else 'Model',role=item.role,raw_text=raw,annotation_handle=ann.dxf.handle,specification=item.spec or None,thickness_mm=h if label!='板厚冲突' else None,frame_range=item.frames,status=item.expected,material='AH36' if label=='材料明注' else None,disregard_handles=unrelated,instances=instances)
if __name__=='__main__':
 dest=P/'frozen';dest.mkdir(exist_ok=False);truth=[]
 for i,(label,it) in enumerate(CASES,1):
    cid=f'S{i:02}';folder=dest/'inputs'/cid;folder.mkdir(parents=True);pages=[make(folder,cid,label,it,j) for j in range(2 if label in ['组合跨图同版','同件跨版冲突'] else 1)]
    truth.append(dict(case=cid,scenario=label,files=pages))
 save(dest/'truth.json',truth)
