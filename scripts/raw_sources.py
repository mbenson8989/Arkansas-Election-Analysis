"""Raw-source loader (independent of the pipeline): BULK (FullDataFile.json) and API county figures, keyed by FIPS. Copied from independent_pdf_check.py."""
import json, re, subprocess, sys, csv
R='/workspace/arkansas-elections/raw/'; OUT='/workspace/arkansas-elections/verification/independent_pdf_check/'
J=lambda p:json.load(open(R+p))
key=lambda s:re.sub(r'[^A-Z]','',s.upper())          # 'ST FRANCIS' == 'St. Francis'
def contest_id(el,name):
    cs=J(el+'/api_GetContestSearchList.json')['response']['contests']; it=cs.values() if isinstance(cs,dict) else cs
    hits=[c for c in it if (c.get('contestName') or '').strip()==name]; assert len(hits)==1,(el,name,len(hits)); c=hits[0]
    return str(c.get('contestId') or c.get('contestID')), {str(k):(v.get('name'),str(v.get('partyID') or v.get('partyId'))) for k,v in c['choices'].items()}
def dem_party(el):
    ps=J(el+'/api_GetElectionInfo.json')['response']['parties']; d=[k for k,v in ps.items() if v['partyName'] in ('Democratic Party','Democratic')]; assert len(d)==1; return d[0]
SRCF={}  # field -> file/field description
# ---------------- BULK
def bulk_2022(el,cname,dem_only):
    d=J(el+'/FullDataFile.json'); c=[x for x in d['ContestData'] if x['ContestName'].strip()==cname]; assert len(c)==1,(el,cname)
    out={}
    for p in c[0]['Counties']:
        v=sum(x['TotalVotes'] for x in p['Candidates'] if (x['PartyName']=='Democratic Party' if dem_only else True))
        out[key(p['CountyName'])]=out.get(key(p['CountyName']),0)+v
    tb={key(t['CountyName']):t['VotesCast'] for t in d['Turnout']['CountyTurnout']}
    return out,tb
def bulk_2026(el,cid,choice_ids,names):
    d=J(el+'/FullDataFile.json'); c=[x for x in d['ContestData'] if x['ContestID']==cid]; assert len(c)==1
    out={}
    for fips,L in c[0]['Locations'].items():
        out[fips]=sum(x['TotalVotes'] for x in L['Choices'] if x['ChoiceID'] in choice_ids)
        if L.get('LocationName'): names[fips]=L['LocationName']
    tl=d['TurnoutData']['Locations']; tb={f:v['TotalBallotsCast'] for f,v in tl.items()}
    for f,v in tl.items():
        if v.get('LocationName'): names.setdefault(f,v['LocationName'])
    return out,tb
# ---------------- API
def api(el,files,cid,choice_ids):
    out=None
    for fn in files:
        cs=J(el+'/'+fn)['response']['contests']
        if cid in cs: out={f:sum(x['totalVotes'] for x in L['choices'] if str(x['choiceID']) in choice_ids) for f,L in cs[cid]['locations'].items()}
    assert out is not None,(el,cid)
    tb={f:v['totalBallotsCast'] for f,v in J(el+'/api_GetTurnout.json')['response']['locations'].items()}
    return out,tb
NAMES={}
# 2026 general governor (Dem choice by party id) ; 2026 primary DEM U.S. Senate (all choices)
g26,ch=contest_id('2026','Governor'); dp=dem_party('2026'); g26c={k for k,(n,p) in ch.items() if p==dp}
s26,ch=contest_id('2026_primary','DEM U.S. Senate'); s26c=set(ch)
B={}; A={}
B['dem_2026'],B['ballots_2026']=bulk_2026('2026',g26,g26c,NAMES)
B['dsen_2026'],B['pballots_2026']=bulk_2026('2026_primary',s26,s26c,NAMES)
A['dem_2026'],A['ballots_2026']=api('2026',['api_GetContestResults_Statewide.json','api_GetContestResults_Federal.json'],g26,g26c)
A['dsen_2026'],A['pballots_2026']=api('2026_primary',['api_GetContestResults_Statewide.json','api_GetContestResults_Federal.json'],s26,s26c)
# census FIPS names (raw/census) as a cross-check of FIPS->county names
cen={}
for r in csv.DictReader(open(R+'census/co-est2025-alldata.csv',encoding='latin-1')):
    if r['STATE']=='05' and r['SUMLEV']=='050': cen['05'+r['COUNTY']]=r['CTYNAME'].replace(' County','')
assert len(NAMES)==75 and all(key(NAMES[f])==key(cen[f]) for f in NAMES), 'FIPS name mismatch'
K2F={key(n):f for f,n in NAMES.items()}
g22,ch=contest_id('2022','Governor'); dp22=dem_party('2022'); g22c={k for k,(n,p) in ch.items() if p==dp22}
s22,ch=contest_id('2022_primary','U.S. Senate - DEM'); s22c=set(ch)
b,t=bulk_2022('2022','Governor',True); B['dem_2022']={K2F[k]:v for k,v in b.items()}; B['ballots_2022']={K2F[k]:v for k,v in t.items()}
b,t=bulk_2022('2022_primary','U.S. Senate - DEM',False); B['dsen_2022']={K2F[k]:v for k,v in b.items()}; B['pballots_2022']={K2F[k]:v for k,v in t.items()}
A['dem_2022'],A['ballots_2022']=api('2022',['api_GetContestResults_STW.json','api_GetContestResults_FED.json'],g22,g22c)
A['dsen_2022'],A['pballots_2022']=api('2022_primary',['api_GetContestResults_STW.json','api_GetContestResults_FED.json'],s22,s22c)
for S in (A,B):
    for k,v in S.items(): assert len(v)==75 and set(v)==set(NAMES),(k,len(v))
FILE={'dem_2022':('2022/FullDataFile.json: ContestData[Governor].Counties[*].Candidates[PartyName=Democratic Party].TotalVotes summed by CountyName','2022/api_GetContestResults_STW.json: contests[286].locations[fips].choices[partyID=2099].totalVotes'),
      'ballots_2022':('2022/FullDataFile.json: Turnout.CountyTurnout[].VotesCast','2022/api_GetTurnout.json: response.locations[fips].totalBallotsCast'),
      'dem_2026':('2026/FullDataFile.json: ContestData[Governor].Locations[fips].Choices[DEM Fred Love].TotalVotes','2026/api_GetContestResults_Statewide.json: contests[Governor].locations[fips].choices[DEM].totalVotes'),
      'ballots_2026':('2026/FullDataFile.json: TurnoutData.Locations[fips].TotalBallotsCast','2026/api_GetTurnout.json: response.locations[fips].totalBallotsCast'),
      'dsen_2026':('2026_primary/FullDataFile.json: ContestData[DEM U.S. Senate].Locations[fips].Choices[*].TotalVotes','2026_primary/api_GetContestResults_Federal.json: contests[DEM U.S. Senate].locations[fips].choices[*].totalVotes'),
      'pballots_2026':('2026_primary/FullDataFile.json: TurnoutData.Locations[fips].TotalBallotsCast','2026_primary/api_GetTurnout.json: response.locations[fips].totalBallotsCast')}
