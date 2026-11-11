import json, math
d=json.load(open('/workspace/maritime-sim-design/reports/haili5/case.json'))
def ts(p):
    h,m,s=p['time']['beijing'][11:19].split(':'); return int(h)*3600+int(m)*60+int(s)
T0=ts({'time':{'beijing':'2025-10-25T19:42:00'}}); T1=ts({'time':{'beijing':'2025-10-25T19:54:32'}})
lat0,lon0=22.2785,113.806833
def enu(lat,lon): return ((lon-lon0)*111320*math.cos(math.radians(lat0)), (lat-lat0)*110574)
KN=1852/3600
pts={'haili5':[], 'wanhai_a17':[]}
for p in d['trackPoints']:
    if p['id']=='t-a17-195115-fig24': continue
    pts[p['vesselId']].append((ts(p)-T0, p['courseDeg'], p['speedKn'], enu(p['location']['latDeg'],p['location']['lonDeg']) if p['location'] else None))
for k in pts: pts[k].sort()
def cs_at(lst,t):
    # piecewise linear course/speed
    prev=lst[0]
    for q in lst:
        if q[0]>=t:
            if q[0]==prev[0]: return q[1],q[2]
            f=(t-prev[0])/(q[0]-prev[0]); dc=((q[1]-prev[1]+180)%360)-180
            return (prev[1]+dc*f)%360, prev[2]+(q[2]-prev[2])*f
        prev=q
    return lst[-1][1],lst[-1][2]
dur=T1-T0
def build(v, anchor_t):
    lst=[q for q in pts[v] if q[0]>=-1800]
    anc=[q for q in lst if q[3] is not None and q[0]==anchor_t][0][3]
    pos={anchor_t:anc}
    e,n=anc
    for t in range(anchor_t,dur):  # forward
        c,s=cs_at(lst,t+0.5); e+=s*KN*math.sin(math.radians(c)); n+=s*KN*math.cos(math.radians(c)); pos[t+1]=(e,n)
    e,n=anc
    for t in range(anchor_t,0,-1):
        c,s=cs_at(lst,t-0.5); e-=s*KN*math.sin(math.radians(c)); n-=s*KN*math.cos(math.radians(c)); pos[t-1]=(e,n)
    return lst,pos
out=open('/tmp/w1real/tracks.csv','w'); out.write('vessel,t,e,n,cog,sogMps\n')
res={}
for v,anchor in (('haili5',ts({'time':{'beijing':'2025-10-25T19:53:08'}})-T0),('wanhai_a17',ts({'time':{'beijing':'2025-10-25T19:53:08'}})-T0)):
    lst,pos=build(v,anchor); res[v]=(lst,pos)
    for t in range(0,dur+1,1):
        c,s=cs_at(lst,t); out.write(f"{v},{t},{pos[t][0]:.2f},{pos[t][1]:.2f},{c:.2f},{s*KN:.4f}\n")
    # check against known fixes
    for q in lst:
        if q[3] is not None and 0<=q[0]<=dur: print(v,q[0],'fix',[round(x) for x in q[3]],'DR',[round(x) for x in pos[q[0]]])
out.close()
h=res['haili5'][1]; a=res['wanhai_a17'][1]
for t in (0,555,650,666,700,752):
    print('t',t, 'dist nm', round(math.dist(h[t],a[t])/1852,2))
