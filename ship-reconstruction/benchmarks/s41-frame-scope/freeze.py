"""封存变形试验。生成器只构造工程图与解析真值，不调用生产代码。"""
from pathlib import Path
import hashlib,json,random,math
import ezdxf
root=Path(__file__).parent
rng=random.Random(719831)
for i in range(8):
    dest=root/f'h{i+1:02}'
    dest.mkdir()
    d=ezdxf.new('R2013');d.units=4;m=d.modelspace()
    off=(rng.randint(-50000,50000),rng.randint(-50000,50000));ang=rng.choice([0,30,90,180]);th=math.radians(ang)
    def pt(x,y):return [off[0]+x*math.cos(th)-y*math.sin(th),off[1]+x*math.sin(th)+y*math.cos(th)]
    def t(s,x,y):return m.add_text(s,dxfattribs=dict(insert=pt(x,y),height=8,rotation=ang)).dxf.handle
    kind=rng.choice(['甲板','横舱壁','肋骨'])
    start=rng.randint(2,20)
    s=f'Fr.{start}~Fr.{start+6} {kind}' if i%2 else f'Fr.{start} Fr.{start+2} Fr.{start+4} {kind}'
    n=t(s,0,0); h=t('隔肋设',0,30)
    m.add_line(pt(-12,-8),pt(48,-8));m.add_line(pt(48,-8),pt(48,-22))
    d.saveas(dest/'drawing.dxf')
    (dest/'truth.json').write_text(json.dumps(dict(note=n,rule=h,explicit=[] if i%2 else [start,start+2,start+4],ranges=[[start,start+6]] if i%2 else [],placements=0),indent=2))
(root/'criteria.md').write_text('八幅独立生成图。按源实体对照显式肋位或区间、未指定起始相位的隔肋规则，无依据的空间部署数必须为零。评分阶段才读真值。\n')
files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}
(root/'frozen.json').write_text(json.dumps(files,ensure_ascii=False,indent=2))
