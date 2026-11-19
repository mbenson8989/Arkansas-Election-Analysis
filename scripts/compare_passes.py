"""Compare pass A (bulk FullDataFile.json, precinct rows summed to counties) vs pass B (SOS results API, county rows)
figure by figure, then adjudicate every mismatch with independent checks:
  check 1 (internal): does the figure fit inside the ballots cast that the SAME bulk file reports for that county?
          (a governor total, or Dem + Rep governor-primary votes, larger than ballots cast is impossible)
  check 2 (third source, 2022 general, all 75 counties): Wikipedia county table for the 2022 race (secondary; cites the SOS)
  check 3 (county certification): White County Election Commission certified totals as published by the White County Citizen, Nov 18 2022
  check 4 (statewide, third source): statewide primary totals on Wikipedia (2022 governor primaries, 2022 and 2026 U.S. Senate primaries,
          2026 Democratic governor primary) vs the county sums of each pass. If pass B's sum equals the published total and pass A exceeds it by
          exactly the sum of the county mismatches, the mismatching counties are resolved for pass B.
Outputs verification/compare_A_B_figure_by_figure.csv, verification/compare_report.json, verification/adjudication.csv"""
import csv, json, pandas as pd
W='/workspace/arkansas-elections/'; V=W+'verification/'; R=W+'raw/'
A={r['county']:{k:int(v) for k,v in r.items() if k!='county'} for r in csv.DictReader(open(V+'passA_counties.csv'))}
B={r['county']:{k:int(v) for k,v in r.items() if k!='county'} for r in csv.DictReader(open(V+'passB_counties.csv'))}
assert set(A)==set(B) and len(A)==75
F=list(next(iter(A.values())))
rows=[]; mm=[]
for c in sorted(A):
    for f in F:
        a,b=A[c][f],B[c][f]; ok=a==b; rows.append(dict(county=c,figure=f,passA=a,passB=b,match=ok))
        if not ok: mm.append(dict(county=c,figure=f,passA=a,passB=b,diff=a-b))
