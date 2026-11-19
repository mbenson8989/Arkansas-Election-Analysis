"""Wiki verification, independent of build_wiki.py.
 1) Full county table on Reverse-Math: every integer checked against PASS B, every share recomputed from PASS B.
 2) Every number on all five pages (outside URLs) must equal a value recomputed here from PASS B, the census file, the fit summary,
    the comparison report, or a cited reference file. Structural numbers (years, dates, list/section numbers, IDs) are whitelisted explicitly.
 3) Banner, proxy label, UNOFFICIAL label and Cedar link present on every page.
Exit 1 on any failure."""
import csv,re,sys,json,itertools,pandas as pd,numpy as np
W='/workspace/arkansas-elections/'; WK=W+'wiki/'
PAGES=['Home','Reverse-Math','Locked-Arkansas-Formula','Floor-and-Ceiling','Graphs']
B={r['county']:{k:int(v) for k,v in r.items() if k!='county'} for r in csv.DictReader(open(W+'verification/passB_counties.csv'))}
J=json.load(open(W+'repo/data/AR_results_summary.json')); C=json.load(open(W+'verification/compare_report.json'))
A={r['county']:{k:int(v) for k,v in r.items() if k!='county'} for r in csv.DictReader(open(W+'verification/passA_counties.csv'))}
num=lambda s:float(s.replace(',','').replace('−','-').replace('+','').rstrip('%'))
fail=[]
# ---------- 1) full table
t=open(WK+'Reverse-Math.md').read().split('## Full county table')[1]
rows=[l for l in t.splitlines() if l.startswith('| ') and not l.startswith('| County')]
n1=0
for l in rows:
    c=[x.strip() for x in l.strip('|').split('|')]; name=c[0].rstrip('†‡§'); b=B[name]
    for k,i in (('prim_demsen_2022',3),('prim_ballots_2022',4),('dem_2022',6),('ballots_2022',7),('prim_demsen_2026',10),('prim_ballots_2026',11),('dem_2026',13),('ballots_2026',14)):
        n1+=1
        if int(num(c[i]))!=b[k]: fail.append(('table',name,k,c[i],b[k]))
    P22=100*b['prim_demsen_2022']/b['prim_ballots_2022']; S22=100*b['dem_2022']/b['ballots_2022']; P26=100*b['prim_demsen_2026']/b['prim_ballots_2026']; S26=100*b['dem_2026']/b['ballots_2026']
    for v,i in ((P22,5),(S22,8),(S22-P22,9),(P26,12),(S26,15),(S26-P26,16),((S26-P26)-(S22-P22),17)):
        n1+=1
        if abs(round(v,2)-num(c[i]))>0.0051: fail.append(('table',name,i,c[i],v))
if len(rows)!=75: fail.append(('table rows',len(rows)))
# ---------- 2) ledger of allowed values, recomputed here
o=pd.DataFrame(B).T.astype(float)
cen=pd.read_csv(W+'raw/census/co-est2025-alldata.csv',encoding='latin-1',dtype={'STATE':str,'SUMLEV':str}); cen=cen[(cen.SUMLEV=='050')&(cen.STATE=='05')]; cen.index=cen.CTYNAME.str.replace(' County','')
o['pop']=cen.POPESTIMATE2025.reindex(o.index)
for y,t_ in (('2022','22'),('2026','26')):
    o['S'+t_]=100*o[f'dem_{y}']/o[f'ballots_{y}']; o['P'+t_]=100*o[f'prim_demsen_{y}']/o[f'prim_ballots_{y}']; o['G'+t_]=o['S'+t_]-o['P'+t_]
