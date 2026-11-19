"""PASS A: bottom-up from the bulk FullDataFile.json of each election (results.tally-enr.com, Arkansas SOS results system).
Vote figures are built by SUMMING PRECINCT ROWS up to each county; turnout comes from the file's county turnout block.
County names: 2022 files carry them; 2026 files are keyed by FIPS, mapped to names with the Census county file.
2026 primary FullDataFile has no contest names, so the contest ID for 'DEM Governor' / 'DEM U.S. Senate' / 'REP U.S. Senate'
is looked up by name in api_GetContestSearchList.json (metadata only; every number still comes from FullDataFile).
Outputs verification/passA_counties.csv and verification/passA_statewide.json"""
import json, csv, re
W='/workspace/arkansas-elections/'; R=W+'raw/'; V=W+'verification/'
cen={}
for r in csv.DictReader(open(R+'census/co-est2025-alldata.csv',encoding='latin-1')):
    if r['SUMLEV']=='050' and r['STATE']=='05': cen['05'+r['COUNTY']]=r['CTYNAME'].replace(' County','')
assert len(cen)==75
norm=lambda s:re.sub(r'[^a-z]','',s.lower().replace('saint','st'))
N={norm(v):v for v in cen.values()}
def load(d): return json.load(open(R+d+'/FullDataFile.json'))
# ---------- 2022 format ----------
def t22(D):
    return {N[norm(c['CountyName'])]:(c['RegisteredVoters'],c['VotesCast']) for c in D['Turnout']['CountyTurnout']}
def c22(D,name):
    cs=[c for c in D['ContestData'] if c['ContestName'].strip()==name]; assert len(cs)==1,name; c=cs[0]
    out={}
    for p in c['Counties']:   # one entry per precinct
        k=N[norm(p['CountyName'])]
        for ch in p['Candidates']: out.setdefault(k,{}); out[k][ch['PartyName']]=out[k].get(ch['PartyName'],0)+ch['TotalVotes']
    tot={}
    for ch in c['Candidates']: tot[ch['PartyName']]=tot.get(ch['PartyName'],0)+ch['TotalVotes']
    return out,tot
# ---------- 2026 format ----------
def t26(D):
    return {cen[f]:(L['RegisteredVoters'],L['TotalBallotsCast']) for f,L in D['TurnoutData']['Locations'].items()}
def chv(ch): return ch['TotalVotes'] if 'TotalVotes' in ch else sum(v['Votes'] for v in ch.get('Votes',[]))
def c26(D,cid,parties):
    cs=[c for c in D['ContestData'] if c['ContestID']==cid]; assert len(cs)==1,cid; c=cs[0]
    out={}; agg_ok=True
    for f,L in c['Locations'].items():
        k=cen[f]; out[k]={}
        for pid,P in L['Locations'].items():   # precincts
            for ch in P['Choices']+P.get('WriteinChoices',[]):
                pn=parties.get(ch.get('PartyID'),'Write-in'); out[k][pn]=out[k].get(pn,0)+chv(ch)
        cty={}
        for ch in L['Choices']+L.get('WriteinChoices',[]): pn=parties.get(ch.get('PartyID'),'Write-in'); cty[pn]=cty.get(pn,0)+ch['TotalVotes']
        if cty!=out[k]: agg_ok=False
    tot={}
    for ch in c['Choices']+c.get('WriteinChoices',[]): pn=parties.get(ch.get('PartyID'),'Write-in'); tot[pn]=tot.get(pn,0)+ch['TotalVotes']
    return out,tot,agg_ok
def cid_by_name(d,name):
    j=json.load(open(R+d+'/api_GetContestSearchList.json'))['response']['contests']
    ids=[k for k,v in j.items() if v['contestName']==name]; assert len(ids)==1,(d,name); return ids[0]
def parties(d): return {k:v['partyName'] for k,v in json.load(open(R+d+'/api_GetElectionInfo.json'))['response']['parties'].items()}
rows={c:{'county':c} for c in sorted(cen.values())}; SW={}; CHK={}
isdem=lambda p:p.startswith('Democratic'); isrep=lambda p:p.startswith('Republican')
# ---- 2022 general
D=load('2022'); t=t22(D); g,sw=c22(D,'Governor')
SW['2022']=dict(gov=sw,ballots=D['Turnout']['VotesCast'],reg=D['Turnout']['RegisteredVoters'],official=D['ElectionInfo']['IsOfficial'])
for c,(reg,bal) in t.items():
    r=rows[c]; v=g[c]; r['reg_2022']=reg; r['ballots_2022']=bal
    r['dem_2022']=sum(n for p,n in v.items() if isdem(p)); r['rep_2022']=sum(n for p,n in v.items() if isrep(p))
    r['other_2022']=sum(n for p,n in v.items() if not isdem(p) and not isrep(p)); r['govtotal_2022']=sum(v.values())
