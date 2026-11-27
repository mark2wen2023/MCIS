"""全合成船体的解析船轴，X 向艏、Y 向左舷、Z 向上，长度单位米。"""
from dataclasses import dataclass
from math import sin, cos, pi, sqrt, exp

@dataclass(frozen=True)
class Form:
    code:str
    name:str
    length:float
    beam:float
    depth:float
    station_fractions:tuple
    drafts:tuple

FORMS=(
    Form('A','圆舭研究体',32.,8.2,3.6,(0,.06,.17,.33,.51,.70,.85,.95,1.),(.9,1.8,2.7)),
    Form('B','双折角棱柱与方艉研究体',23.5,6.8,2.9,(0,.11,.25,.40,.55,.68,.79,.89,.97,1.),(.74,1.45,2.30)),
    Form('C','变底线偏舷复合艏艉研究体',41.,8.8,4.0,(0,.025,.075,.15,.29,.46,.62,.76,.86,.925,.97,1.),(1.30,2.20,3.40)),
)

def vertical(form,f):
    if form.code=='C':
        return (.12+.60*exp(-((f-.995)/.096)**2)+.31*exp(-(f/.11)**2),form.depth+.32*f**4+.18*(1-f)**4)
    return (0.,form.depth)

def width(form,x,z,side):
    if side not in ('port','starboard'):
        raise ValueError(side)
    f=x/form.length
    k,deck=vertical(form,f)
    if f<0 or f>1 or z<k-1e-12 or z>deck+1e-12:
        return None
    t=min(1.,max(0.,(z-k)/(deck-k)))
    if form.code=='A':
        lengthfactor=sin(pi*f)*(.93+.07*sin(pi*f)**2)
        sect=sqrt(t*(2-t))
    elif form.code=='B':
        interp=lambda a,b,r:a+(b-a)*r
        if f<=.55:
            lengthfactor=.80+.20*f/.55
        elif f<=.80:
            lengthfactor=1.-.16*(f-.55)/.25
        else:
            lengthfactor=.84*(1.-f)/.20
        sect=interp(.18,.72,t/.25) if t<=.25 else (interp(.72,.91,(t-.25)/.41) if t<=.66 else interp(.91,1.,(t-.66)/.34))
    else:
        lengthfactor=sin(pi*f)**.72
        stern=exp(-((f-.10)/.085)**2)
        bulb=exp(-((f-.89)/.075)**2)
        change=(.19*bulb*exp(-((t-.27)/.15)**2)-.12*stern*t**2)
        asymmetric=(.09*sin(1.5*pi*f)+.055*stern)*(1 if side=='port' else -1)
        sect=sqrt(t)*(1.13-.13*t)*(1+change+asymmetric*(.4+.6*t))
    return max(0.,.5*form.beam*lengthfactor*sect)