o['dS']=o.S26-o.S22; o['dP']=o.P26-o.P22; o['dG']=o.G26-o.G22
o['res']=o.dG-o.dP.abs(); o['iev']=o.dem_2026-o.S22/100*o.ballots_2026; o['gap']=o.dem_2026-o.dem_2022*(o.prim_demsen_2026/o.prim_demsen_2022)
o['a_minus']=o.dem_2022+o.rep_2022-o.ballots_2022; o['g_minus']=o.govtotal_2022-o.ballots_2022
vals=set()
def add(v):
    if v is None or isinstance(v,(str,bool)) : return
    v=float(v); vals.add(round(v,2)); vals.add(round(abs(v),2)); vals.add(round(v)); vals.add(round(abs(v)))
    for d in (3,4,5,7): vals.add(round(v,d)); vals.add(round(abs(v),d))
for col in o.columns:
    for v in o[col].values: add(v)
T=o.sum()
tot={k:T[k] for k in o.columns if not k[0].isupper() and k not in('res','iev','gap')}
for k,v in tot.items(): add(v)
for y in ('2022','2026'):
    for k in ('prim_demsen','prim_ballots','dem','ballots'): add(T[f'{k}_2026']-T[f'{k}_2022'])
add((T.prim_demsen_2026/T.prim_demsen_2022-1)*100); add((1-T.prim_ballots_2026/T.prim_ballots_2022)*100)
S22=100*T.dem_2022/T.ballots_2022; S26=100*T.dem_2026/T.ballots_2026; P22=100*T.prim_demsen_2022/T.prim_ballots_2022; P26=100*T.prim_demsen_2026/T.prim_ballots_2026
for v in (S22,S26,P22,P26,S22-P22,S26-P26,(S26-P26)-(S22-P22),S26-S22,P26-P22,(S26-S22)/100*T.ballots_2026): add(v)
# group rows (six largest / others)
oo=o.sort_values('pop',ascending=False)
for d in (oo.head(6),oo.iloc[6:]):
    t2=d.sum(); s22=100*t2.dem_2022/t2.ballots_2022; s26=100*t2.dem_2026/t2.ballots_2026; p22=100*t2.prim_demsen_2022/t2.prim_ballots_2022; p26=100*t2.prim_demsen_2026/t2.prim_ballots_2026
    for v in (s22,s26,p22,p26,s26-s22,p26-p22,(s26-p26)-(s22-p22),d.dG.median(),d.dG.min(),d.dG.max(),d.iev.sum(),len(d)): add(v)
for v in (o.dG.median(),o.dS.median(),o.dG.std(),o.dS.std(),np.nanmedian(o.res[o.prim_demsen_2026<o.prim_demsen_2022]),o.iev.sum(),(o.dG>0).sum(),(o.dG<0).sum(),(o.dS>0).sum(),(o.dS<0).sum(),(o.dP<0).sum(),(o.dP>0).sum(),(o.prim_demsen_2026<o.prim_demsen_2022).sum(),(o.prim_demsen_2026>=o.prim_demsen_2022).sum(),((o.prim_demsen_2026<o.prim_demsen_2022)&(o.dP>0)).sum()): add(v)
for t_,y in (('22','2022'),('26','2026')):
    fv=J['fits'][y]['m']*o['P'+t_]/100+J['fits'][y]['b']
    for v in fv.values: add(v)
    for v in (o['G'+t_]-fv).values: add(v)
def walk(x):
    if isinstance(x,dict): [walk(v) for v in x.values()]
    elif isinstance(x,list): [walk(v) for v in x]
    elif isinstance(x,(int,float)) and not isinstance(x,bool):
        add(x); add(x/100); add(x*100); add(1+x/100)
walk(J['fits']); walk(J['regions']); walk(J['narrow']); walk(J['K']); walk(J['sensitivity_two_party_senate_primary']); walk(J['overballot'])
walk({k:v for k,v in C.items() if k not in('mismatches','adjudication')})
for c in ('White','Conway'):
    for k in ('govtotal_2022','ballots_2022'): add(A[c][k])
