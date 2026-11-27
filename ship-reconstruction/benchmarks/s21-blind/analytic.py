"""独立解析真值: 截面积与静水力做分段高斯积分，尖部和底部变量代换。"""
import csv,json
from pathlib import Path
import numpy as np
from functools import lru_cache
from math import sqrt
from forms import FORMS,width,vertical
P=Path(__file__).resolve().parent
@lru_cache(None)
def legendre(n):
    a,b=np.polynomial.legendre.leggauss(n)
    return (a+1)*.5,b*.5
def nodes(a,b,n):
    u,w=legendre(n)
    return [(float(a+(b-a)*t),float((b-a)*q)) for t,q in zip(u,w)]
def section(f,x,h,n):
    k,de=vertical(f,x/f.length);up=min(h,de)
    if up<=k:return np.zeros(3)
    lim=sqrt((up-k)/(de-k))
    knots=[0,lim]+([sqrt(v) for v in [.25,.66] if v<lim**2] if f.code=='B' else [])
    arr=np.zeros(3)
    for a,b in zip(sorted(knots),sorted(knots)[1:]):
        for u,q in nodes(a,b,n):
            z=k+(de-k)*u*u;dz=2*u*(de-k)
            p=width(f,x,z,'port');s=width(f,x,z,'starboard')
            arr+=q*dz*np.array([p+s,.5*(p*p-s*s),z*(p+s)])
    return arr
def hydro(f,h,n):
    qv=np.zeros(7)
    divisions=sorted({0.,1.,.50,*([.55,.80] if f.code=='B' else [.10,.29,.62,.89])})
    for a,b in zip(divisions,divisions[1:]):
        for u,w in nodes(0,1,n):
            if a==0:x=a+(b-a)*u**4;j=(b-a)*4*u**3
            elif b==1:x=b-(b-a)*(1.-u)**4;j=(b-a)*4*(1-u)**3
            else:x=a+(b-a)*u;j=b-a
            xm=x*f.length;A,my,mz=section(f,xm,h,n)
            pp=width(f,xm,h,'port') or 0;ss=width(f,xm,h,'starboard') or 0
            qv+=w*j*f.length*np.array([A,xm*A,my,mz,pp+ss,(pp**3+ss**3)/3,(pp**2-ss**2)/2])
    v,mx,my,mz,wp,it,wpy=qv;yc=wpy/wp
    return dict(draft_m=h,volume_m3=v,LCB_m=mx/v,TCB_m=my/v,KB_m=mz/v,waterplane_m2=wp,BMt_m=(it-wp*yc**2)/v)
def main():
    d=P/'casebook';out=[]
    for f in FORMS:
        hs=[];sections=[];points=[]
        for h in f.drafts:
            a,b=hydro(f,h,20),hydro(f,h,32)
            delta=max(abs(a[k]-b[k])/max(1.,abs(b[k])) for k in a)
            if delta>1e-7: raise ValueError(f.code,h,delta)
            hs.append(dict(**b,quadrature_delta_relative_or_absolute=delta))
        for i,(a,b) in enumerate(zip(f.station_fractions,f.station_fractions[1:])):
            for xi in (.289,.713):
                x=f.length*(a+(b-a)*xi);k,deck=vertical(f,x/f.length)
                for t in (.058,.199,.387,.577,.809,.948):
                    z=k+(deck-k)*t
                    for side,sign in [('port',1.),('starboard',-1.)]:
                        points.append(dict(id=f'{i}_{xi}_{t}_{side}',x_m=x,z_m=z,side=side,y_m=sign*width(f,x,z,side)))
                for index,h in enumerate(f.drafts):
                    ae=section(f,x,h,32)[0]
                    sections.append(dict(id=f'{i}_{xi}_{index}',x_m=x,draft_m=h,area_m2=ae))
        out.append(dict(case=f.code,ship_name=f.name,length_m=f.length,nominal_beam_m=f.beam,nominal_depth_m=f.depth,holdout=points,areas=sections,hydro=hs))
    (d/'geometry-truth.json').write_text(json.dumps(out,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    for name in ('holdout','areas','hydro'):
        rows=[{'case':f['case'],**r} for f in out for r in f[name]]
        with (d/(name+'.csv')).open('w',newline='') as fn:
            w=csv.DictWriter(fn,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
if __name__=='__main__':main()
