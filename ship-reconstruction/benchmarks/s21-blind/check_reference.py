"""A 与 B 二次独立核对积分闭式；C 用水线条带反向积分交叉核对。"""
import argparse, json
from pathlib import Path
from math import acos,sqrt,pi
import numpy as np
from forms import FORMS
P=Path(__file__).resolve().parent

def exact_polygon(xs,ys):
    return sum((v+w)*.5*(b-a) for a,b,v,w in zip(xs,xs[1:],ys,ys[1:]))
def by_shape(form,h):
    if form.code=='A':
        t=h/form.depth
        fx=.93*2/pi+.07*4/(3*pi)
        area_z=.5*(acos(1-t)-(1-t)*sqrt(1-(1-t)**2))*form.depth
        scale=fx*form.beam*form.length
        return scale*area_z,scale*sqrt(1-(1-t)**2)
    if form.code=='B':
        t=h/form.depth
        xs=[0.,.55,.8,1.];ys=[.8,1.,.84,0.]
        L=exact_polygon(xs,ys)*form.length
        levels=[0,.25,.66,1.];ww=[.18,.72,.91,1.]
        below=[k for k in levels if k<t]+[t]
        half_fraction=float(np.interp(t,levels,ww))
        return L*form.beam*form.depth*exact_polygon(below,np.interp(below,levels,ww)),L*form.beam*half_fraction
    # C 的水线面积先沿 X 近似积分，再沿全船统一的 Z 采样积分，与逐截面先纵后横有别。
    # 对底线边界使用向量化设计式，以 1000 个垂向条带和 2000 个纵向中点独立求积；不平移端点。
    def strip(n): 
        x=(np.arange(2*n)+.5)/(2*n);k=.12+.60*np.exp(-((x-.995)/.096)**2)+.31*np.exp(-(x/.11)**2)
        top=form.depth+.32*x**4+.18*(1-x)**4
        shape=np.sin(np.pi*x)**.72;stern=np.exp(-((x-.10)/.085)**2);bulb=np.exp(-((x-.89)/.075)**2)
        def water(z):
            t=np.clip((z-k)/(top-k),0,1)
            y=form.beam*shape*np.sqrt(t)*(1.13-.13*t)*(1+.19*bulb*np.exp(-((t-.27)/.15)**2)-.12*stern*t**2)
            return form.length*y.mean()
        V=sum(water(h*(i+.5)/n) for i in range(n))*h/n
        return V,water(h)
    return strip(1000)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('output',type=Path);args=a.parse_args()
    truth=json.loads((P/'casebook/geometry-truth.json').read_bytes());rows=[]
    for form,g in zip(FORMS,truth):
        for h in g['hydro']:
            v,w=by_shape(form,h['draft_m'])
            ev=abs(v-h['volume_m3'])/h['volume_m3'];ew=abs(w-h['waterplane_m2'])/h['waterplane_m2']
            tol=3e-5 if form.code=='C' else 1e-10
            rows.append(dict(case=form.code,draft_m=h['draft_m'],relative_volume_error=ev,relative_waterplane_error=ew,method='independent_fixed_midpoint_strips' if form.code=='C' else 'independent_closed_form',passed=bool(max(ev,ew)<tol),tolerance=tol))
    args.output.write_text(json.dumps(rows,indent=2)+'\n')
    print([(r['case'],round(r['relative_volume_error'],7),round(r['relative_waterplane_error'],7),r['passed']) for r in rows])
