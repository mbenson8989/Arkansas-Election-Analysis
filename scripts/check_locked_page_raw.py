"""Independent raw-source check of wiki/Locked-Arkansas-Formula.md (no pipeline tables/analysis code; numpy/scipy only).
Every number on the page must equal a value recomputed here from raw/ (scripts/raw_sources.py: bulk FullDataFile.json + API county responses),
at its printed precision, or be an explicitly whitelisted structural number. White/Conway 2022 use the API values (= certified White totals);
any page number that depends on a bulk/API disagreement is listed. Exit 1 on any failure."""
import sys, re, json, numpy as np
from scipy import stats
sys.path.insert(0,'/workspace/arkansas-elections/scripts'); import raw_sources as RS
W='/workspace/arkansas-elections/'; A,B,NAMES=RS.A,RS.B,RS.NAMES
F=sorted(NAMES); n=75
# Rep Senate primary (for the two-party sensitivity line)
for el,nm,files,yy in (('2022_primary','U.S. Senate - REP',['api_GetContestResults_FED.json'],'2022'),('2026_primary','REP U.S. Senate',['api_GetContestResults_Federal.json'],'2026')):
    cid,ch=RS.contest_id(el,nm); A['rsen_'+yy],_=RS.api(el,files,cid,set(ch))
v=lambda k:np.array([A[k][f] for f in F],float)
D={}
for y in ('2022','2026'):
    t=y[2:]; D['S'+t]=100*v('dem_'+y)/v('ballots_'+y); D['P'+t]=100*v('dsen_'+y)/v('pballots_'+y); D['G'+t]=D['S'+t]-D['P'+t]
    D['P2p'+t]=100*v('dsen_'+y)/(v('dsen_'+y)+v('rsen_'+y))
dS=D['S26']-D['S22']; dP=D['P26']-D['P22']; dG=D['G26']-D['G22']; loss=v('dsen_2026')<v('dsen_2022')
idx={NAMES[f]:i for i,f in enumerate(F)}
vals=set()
def add(x):
    x=float(x)
    for d in (0,1,2,3,4): vals.add(round(x,d)); vals.add(round(abs(x),d))
def ols(y,x,w=None):
    X=np.c_[np.ones(len(x)),x/100]; Wt=np.ones(len(x)) if w is None else w
    XtW=X.T*Wt; beta=np.linalg.solve(XtW@X,XtW@y); e=y-X@beta; s2=(Wt*e*e).sum()/(len(x)-2); se=np.sqrt(np.diag(s2*np.linalg.inv(XtW@X)))
    yb=(Wt*y).sum()/Wt.sum(); r2=1-(Wt*e*e).sum()/(Wt*(y-yb)**2).sum()
    return dict(b=beta[0],m=beta[1],b_se=se[0],m_se=se[1],r2=r2,resid_se=np.sqrt((e*e).sum()/(len(x)-2)),w1=np.mean(abs(e)<=1)*100,w2=np.mean(abs(e)<=2)*100,w3=np.mean(abs(e)<=3)*100,med=np.median(abs(e)),e=e,X=X,s2=s2)
R={}
for t in ('22','26'):
    R['all'+t]=ols(D['G'+t],D['P'+t]); R['w'+t]=ols(D['G'+t],D['P'+t],v('ballots_20'+t))
# narrowing: Cook's D > 4/n or |externally studentized residual| > 2.5 in either year's all-county fit
flag=set()
for t in ('22','26'):
    r=R['all'+t]; X=r['X']; h=np.einsum('ij,jk,ik->i',X,np.linalg.inv(X.T@X),X); e=r['e']; p=2; s2=r['s2']
    cook=e**2/(p*s2)*h/(1-h)**2; s2i=((n-p)*s2-e**2/(1-h))/(n-p-1); stud=e/np.sqrt(s2i*(1-h))
    R['cook'+t]=cook; R['stud'+t]=stud; flag|={F[i] for i in range(n) if cook[i]>4/n or abs(stud[i])>2.5}
