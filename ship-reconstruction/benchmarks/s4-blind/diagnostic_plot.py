"""从原始 DXF 和冻结逐案结果绘制证据定位图，便于复核箭头与注记。"""
from pathlib import Path
import argparse,json
import ezdxf,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
P=Path(__file__).resolve().parent
def draw(run,dest):
    cjk=next((s for s in ('PingFang SC','Arial Unicode MS','Noto Sans CJK SC','Heiti TC') if s in {f.name for f in font_manager.fontManager.ttflist}),None)
    if cjk:plt.rcParams['font.family']=cjk
    truth=json.loads((P/'frozen/truth.json').read_bytes())
    fig,axes=plt.subplots(2,2,figsize=(11,6.1),layout='constrained')
    for cid,ax in zip(('S07','S20','S25','S27'),axes.flat):
        case=next(c for c in truth if c['case']==cid);f=case['files'][0];doc=ezdxf.readfile(P/'frozen/inputs'/cid/f['file']);instance=f['instances'][0]
        for h in instance['target_instances']+instance['leader_instances']:
            e=doc.entitydb[h]
            pp=[(v[0],v[1]) for v in e.vertices] if e.dxftype()=='LEADER' else e.get_points('xy')
            color='#14726C' if h in instance['target_instances'] else '#CA722C'
            ax.plot(*zip(*pp),color=color,linewidth=2 if h in instance['target_instances'] else 1.25)
            if h in instance['leader_instances']:
                ax.plot(*pp[0],marker='o',ms=4,color=color)
        for h in instance['text_instances']:
            t=doc.entitydb[h];p=t.dxf.insert
            ax.text(p.x,p.y,t.dxf.text,fontsize=8,color='#1E354A',va='center')
        receipt=json.loads((P/'runs'/run/cid/'receipt.json').read_bytes())
        ax.set_title(cid+'　'+case['scenario']+'　'+('符合预登记' if receipt['dedicated_full_pass'] else '本轮有缺项'),loc='left',fontsize=10,fontweight='bold')
        ax.set(xlim=(-3,175),ylim=(-20,55),aspect='equal',xlabel='CAD X (mm)',ylabel='CAD Y (mm)');ax.grid(alpha=.18)
        ax.spines[['right','top']].set_visible(False)
    fig.suptitle('原图位置见证：绿色为构件投影，橙色为引线与箭头落点',fontsize=14)
    fig.savefig(dest,dpi=165);plt.close(fig)
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('run');a.add_argument('destination',type=Path);v=a.parse_args();draw(v.run,v.destination)
