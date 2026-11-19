"""Download every raw source used, from the Arkansas Secretary of State's official results system (arkansas.tally-enr.com,
linked from https://www.sos.arkansas.gov/elections/research/election-results).
  PASS A source: the bulk 'FullDataFile.json' per election (host results.tally-enr.com; the site's 'download full election' file)
  PASS B source: the results API the site itself calls (host enr-results-api.totalresults.com): GetElectionInfo, GetContestSearchList,
                 GetTurnout (county turnout) and GetContestResults (county contest totals) per election.
Every URL, HTTP status, byte count and retrieval time goes to raw/download_log.json and raw/<election>/SOURCE.txt."""
import subprocess, json, datetime, os
R='/workspace/arkansas-elections/raw/'
EL={'2022':'1844','2022_primary':'1843','2026':'11b07106-031e-4d7c-911a-d01fb473d6dd','2026_primary':'7f77a178-af02-40ec-92db-c5cc50882c68'}
CT={'2022':['STW','FED'],'2022_primary':['STW','FED'],'2026':['Statewide','Federal'],'2026_primary':['Statewide','Federal']}
API='https://enr-results-api.totalresults.com/'
log=[]
def get(url,out):
    r=subprocess.run(['curl','-sL','--compressed','-m','180','-A','Mozilla/5.0','-o',out,'-w','%{http_code} %{size_download}',url],capture_output=True,text=True).stdout.split()
    e=dict(url=url,file=out.replace(R,'raw/'),http=r[0],bytes=int(float(r[1])),retrieved=datetime.datetime.now().astimezone().isoformat(timespec='seconds')); log.append(e); return e
for d,eid in EL.items():
    os.makedirs(R+d,exist_ok=True); L=[]
    L.append(get(f'https://results.tally-enr.com/results/arkansas/{eid}/FullDataFile.json',R+d+'/FullDataFile.json'))
    L.append(get(API+f'Election/GetElectionInfo?cId=arkansas&electionID={eid}',R+d+'/api_GetElectionInfo.json'))
    L.append(get(API+f'Contest/GetContestSearchList?cid=arkansas&electionID={eid}',R+d+'/api_GetContestSearchList.json'))
    L.append(get(API+f'Turnout/GetTurnout?cId=arkansas&electionID={eid}',R+d+'/api_GetTurnout.json'))
    for ct in CT[d]: L.append(get(API+f'Contest/GetContestResults?cId=arkansas&electionID={eid}&contestType={ct}',R+d+f'/api_GetContestResults_{ct}.json'))
    with open(R+d+'/SOURCE.txt','w') as f:
        f.write(f'Arkansas Secretary of State election results (arkansas.tally-enr.com), election ID {eid}\nViewer: https://arkansas.tally-enr.com/#election={eid}\n')
        for e in L: f.write(f"{e['url']}  http={e['http']} bytes={e['bytes']} retrieved={e['retrieved']}\n")
    print(d,[e['http'] for e in L])
for u,f in [('https://arkansas.tally-enr.com/appConfig.json','tally_appConfig.json'),(API+'Client/GetClientConfig?cId=arkansas','tally_GetClientConfig.json'),
            (API+'Election/GetElectionList?cId=arkansas','tally_GetElectionList.json'),('https://www.sos.arkansas.gov/elections/research/election-results','sos_election-results_page.html')]:
    get(u,R+f)
json.dump(log,open(R+'download_log.json','w'),indent=1)
print(sum(e['http']!='200' for e in log),'failures')