# ---- 2022 primary
D=load('2022_primary'); t=t22(D)
gd,swd=c22(D,'Governor - DEM'); gr,swr=c22(D,'Governor - REP'); sd,sws=c22(D,'U.S. Senate - DEM'); sr,swsr=c22(D,'U.S. Senate - REP')
SW['2022_primary']=dict(gov_dem=sum(swd.values()),gov_rep=sum(swr.values()),sen_dem=sum(sws.values()),sen_rep=sum(swsr.values()),ballots=D['Turnout']['VotesCast'],reg=D['Turnout']['RegisteredVoters'],official=D['ElectionInfo']['IsOfficial'])
for c,(reg,bal) in t.items():
    r=rows[c]; r['prim_reg_2022']=reg; r['prim_ballots_2022']=bal
    r['prim_dem_2022']=sum(gd[c].values()); r['prim_rep_2022']=sum(gr[c].values()); r['prim_demsen_2022']=sum(sd[c].values()); r['prim_repsen_2022']=sum(sr[c].values())
# ---- 2026 general
D=load('2026'); P=parties('2026'); t=t26(D)
gc=[c for c in D['ContestData'] if c.get('ContestName')=='Governor']; assert len(gc)==1
g,sw,ok=c26(D,gc[0]['ContestID'],P); CHK['2026_gov_precinct_sum_equals_county_rows']=ok
SW['2026']=dict(gov=sw,ballots=D['TurnoutData']['TotalBallotsCast'],reg=D['TurnoutData']['RegisteredVoters'],official_flag=D['ElectionData']['IsOfficial'])
for c,(reg,bal) in t.items():
    r=rows[c]; v=g[c]; r['reg_2026']=reg; r['ballots_2026']=bal
    r['dem_2026']=sum(n for p,n in v.items() if isdem(p)); r['rep_2026']=sum(n for p,n in v.items() if isrep(p))
    r['other_2026']=sum(n for p,n in v.items() if not isdem(p) and not isrep(p)); r['govtotal_2026']=sum(v.values())
# ---- 2026 primary (no REP governor primary on the ballot: Sanders unopposed)
D=load('2026_primary'); P=parties('2026_primary'); t=t26(D)
gd,swd,ok1=c26(D,cid_by_name('2026_primary','DEM Governor'),P); sd,sws,ok2=c26(D,cid_by_name('2026_primary','DEM U.S. Senate'),P); sr,swsr,ok3=c26(D,cid_by_name('2026_primary','REP U.S. Senate'),P)
CHK['2026p_precinct_sum_equals_county_rows']=ok1 and ok2 and ok3
SW['2026_primary']=dict(gov_dem=sum(swd.values()),gov_rep=None,sen_dem=sum(sws.values()),sen_rep=sum(swsr.values()),ballots=D['TurnoutData']['TotalBallotsCast'],reg=D['TurnoutData']['RegisteredVoters'],official_flag=D['ElectionData']['IsOfficial'])
for c,(reg,bal) in t.items():
    r=rows[c]; r['prim_reg_2026']=reg; r['prim_ballots_2026']=bal
    r['prim_dem_2026']=sum(gd[c].values()); r['prim_demsen_2026']=sum(sd[c].values()); r['prim_repsen_2026']=sum(sr[c].values())
assert len(rows)==75
F=['county','reg_2022','ballots_2022','dem_2022','rep_2022','other_2022','govtotal_2022','prim_reg_2022','prim_ballots_2022','prim_dem_2022','prim_rep_2022','prim_demsen_2022','prim_repsen_2022',
   'reg_2026','ballots_2026','dem_2026','rep_2026','other_2026','govtotal_2026','prim_reg_2026','prim_ballots_2026','prim_dem_2026','prim_demsen_2026','prim_repsen_2026']
for r in rows.values(): assert all(k in r for k in F),r
with open(V+'passA_counties.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=F); w.writeheader(); [w.writerow(rows[c]) for c in sorted(rows)]
S=lambda k:sum(r[k] for r in rows.values())
for y in ('2022','2026'):
    gv=SW[y]['gov']
    CHK[y]=dict(dem=S(f'dem_{y}')==sum(n for p,n in gv.items() if isdem(p)),rep=S(f'rep_{y}')==sum(n for p,n in gv.items() if isrep(p)),govtotal=S(f'govtotal_{y}')==sum(gv.values()),
                ballots=S(f'ballots_{y}')==SW[y]['ballots'],reg=S(f'reg_{y}')==SW[y]['reg'])
    p=SW[y+'_primary']
    CHK[y+'_primary']=dict(gov_dem=S(f'prim_dem_{y}')==p['gov_dem'],sen_dem=S(f'prim_demsen_{y}')==p['sen_dem'],sen_rep=S(f'prim_repsen_{y}')==p['sen_rep'],ballots=S(f'prim_ballots_{y}')==p['ballots'],reg=S(f'prim_reg_{y}')==p['reg'])
CHK['2022_primary']['gov_rep']=S('prim_rep_2022')==SW['2022_primary']['gov_rep']
json.dump(dict(statewide=SW,county_sum_equals_statewide=CHK),open(V+'passA_statewide.json','w'),indent=1)
print(json.dumps(CHK)); print(len(rows),'counties x',len(F)-1,'figures')
