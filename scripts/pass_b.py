"""PASS B: independent of pass A. Uses the results API the SOS site itself calls (host enr-results-api.totalresults.com),
NOT the bulk FullDataFile:
  - county vote totals: api_GetContestResults_<type>.json  'locations' (county-level rows as published; no precinct summing)
  - county registered voters / ballots cast: api_GetTurnout.json  response.locations
  - contest names: api_GetContestSearchList.json ; party names: api_GetElectionInfo.json ; county names: api_GetElectionInfo.json locations
Parsed with regex over the raw text for the turnout and names (no json module for those) and json for the contest blocks.
Outputs verification/passB_counties.csv and verification/passB_sources.json"""
import re, json, csv
W='/workspace/arkansas-elections/'; R=W+'raw/'; V=W+'verification/'
txt=lambda d,f:open(R+d+'/'+f,encoding='utf-8').read()
def county_names(d):
    t=txt(d,'api_GetElectionInfo.json')
    m=dict(re.findall(r'"locationID":"(05\d{3})","locationName":"([^"]+)"',t)); assert len(m)==75,(d,len(m))
    canon=lambda s:re.sub(r'^St\.? ','St. ',' '.join(w.capitalize() for w in s.split()))   # 'ST FRANCIS' / 'St. Francis' -> 'St. Francis'
    return {f:canon(v) for f,v in m.items()}
def party_names(d):
    t=txt(d,'api_GetElectionInfo.json'); return dict(re.findall(r'"partyID":"([^"]+)","abbreviation":(?:null|"[^"]*"),"partyName":"([^"]*)"',t))
def turnout(d):
    t=txt(d,'api_GetTurnout.json')
    rows=re.findall(r'"(05\d{3})":\{"locationID":"\1","registeredVoters":(\d+),.*?"totalBallotsCast":(\d+)',t); assert len(rows)==75,(d,len(rows))
    st=re.search(r'"response":\{"registeredVoters":(\d+),.*?"totalBallotsCast":(\d+)',t)
    return {f:(int(a),int(b)) for f,a,b in rows},(int(st.group(1)),int(st.group(2)))
def contest_id(d,name):
    t=txt(d,'api_GetContestSearchList.json')
    ids=re.findall(r'"contestId":"([^"]+)","contestName":"'+re.escape(name)+r'"',t); assert len(ids)==1,(d,name,ids); return ids[0]
def contest(d,ctype,cid,P):
    j=json.loads(txt(d,f'api_GetContestResults_{ctype}.json'))['response']['contests'][cid]
    out={}
    for f,L in j['locations'].items():
        out[f]={}
        for ch in L['choices']+L.get('writeinChoices',[]): p=P.get(ch.get('partyID'),'Write-in'); out[f][p]=out[f].get(p,0)+ch['totalVotes']
    tot={}
    for ch in j['choices']+j.get('writeInChoices',[]): p=P.get(ch.get('partyID'),'Write-in'); tot[p]=tot.get(p,0)+ch['totalVotes']
    return out,tot
isdem=lambda p:p.lower().startswith('democrat'); isrep=lambda p:p.lower().startswith('republican')
out={}; SRC={}; ST={}
for y,(ST_T,FED) in (('2022',('STW','FED')),('2026',('Statewide','Federal'))):
    d=y; nm=county_names(d); P=party_names(d); T,stt=turnout(d)
    gid=contest_id(d,'Governor'); g,gt=contest(d,ST_T,gid,P); ST[y]=dict(gov=gt,reg=stt[0],ballots=stt[1])
    for f,c in nm.items():
        r=out.setdefault(c,{'county':c}); v=g[f]
        r[f'reg_{y}'],r[f'ballots_{y}']=T[f]
        r[f'dem_{y}']=sum(n for p,n in v.items() if isdem(p)); r[f'rep_{y}']=sum(n for p,n in v.items() if isrep(p))
        r[f'other_{y}']=sum(n for p,n in v.items() if not isdem(p) and not isrep(p)); r[f'govtotal_{y}']=sum(v.values())
    SRC[d]=dict(governor_contest_id=gid,files=['api_GetContestResults_'+ST_T+'.json','api_GetTurnout.json','api_GetElectionInfo.json','api_GetContestSearchList.json'])
    d=y+'_primary'; nm=county_names(d); P=party_names(d); T,stt=turnout(d)
    names=dict(gov_dem='Governor - DEM' if y=='2022' else 'DEM Governor',sen_dem='U.S. Senate - DEM' if y=='2022' else 'DEM U.S. Senate',sen_rep='U.S. Senate - REP' if y=='2022' else 'REP U.S. Senate')
    if y=='2022': names['gov_rep']='Governor - REP'
    res={}
    for k,n in names.items():
        cid=contest_id(d,n); ct=ST_T if 'Governor' in n else FED; res[k]=contest(d,ct,cid,P); SRC.setdefault(d,{})[k]=dict(name=n,id=cid,file='api_GetContestResults_'+ct+'.json')
    ST[d]=dict(reg=stt[0],ballots=stt[1],**{k:sum(v[1].values()) for k,v in res.items()})
    for f,c in nm.items():
        r=out[c]; r[f'prim_reg_{y}'],r[f'prim_ballots_{y}']=T[f]
        r[f'prim_dem_{y}']=sum(res['gov_dem'][0][f].values()); r[f'prim_demsen_{y}']=sum(res['sen_dem'][0][f].values()); r[f'prim_repsen_{y}']=sum(res['sen_rep'][0][f].values())
        if y=='2022': r['prim_rep_2022']=sum(res['gov_rep'][0][f].values())
F=[l for l in open(V+'passA_counties.csv').readline().strip().split(',')]
assert len(out)==75
with open(V+'passB_counties.csv','w',newline='') as fh:
    w=csv.DictWriter(fh,fieldnames=F); w.writeheader(); [w.writerow(out[c]) for c in sorted(out)]
S=lambda k:sum(r[k] for r in out.values())
CHK={y:dict(dem=S(f'dem_{y}')==sum(n for p,n in ST[y]['gov'].items() if isdem(p)),ballots=S(f'ballots_{y}')==ST[y]['ballots'],reg=S(f'reg_{y}')==ST[y]['reg'],govtotal=S(f'govtotal_{y}')==sum(ST[y]['gov'].values())) for y in ('2022','2026')}
for y in ('2022','2026'): CHK[y+'_primary']=dict(gov_dem=S(f'prim_dem_{y}')==ST[y+'_primary']['gov_dem'],ballots=S(f'prim_ballots_{y}')==ST[y+'_primary']['ballots'],sen_dem=S(f'prim_demsen_{y}')==ST[y+'_primary']['sen_dem'],sen_rep=S(f'prim_repsen_{y}')==ST[y+'_primary']['sen_rep'])
json.dump(dict(sources=SRC,statewide=ST,county_sum_equals_statewide=CHK),open(V+'passB_sources.json','w'),indent=1)
print(json.dumps(CHK)); print(json.dumps(ST,indent=0))
