"""图表来自解析合成真值和独立 CAD 读取，明确 S3 尚未输出。"""
import argparse,csv,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from forms import FORMS,width,vertical
P=Path(__file__).resolve().parent
def draw(out,run):
    out.mkdir(parents=True,exist_ok=True)
    colors=['#076477','#E8882A','#744CA3']
    plt.rcParams.update({'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.22})
    fig,axes=plt.subplots(1,3,figsize=(11,3.8),constrained_layout=True,sharey=True,sharex=True)
    for ax,form,title in zip(axes,FORMS,['A   Round bilge','B   Hard chine','C   Asymmetric']):
        for frac,c in zip([.10,.49,.91],colors):
            x=frac*form.length;k,top=vertical(form,frac);z=k+(top-k)*np.linspace(0,1,201)**2
            for side,sign in [('port',1),('starboard',-1)]:
                y=np.array([sign*width(form,x,h,side) for h in z])
                ax.plot(y,z,color=c,lw=1.7,label=(f'x/L = {frac:.2f}' if sign==1 else None))
            if form.code=='B':
                a=width(form,x,k,'starboard');b=width(form,x,k,'port');ax.plot([-a,b],[k,k],color=c,lw=1.7)
        ax.set_title(title,loc='left',fontweight='bold');ax.set(xlabel='Signed transverse Y (m)',aspect='equal',xlim=(-5,5),ylim=(-.2,4.8))
    axes[0].set_ylabel('Height Z (m)');axes[0].legend(frameon=False,fontsize=8)
    fig.suptitle('Analytic reference sections | independent synthetic benchmark',fontsize=14)
    fig.savefig(out/'解析横剖面对照.png',dpi=180);plt.close(fig)
    truth=json.loads((P/'casebook/geometry-truth.json').read_bytes())
    fig,axes=plt.subplots(1,2,figsize=(8.5,3.6),constrained_layout=True)
    for form,c,data in zip(FORMS,colors,truth):
        h=data['hydro'];ds=[row['draft_m'] for row in h]
        for ax,k in zip(axes,['volume_m3','waterplane_m2']):
            ax.plot(ds,[row[k] for row in h],'.-',lw=2,markersize=8,color=c,label=form.code)
            ax.set_xlabel('Draft (m)')
    axes[0].set_ylabel('Displaced volume (m³)');axes[1].set_ylabel('Waterplane area (m²)');axes[0].legend(title='Case',frameon=False)
    fig.suptitle('Three evaluated drafts per ship | reference values',fontsize=13)
    fig.savefig(out/'三吃水静水力真值.png',dpi=180);plt.close(fig)
    if run:
        with (P/'runs'/run/'曲线三维独立回读.csv').open(encoding='utf-8-sig') as f:data=list(csv.DictReader(f))
        fig,ax=plt.subplots(figsize=(6.4,3.6),constrained_layout=True)
        for i,form in enumerate(FORMS):
            for v,offset,c in [('YZ',-.16,colors[0]),('XY',.16,colors[1])]:
                diff=max(float(r['source_vs_analytic_halfwidth_max_m']) for r in data if r['case']==form.code and r['view']==v)*1000
                ax.bar(i+offset,max(1.e-8,diff),width=.28,color=c,label=f'{v} source' if i==0 else None)
        ax.set_xticks(range(3),[v.code for v in FORMS]);ax.set_yscale('log');ax.set_ylabel('Maximum sampled difference (mm, log scale)');ax.set_xlabel('Synthetic hull');ax.legend(frameon=False)
        ax.set_title('Source curve sampling versus analytic reference')
        fig.savefig(out/'原CAD与解析几何差异.png',dpi=180);plt.close(fig)
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('out',type=Path);a.add_argument('--run');v=a.parse_args();draw(v.out,v.run)