add(C['wikipedia_2022_general_check']['figures'])
# cited reference values, parsed from the saved reference files
ref=open(W+'raw/reference/whitecountycitizen_2022_official_general_results.txt').read()
for m in re.findall(r'(Sanders|Jones|Harrington Jr\.) ([\d,]+)',ref): add(num(m[1]))
wk=[x for x in pd.read_html(W+'raw/reference/wikipedia_2022_Arkansas_gubernatorial_election.html') if 'Bland' in x.to_string() and len(x)<12]
for x in wk:
    for _,r in x.iterrows():
        if 'Russell' in str(r.iloc[2]): add(r['Votes'])
add(11)   # Russell's 2022 votes in the SOS feed: checked below against the raw API file
api=json.load(open(W+'raw/2022_primary/api_GetContestResults_STW.json'))['response']['contests']['99']['choices']
if not any(ch['totalVotes']==11 for ch in api): fail.append(('Russell 11 not in raw API',))
# explicit structural whitelist
STRUCT={2022,2026,2025,2020,1844,1843,234,3318,10,36,19,24,3,1,2,4,5,6,7,8,9,11,12,13,14,15,75,100}
lawcite='14-166-202'
n2=0
# ---------- 2c) statewide fitted equation on Locked page: OLS recomputed here with numpy from PASS B (independent of statsmodels)
x=(o.P22-o.P26).values; yv=o.dG.values; X=np.c_[np.ones(len(x)),x]; beta,*_=np.linalg.lstsq(X,yv,rcond=None); e=yv-X@beta
s2=e@e/(len(x)-2); se=np.sqrt(np.diag(s2*np.linalg.inv(X.T@X))); r2=1-e@e/((yv-yv.mean())@(yv-yv.mean()))
FX=dict(b=beta[0],k=beta[1],b_se=se[0],k_se=se[1],r2=r2,n=len(x))
lkt=open(WK+'Locked-Arkansas-Formula.md').read(); fs=lkt.split('## Arkansas fitted equation (final)')[1].split('\n## ')[0]
if lkt.find('## Arkansas fitted equation (final)')>lkt.find('## The equation'): fail.append(('fitted section not near top',))
m_=re.search(r'Arkansas equation:\s+ΔG = ([−+\-][\d.]+) \+ ([\d.]+) ×',fs); m4=re.search(r'Four decimals:\s+ΔG = ([−+\-][\d.]+) \+ ([\d.]+) ×',fs)
for got,v,d in ((m_.group(1),FX['b'],2),(m_.group(2),FX['k'],2),(m4.group(1),FX['b'],4),(m4.group(2),FX['k'],4)):
    n1+=1
    if abs(num(got)-round(v,d))>10**-d*0.51: fail.append(('fitted eq',got,v))
want={'Constant (intercept)':FX['b'],'Constant standard error':FX['b_se'],'Multiplier (slope)':FX['k'],'Multiplier standard error':FX['k_se'],'R²':FX['r2'],'n (counties)':FX['n']}
seen=0
for l in fs.splitlines():
    c=[z.strip() for z in l.strip('|').split('|')]
    if l.startswith('| ') and c[0] in want:
        seen+=1
        for cell,d in ((c[1],2),(c[2],4)):
            n1+=1; d=0 if c[0].startswith('n ') else d
            if abs(num(cell)-round(want[c[0]],d))>10**-max(d,0)*0.51: fail.append(('fitted table',c[0],cell,want[c[0]]))
if seen!=6: fail.append(('fitted table rows',seen))
wx=re.search(r'\*\*Worked example: ([A-Za-z .]+)\*\*',fs).group(1).strip(); dr=o.loc[wx,'P22']-o.loc[wx,'P26']; pr=FX['b']+FX['k']*dr
for tok,v in zip(re.findall(r'Predicted ΔG = .*?= ([−+][\d.]+)\. Actual ΔG = ([−+][\d.]+)\. Difference .*?= ([−+][\d.]+)\.',fs)[0],(pr,o.loc[wx,'dG'],o.loc[wx,'dG']-pr)):
    n1+=1
    if abs(num(tok)-round(v,2))>0.0051: fail.append(('worked example',wx,tok,v))