with open(V+'compare_A_B_figure_by_figure.csv','w',newline='') as fh:
    w=csv.DictWriter(fh,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
# ---- check 2: Wikipedia 2022 county table
t=[x for x in pd.read_html(R+'reference/wikipedia_2022_Arkansas_gubernatorial_election.html') if len(x)>70][0]
t.columns=['county','rep','rep_pct','dem','dem_pct','lib','lib_pct','margin','margin_pct','total']
t=t[t.county.isin(A.keys())].set_index('county'); assert len(t)==75
WK={c:dict(dem_2022=int(t.loc[c,'dem']),rep_2022=int(t.loc[c,'rep']),other_2022=int(t.loc[c,'lib']),govtotal_2022=int(t.loc[c,'total'])) for c in t.index}
wk_vs={p:sum(1 for c in WK for k,v in WK[c].items() if v!=X[c][k]) for p,X in (('passA',A),('passB',B))}
# ---- check 3: White County certified
WHITE=dict(dem_2022=4613,rep_2022=18010,other_2022=502)
# ---- check 4: statewide primary totals from Wikipedia result tables (votes copied by parser, not by hand)
def wtot(fn,cands):
    for x in pd.read_html(R+'reference/'+fn):
        st=x.to_string()
        if 'Total votes' in st and len(x)<12 and all(c in st for c in cands):
            return int(x[x.iloc[:,0].astype(str)=='Total votes'].iloc[0]['Votes'])
    raise SystemExit('wiki table not found '+fn)
WS={'prim_rep_2022':wtot('wikipedia_2022_Arkansas_gubernatorial_election.html',['Washburn','Sanders']),
    'prim_dem_2022':wtot('wikipedia_2022_Arkansas_gubernatorial_election.html',['Bland','Jones']),
    'prim_demsen_2022':wtot('wikipedia_2022_US_Senate_election_in_Arkansas.html',['Natalie James','Whitfield']),
    'prim_repsen_2022':wtot('wikipedia_2022_US_Senate_election_in_Arkansas.html',['Bequette','Loftis']),
    'prim_demsen_2026':wtot('wikipedia_2026_US_Senate_election_in_Arkansas.html',['Shoffner','Dunbar']),
    'prim_repsen_2026':wtot('wikipedia_2026_US_Senate_election_in_Arkansas.html',['Ashby','Little']),
    'prim_dem_2026':wtot('wikipedia_2026_Arkansas_gubernatorial_election.html',['Xayprasith-Mays','Love'])}
STW={k:dict(wikipedia=v,passA_sum=sum(A[c][k] for c in A),passB_sum=sum(B[c][k] for c in B)) for k,v in WS.items()}
for k,d in STW.items():
    d['passB_equals_wikipedia']=d['passB_sum']==d['wikipedia']; d['passA_minus_wikipedia']=d['passA_sum']-d['wikipedia']
    d['sum_of_county_mismatches']=sum(A[c][k]-B[c][k] for c in A)
ADJ=[]
for m in mm:
    c,f,y=m['county'],m['figure'],m['figure'][-4:]
    d=dict(m)
    if f in('dem_2022','rep_2022','other_2022','govtotal_2022'):
        d['passA_gov_total_vs_ballots']=f"{A[c]['govtotal_2022']:,} governor votes vs {A[c]['ballots_2022']:,} ballots in the same file ({'IMPOSSIBLE' if A[c]['govtotal_2022']>A[c]['ballots_2022'] else 'fits'})"
        d['wikipedia']=WK[c][f]; d['wikipedia_agrees_with']='passB' if WK[c][f]==m['passB'] else ('passA' if WK[c][f]==m['passA'] else 'neither')
        if c=='White' and f in WHITE: d['county_certified']=WHITE[f]; d['certified_agrees_with']='passB' if WHITE[f]==m['passB'] else 'passA' if WHITE[f]==m['passA'] else 'neither'
    elif f.startswith('prim_'):
        a2=A[c]['prim_dem_2022']+A[c]['prim_rep_2022']; b2=B[c]['prim_dem_2022']+B[c]['prim_rep_2022']
        d['passA_primary_DR_vs_ballots']=f"{a2:,} Dem + Rep governor-primary votes vs {A[c]['prim_ballots_2022']:,} primary ballots in the same file ({'IMPOSSIBLE' if a2>A[c]['prim_ballots_2022'] else 'fits'}); pass B: {b2:,} ({'fits' if b2<=B[c]['prim_ballots_2022'] else 'IMPOSSIBLE'})"
        s2=A[c]['prim_demsen_2022']+A[c]['prim_repsen_2022']; d['passA_primary_senate_DR_vs_ballots']=f"{s2:,} vs {A[c]['prim_ballots_2022']:,} ({'IMPOSSIBLE' if s2>A[c]['prim_ballots_2022'] else 'fits'})"
    if f in STW: d['statewide_check']=f"pass B county sum {STW[f]['passB_sum']:,} vs published statewide {STW[f]['wikipedia']:,} ({'equal' if STW[f]['passB_equals_wikipedia'] else 'DIFFERENT'}); pass A exceeds published by {STW[f]['passA_minus_wikipedia']:,} = sum of county mismatches {STW[f]['sum_of_county_mismatches']:,}"
    d['resolved_for']='passB' if (any(k.startswith('passA_') and 'IMPOSSIBLE' in str(v) for k,v in d.items()) or d.get('wikipedia_agrees_with')=='passB'
        or (f in STW and STW[f]['passB_equals_wikipedia'] and STW[f]['passA_minus_wikipedia']==STW[f]['sum_of_county_mismatches'])) else 'UNRESOLVED'
    ADJ.append(d)
pd.DataFrame(ADJ).to_csv(V+'adjudication.csv',index=False)
USED=['reg_2022','ballots_2022','dem_2022','rep_2022','other_2022','govtotal_2022','prim_ballots_2022','prim_demsen_2022','prim_repsen_2022',
      'reg_2026','ballots_2026','dem_2026','rep_2026','other_2026','govtotal_2026','prim_ballots_2026','prim_demsen_2026','prim_repsen_2026']   # = analysis.py USED
crit=[m for m in mm if m['figure'] in USED]
bad_counties=sorted({m['county'] for m in mm})
resolved=all(d['resolved_for']=='passB' for d in ADJ)
rep=dict(counties=75,figures_per_county=len(F),total_comparisons=len(rows),matched=sum(r['match'] for r in rows),mismatched=len(mm),
         mismatch_counties=bad_counties,mismatch_elections=sorted({m['figure'][-4:] for m in mm}),
         mismatches=mm,mismatches_in_analysis_figures=crit,
         comparisons_2026=sum(1 for r in rows if r['figure'].endswith('2026')),matched_2026=sum(1 for r in rows if r['figure'].endswith('2026') and r['match']),
         comparisons_outside_mismatch_counties=sum(1 for r in rows if r['county'] not in bad_counties),matched_outside_mismatch_counties=sum(1 for r in rows if r['county'] not in bad_counties and r['match']),
         wikipedia_2022_general_check=dict(figures=4*75,disagree_with_passA=wk_vs['passA'],disagree_with_passB=wk_vs['passB']),
         statewide_third_source_check=STW,adjudication=ADJ,
         all_analysis_mismatches_resolved_for_passB=all(d['resolved_for']=='passB' for d in ADJ if d['figure'] in USED),
         unresolved=[(d['county'],d['figure'],d['passA'],d['passB'],'used in analysis' if d['figure'] in USED else 'NOT used in any calculation') for d in ADJ if d['resolved_for']!='passB'],all_mismatches_resolved_in_favor_of_passB=resolved,
         CLEAN_analysis_figures=len(crit)==0)
json.dump(rep,open(V+'compare_report.json','w'),indent=1)
print(json.dumps({k:v for k,v in rep.items() if k not in('mismatches','adjudication','mismatches_in_analysis_figures')},indent=0)); print(pd.DataFrame(ADJ).to_string())