keep=np.array([f not in flag for f in F])
for t in ('22','26'): R['nar'+t]=ols(D['G'+t][keep],D['P'+t][keep])
R['pool']=ols(np.r_[D['G22'],D['G26']],np.r_[D['P22'],D['P26']])
# year interaction (m units = per 100 points of P)
x=np.r_[D['P22'],D['P26']]/100; yr=np.r_[np.zeros(n),np.ones(n)]; Y=np.r_[D['G22'],D['G26']]; X=np.c_[np.ones(2*n),x,yr,x*yr]
be=np.linalg.lstsq(X,Y,rcond=None)[0]; e=Y-X@be; s2=e@e/(2*n-4); se=np.sqrt(np.diag(s2*np.linalg.inv(X.T@X))); pv=2*stats.t.sf(abs(be/se),2*n-4)
# dG on dP, fitted dG on drop, share form
R['dgdp']=ols(dG,dP); fe=ols(dG,-dP)
narc=sorted(NAMES[f] for f in flag)
for k,r in R.items():
    if isinstance(r,dict):
        for kk in ('b','m','b_se','m_se','r2','resid_se','w1','w2','w3','med'): add(r[kk])
add(R['dgdp']['m']/100); add(be[2]); add(be[3]); add(pv[2]); add(pv[3])
for kk in ('b','b_se','r2'): add(fe[kk])
add(fe['m']/100); add(fe['m_se']/100); add(fe['r2']*100)
for t in ('22','26'):
    s=ols(D['S'+t],D['P'+t]); E=s['e']; k=int(np.argmax(abs(E)))
    for q in (s['m'],s['b'],s['m_se'],s['b_se'],s['r2'],np.mean(abs(E)),E[k],np.sqrt(np.mean(E**2)),R['all'+t]['m']+100,1+R['all'+t]['m']/100,
              np.mean(abs(D['S'+t]-(R['all'+t]['m']*D['P'+t]/100+R['all'+t]['b'])))): add(q)
    for i in range(n): add(s['X'][i,1]); add((s['X']@np.r_[s['b'],s['m']])[i]); add(E[i])
    R['share'+t]=s
# per-county values, worked examples, statewide
for arr in (D['S22'],D['S26'],D['P22'],D['P26'],D['G22'],D['G26'],dS,dP,dG,-dP,dG-abs(dP)):
    for q in arr: add(q)
for k in A:
    for q in A[k].values(): add(q)
for i in range(n):
    add(v('dem_2026')[i]-D['S22'][i]/100*v('ballots_2026')[i]); add(v('dem_2026')[i]-v('dem_2022')[i]*v('dsen_2026')[i]/v('dsen_2022')[i])
    for t in ('22','26'):
        fg=R['all'+t]['m']*D['P'+t][i]/100+R['all'+t]['b']; add(fg); add(D['G'+t][i]-fg)
    add(fe['b']+fe['m']/100*(-dP[i])); add(dG[i]-(fe['b']+fe['m']/100*(-dP[i])))
add(sum(A['dsen_2022'].values())); add(sum(A['dsen_2026'].values()))
add(np.corrcoef((D['S26']-D['P2p26'])-(D['S22']-D['P2p22']),dG)[0,1])
add(loss.sum()); add((~loss).sum()); add(len(flag)); add(n-len(flag)); add(2*n); add(4/n)
STRUCT={2022,2026,2025,2020,1844,1843,234,3318,100,75,150,24,3,19,36,10}|set(range(0,16))
REFS={6421:'raw/reference/wikipedia_2022_Arkansas_gubernatorial_election.html (Russell, published 2022 Dem primary)'}
ref=open(W+'raw/reference/wikipedia_2022_Arkansas_gubernatorial_election.html',encoding='utf-8',errors='ignore').read()
assert '6,421' in ref
pg=open(W+'wiki/Locked-Arkansas-Formula.md').read()
body=re.sub(r'https?://\S+','',pg); body=re.sub(r'\(Graphs#[^)]*\)|\(#[^)]*\)|\([A-Za-z-]+#[^)]*\)','',body)
body=re.sub(r'AR_[A-Za-z0-9_]+\.png','',body)
fail=[]; ntok=0
for tok in re.findall(r'[−+\-]?\d[\d,]*(?:\.\d+)?%?',body):
    x=float(tok.replace(',','').replace('−','-').replace('+','').rstrip('%')); ntok+=1
    if float(x).is_integer() and (abs(x) in STRUCT or abs(x) in REFS): continue
    d=len(tok.split('.')[1].rstrip('%')) if '.' in tok else 0
    if round(x,d) in vals or round(abs(x),d) in vals: continue
    fail.append(('number not reproduced from raw',tok))