for v in list(FX.values())+[dr,pr,o.loc[wx,'dG']-pr,FX['r2']*100]: add(v)
if 'Arkansas has no party registration' not in fs or 'UNOFFICIAL' not in fs: fail.append(('fitted section labels',))
sb=open(WK+'_Sidebar.md').read()
for p_ in PAGES:
    if f'/wiki/{p_})' not in sb: fail.append(('sidebar missing',p_))
for p in PAGES:
    txt=open(WK+p+'.md').read()
    body=re.sub(r'\]\([^)]*\)','](URL)',txt); body=re.sub(r'https?://\S+','URL',body); body=body.replace(lawcite,'LAW')
    body=re.sub(r'(?:Nov|Mar|May|March|November)\.? \d{1,2},? ?(?:2022|2026)?','DATE',body); body=re.sub(r'\d{1,2}:\d{2} [AP]M','TIME',body)
    body=re.sub(r'^\s*(\d+)\. ','',body,flags=re.M)   # numbered list markers
    body=re.sub(r'^#+ (\d+)\. ','## ',body,flags=re.M)
    body=re.sub(r'\b(?:line|Line) \d+','line',body); body=re.sub(r'\| (\d{1,2}) \|','| N |',body)
    body=re.sub(r'§ ?','',body); body=re.sub(r'\bv\d+','VER',body); body=re.sub(r'±\d','±',body); body=re.sub(r'R²','R2',body)
    for tok in re.findall(r'[−+\-]?\d[\d,]*(?:\.\d+)?%?',body):
        if tok.startswith('-') or tok.startswith('−') or tok.startswith('+'): pass
        v=num(tok); n2+=1
        if abs(v) in STRUCT and float(v).is_integer(): continue
        if round(v,2) in vals or round(abs(v),2) in vals: continue
        if '.' in tok:
            d=len(tok.split('.')[1].rstrip('%'))
            if any(abs(abs(v)-x)<=10**-d*0.51 for x in vals): continue
        fail.append(('number',p,tok))
# ---------- 2b) positional check of the Home statewide table
h=open(WK+'Home.md').read().split('## Statewide at a glance')[1].split('##')[0]
hr=[[x.strip() for x in l.strip('|').split('|')] for l in h.splitlines() if l.startswith('| ') and not l.startswith('| Measure')]
exp=[(T.prim_demsen_2022,T.prim_demsen_2026,T.prim_demsen_2026-T.prim_demsen_2022),(T.prim_ballots_2022,T.prim_ballots_2026,T.prim_ballots_2026-T.prim_ballots_2022),(P22,P26,P26-P22),
     (T.dem_2022,T.dem_2026,T.dem_2026-T.dem_2022),(T.ballots_2022,T.ballots_2026,T.ballots_2026-T.ballots_2022),(S22,S26,S26-S22),(S22-P22,S26-P26,(S26-P26)-(S22-P22))]
for r,e in zip(hr,exp):
    for cell,v in zip(r[1:4],e):
        x=num(cell.replace('ΔG','').replace('pts','').strip())
        if abs(x-(round(v,2) if '.' in cell else round(v)))>0.0051: fail.append(('home table',r[0],cell,v))
n1+=21
# ---------- 3) labels
for p in PAGES:
    txt=open(WK+p+'.md').read()
    for need in ('Democratic primary-ballot share (proxy — Arkansas has no party registration)','UNOFFICIAL','https://github.com/mbenson8989/Nebraska-Election-Analysis-/wiki/Cedar-Audit'):
        if need not in txt: fail.append(('label missing',p,need))
    if len(re.findall(r'^> ',txt,flags=re.M))<1: fail.append(('banner missing',p))
print(f'full table rows {len(rows)}, table checks {n1}; numbers checked on 5 pages {n2}; FAIL {len(fail)}'); [print(x) for x in fail[:60]]
sys.exit(1 if fail else 0)