# positional: share-form table and equation lines vs raw refit
shs=pg.split('## Share form: S = m × (D/100) + b')[1].split('\n## ')[0]
rows={c[0]:c[1:] for c in ([z.strip() for z in l.strip('|').split('|')] for l in shs.splitlines() if l.startswith('| ') and not l.startswith('| Item'))}
nm=lambda z:float(z.replace('−','-').replace('+',''))
for j,t in enumerate(('22','26')):
    s_=R['share'+t]; E=s_['e']; k=int(np.argmax(abs(E)))
    m1=re.match(r'(\S+) \((\S+)\)',rows['Multiplier m (SE)'][j]); m2=re.match(r'(\S+) \((\S+)\)',rows['Offset b (SE)'][j]); m3=re.match(r'(\S+) \((.+)\)',rows['Largest residual (pts)'][j])
    for got,want,d in ((m1.group(1),s_['m'],2),(m1.group(2),s_['m_se'],2),(m2.group(1),s_['b'],2),(m2.group(2),s_['b_se'],2),(rows['R²'][j],s_['r2'],3),
                       (rows['Mean absolute residual (pts)'][j],np.mean(abs(E)),2),(m3.group(1),E[k],2),(rows['RMSE (pts)'][j],np.sqrt(np.mean(E**2)),2),(rows['n (counties)'][j],n,0)):
        ntok+=0
        if abs(nm(got)-round(want,d))>10**-d*0.51: fail.append(('share table cell',t,got,want))
    if m3.group(2)!=NAMES[F[k]]: fail.append(('share largest-residual county',t,m3.group(2),NAMES[F[k]]))
    eq=re.search(('2022:' if t=='22' else re.escape('2026 (UNOFFICIAL):'))+r'\s+S = (\S+) × \(D/100\) \+ (\S+)',shs)
    if not eq or abs(nm(eq.group(1))-round(s_['m'],2))>0.0051 or abs(nm(eq.group(2))-round(s_['b'],2))>0.0051: fail.append(('share equation line',t))
# list checks
if 'Narrowed fits leave out '+', '.join(narc) not in pg: fail.append(('narrowed list differs',narc))
# disagreements between raw sources that feed this page
dis=[]
for k in ('dem_2022','ballots_2022','dsen_2022','pballots_2022','dem_2026','ballots_2026','dsen_2026','pballots_2026'):
    for f in F:
        if A[k][f]!=B[k][f]: dis.append((NAMES[f],k,B[k][f],A[k][f]))
out=dict(tokens_checked=ntok,fail=fail,narrowed=narc,bulk_api_disagreements_used_API=dis,
         share={t:{k:float(R['share'+t][k]) for k in ('m','b','m_se','b_se','r2')} for t in ('22','26')})
json.dump(out,open(W+'verification/check_locked_page_raw.json','w'),indent=1,default=str)
print(f'Locked page: numbers checked {ntok}; FAIL {len(fail)}; narrowed {narc}'); [print(' ',x) for x in fail]
print('bulk/API disagreements (API used):',dis)
sys.exit(1 if fail else 0)
