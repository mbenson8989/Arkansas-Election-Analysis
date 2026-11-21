"""Arkansas governor 2022 vs 2026 county analysis.
Input table: pass B (SOS results API county rows). Assertion: pass A equals pass B on EVERY analysis figure except the
mismatches listed in verification/compare_report.json, each of which must be adjudicated for pass B by an independent check.
PROXY: P = Democratic U.S. Senate primary votes / total primary ballots cast (Democratic primary-ballot share; Arkansas has no party registration)."""
import pandas as pd, numpy as np, json, statsmodels.api as sm, statsmodels.formula.api as smf
from scipy import stats
W='/workspace/arkansas-elections/'; V=W+'verification/'; O=W+'repo/'
A=pd.read_csv(V+'passA_counties.csv',index_col='county'); B=pd.read_csv(V+'passB_counties.csv',index_col='county'); CR=json.load(open(V+'compare_report.json'))
USED=['reg_2022','ballots_2022','dem_2022','rep_2022','other_2022','govtotal_2022','prim_ballots_2022','prim_demsen_2022','prim_repsen_2022',
      'reg_2026','ballots_2026','dem_2026','rep_2026','other_2026','govtotal_2026','prim_ballots_2026','prim_demsen_2026','prim_repsen_2026']
adj={(d['county'],d['figure']) for d in CR['adjudication'] if d['resolved_for']=='passB'}
diff=[(c,f) for f in USED for c in A.index if A.loc[c,f]!=B.loc[c,f]]
assert all(x in adj for x in diff), ('unadjudicated pass A/B disagreement', [x for x in diff if x not in adj])
ADJ_USED=sorted(diff)
o=B.copy()
c=pd.read_csv(W+'raw/census/co-est2025-alldata.csv',encoding='latin-1',dtype={'STATE':str,'COUNTY':str,'SUMLEV':str})
c=c[(c.SUMLEV=='050')&(c.STATE=='05')]; c.index=c.CTYNAME.str.replace(' County','')
o['pop2025']=c.POPESTIMATE2025.reindex(o.index); o['pop2020base']=c.ESTIMATESBASE2020.reindex(o.index); assert o.pop2025.notna().all()
o=o.sort_values('pop2025',ascending=False)
# Planning and development districts, Ark. Code § 14-166-202; grouped into four regions for the regional test
PDD={'Northwest':['Baxter','Benton','Boone','Carroll','Madison','Marion','Newton','Searcy','Washington'],
 'Western':['Crawford','Franklin','Logan','Polk','Scott','Sebastian'],
 'White River':['Cleburne','Fulton','Independence','Izard','Jackson','Sharp','Stone','Van Buren','White','Woodruff'],
 'East':['Clay','Craighead','Crittenden','Cross','Greene','Lawrence','Lee','Mississippi','Phillips','Poinsett','Randolph','St. Francis'],
 'Central':['Faulkner','Lonoke','Monroe','Prairie','Pulaski','Saline'],
 'West Central':['Clark','Conway','Garland','Hot Spring','Johnson','Montgomery','Perry','Pike','Pope','Yell'],
 'Southwest':['Calhoun','Columbia','Dallas','Hempstead','Howard','Lafayette','Little River','Miller','Nevada','Ouachita','Sevier','Union'],
 'Southeast':['Arkansas','Ashley','Bradley','Chicot','Cleveland','Desha','Drew','Grant','Jefferson','Lincoln']}
REG={'Northwest':'Northwest','Western':'Northwest','Central':'Central','West Central':'Central','White River':'Northeast','East':'Northeast','Southwest':'South','Southeast':'South'}
pdd={x:k for k,v in PDD.items() for x in v}; assert len(pdd)==75 and set(pdd)==set(o.index)
o['pdd']=o.index.map(pdd); o['region']=o.pdd.map(REG)
for y,t in (('2022','22'),('2026','26')):
    o['S'+t]=100*o[f'dem_{y}']/o[f'ballots_{y}']
    o['P'+t]=100*o[f'prim_demsen_{y}']/o[f'prim_ballots_{y}']
    o['G'+t]=o['S'+t]-o['P'+t]
    o['P2p'+t]=100*o[f'prim_demsen_{y}']/(o[f'prim_demsen_{y}']+o[f'prim_repsen_{y}'])   # sensitivity: two-party Senate-primary share
o['dS']=o.S26-o.S22; o['dP']=o.P26-o.P22; o['dG']=o.G26-o.G22
o['loss']=o.prim_demsen_2026<o.prim_demsen_2022
o['residual']=np.where(o.loss,o.dG-o.dP.abs(),np.nan)
o['implied_extra_votes']=o.dem_2026-o.S22/100*o.ballots_2026
o['gap_primary_scaled']=o.dem_2026-o.dem_2022*(o.prim_demsen_2026/o.prim_demsen_2022)
def fit(y,x,w=None):
    X=sm.add_constant(np.asarray(x,float)/100); r=(sm.WLS(np.asarray(y,float),X,weights=w) if w is not None else sm.OLS(np.asarray(y,float),X)).fit()
    res=np.asarray(y)-r.fittedvalues; ci=r.conf_int()
    return dict(n=int(len(y)),m=float(r.params[1]),m_se=float(r.bse[1]),m_ci=[float(ci[1,0]),float(ci[1,1])],b=float(r.params[0]),b_se=float(r.bse[0]),b_ci=[float(ci[0,0]),float(ci[0,1])],
        r2=float(r.rsquared),resid_se=float(np.sqrt(np.sum(res**2)/(len(y)-2))),rms=float(np.sqrt(np.mean(res**2))),
        within1=float(np.mean(np.abs(res)<=1)),within2=float(np.mean(np.abs(res)<=2)),within3=float(np.mean(np.abs(res)<=3)),med_abs=float(np.median(np.abs(res)))),r
F={}
F['2022'],r22=fit(o.G22,o.P22); F['2026'],r26=fit(o.G26,o.P26)
F['2022_wtd'],_=fit(o.G22,o.P22,o.ballots_2022); F['2026_wtd'],_=fit(o.G26,o.P26,o.ballots_2026)
F['pooled'],_=fit(np.r_[o.G22,o.G26],np.r_[o.P22,o.P26])
o['fit22']=np.asarray(r22.fittedvalues); o['res22']=o.G22-o.fit22; o['fit26']=np.asarray(r26.fittedvalues); o['res26']=o.G26-o.fit26
L=pd.DataFrame(dict(G=np.r_[o.G22,o.G26],P=np.r_[o.P22,o.P26]/100,yr=np.r_[np.zeros(75),np.ones(75)]))
ri=smf.ols('G~P*yr',L).fit(); F['year_interaction']=dict(d_intercept=float(ri.params['yr']),p_d_intercept=float(ri.pvalues['yr']),d_slope=float(ri.params['P:yr']),p_d_slope=float(ri.pvalues['P:yr']))
F['dG_on_dP'],rd=fit(o.dG,o.dP)
# sensitivity: SC-style two-party Senate-primary share
SENS={}
for t in ('22','26'):
    g=o['S'+t]-o['P2p'+t]; SENS[t],_=fit(g,o['P2p'+t])
SENS['dG_two_party']=dict(median=float(((o.S26-o.P2p26)-(o.S22-o.P2p22)).median()),corr_with_main_dG=float(np.corrcoef((o.S26-o.P2p26)-(o.S22-o.P2p22),o.dG)[0,1]))
NAR={}
for t,rr in (('22',r22),('26',r26)):
    inf=rr.get_influence(); NAR[t]=pd.DataFrame(dict(cooks=inf.cooks_distance[0],stud=inf.resid_studentized_external,lev=inf.hat_matrix_diag),index=o.index)
n=75; flag=sorted(set(NAR['22'].index[(NAR['22'].cooks>4/n)|(NAR['22'].stud.abs()>2.5)])|set(NAR['26'].index[(NAR['26'].cooks>4/n)|(NAR['26'].stud.abs()>2.5)]))
k=o.drop(flag); F['2022_narrowed'],_=fit(k.G22,k.P22); F['2026_narrowed'],_=fit(k.G26,k.P26)
NARROW=dict(rule=f"Cook's distance > 4/n ({4/n:.3f}) or absolute externally studentized residual > 2.5, in either year's fit",counties=flag,
  detail={c_:dict(cooks22=float(NAR['22'].loc[c_,'cooks']),stud22=float(NAR['22'].loc[c_,'stud']),cooks26=float(NAR['26'].loc[c_,'cooks']),stud26=float(NAR['26'].loc[c_,'stud']),
          P22=float(o.loc[c_,'P22']),G22=float(o.loc[c_,'G22']),P26=float(o.loc[c_,'P26']),G26=float(o.loc[c_,'G26'])) for c_ in flag})
RG={}
for t in ('22','26'):
    d=pd.DataFrame(dict(G=o['G'+t],P=o['P'+t]/100,region=o.region))
    base=smf.ols('G~P',d).fit(); inter=smf.ols('G~P+C(region)',d).fit(); full=smf.ols('G~P*C(region)',d).fit()
    a1=sm.stats.anova_lm(base,inter); a2=sm.stats.anova_lm(base,full)
    per={}
    for g_,dd in d.groupby('region'):
        rr_=smf.ols('G~P',dd).fit(); per[g_]=dict(n=int(len(dd)),m=float(rr_.params['P']),b=float(rr_.params['Intercept']),r2=float(rr_.rsquared),m_se=float(rr_.bse['P']),counties=list(dd.index))
    dn=d.drop(flag); bn=smf.ols('G~P',dn).fit(); fn=smf.ols('G~P*C(region)',dn).fit(); an=sm.stats.anova_lm(bn,fn)
    RG[t]=dict(F_intercepts=float(a1.F[1]),p_intercepts=float(a1['Pr(>F)'][1]),F_full=float(a2.F[1]),p_full=float(a2['Pr(>F)'][1]),r2_single=float(base.rsquared),r2_full=float(full.rsquared),
               p_full_narrowed=float(an['Pr(>F)'][1]),per_region=per)
dgr=o.groupby('region').dG.agg(['count','mean','median','min','max']); kw=stats.kruskal(*[g_.dG.values for _,g_ in o.groupby('region')])
RG['dG_by_region']=dgr.round(3).to_dict(orient='index'); RG['dG_kruskal']=dict(H=float(kw.statistic),p=float(kw.pvalue))
FLOOR=o.sort_values('P22').head(5); CEIL=o.sort_values('dG',ascending=False).head(5)
lr=stats.linregress(np.log10(o.pop2025),o.dG); lrp=stats.linregress(np.log10(o.pop2025),o.dP); lrs=stats.linregress(np.log10(o.pop2025),o.dS)
K=dict(floor_rule='five lowest 2022 proxy shares P2022 (most Republican primary baseline)',floor=FLOOR.index.tolist(),ceiling_rule='five largest ΔG',ceiling=CEIL.index.tolist(),
  floor_by_dG=o.dG.idxmin(),ceiling_by_dG=o.dG.idxmax(),lowest5_dG=o.sort_values('dG').head(5).index.tolist(),
  mean_dG=float(o.dG.mean()),median_dG=float(o.dG.median()),sd_dG=float(o.dG.std()),sd_dS=float(o.dS.std()),n_pos=int((o.dG>0).sum()),n_neg=int((o.dG<0).sum()),
  n_loss=int(o.loss.sum()),loss_counties=o.index[o.loss].tolist(),n_P_fell=int((o.dP<0).sum()),n_S_rose=int((o.dS>0).sum()),n_S_fell=int((o.dS<0).sum()),
  size_slope=dict(slope=float(lr.slope),r=float(lr.rvalue),p=float(lr.pvalue)),size_dP=dict(r=float(lrp.rvalue),p=float(lrp.pvalue)),size_dS=dict(r=float(lrs.rvalue),p=float(lrs.pvalue)),
  median_residual=float(np.nanmedian(o.residual)) if o.loss.any() else None)
T=o.sum(numeric_only=True)
PO=dict(S22=100*T.dem_2022/T.ballots_2022,S26=100*T.dem_2026/T.ballots_2026,P22=100*T.prim_demsen_2022/T.prim_ballots_2022,P26=100*T.prim_demsen_2026/T.prim_ballots_2026)
PO.update(G22=PO['S22']-PO['P22'],G26=PO['S26']-PO['P26']); PO['dG']=PO['G26']-PO['G22']; PO['dP']=PO['P26']-PO['P22']; PO['dS']=PO['S26']-PO['S22']
PO['implied_extra_pooled']=(PO['S26']-PO['S22'])/100*T.ballots_2026; PO['implied_extra_sum']=float(o.implied_extra_votes.sum())
PO['totals']={k_:int(T[k_]) for k_ in USED}
s=max(-PO['dP'],0)/100; N=T.ballots_2026; p=PO['S26']/100
PO['offset']={f'cushion_{cu}':dict(switched=float((s+cu/100)*N),added=float((s+cu/100)*N/(1-p+s+cu/100))) for cu in (0,1,2)} if s>0 else 'proxy share did not fall statewide; no offset need'
TX={}
for y in ('2022','2026'):
    TX[y]=dict(DR_gt_ballots=o.index[o[f'dem_{y}']+o[f'rep_{y}']>o[f'ballots_{y}']].tolist(),
               gov_gt_ballots=o.index[o[f'govtotal_{y}']>o[f'ballots_{y}']].tolist(),
               ballots_gt_reg=o.index[o[f'ballots_{y}']>o[f'reg_{y}']].tolist(),
               govtotal_gt_reg=o.index[o[f'govtotal_{y}']>o[f'reg_{y}']].tolist(),
               primary_DR_senate_gt_primary_ballots=o.index[o[f'prim_demsen_{y}']+o[f'prim_repsen_{y}']>o[f'prim_ballots_{y}']].tolist(),
               min_margin_ballots_minus_gov=dict(county=(o[f'ballots_{y}']-o[f'govtotal_{y}']).idxmin(),votes=int((o[f'ballots_{y}']-o[f'govtotal_{y}']).min())),
               min_margin_ballots_minus_DR=dict(county=(o[f'ballots_{y}']-o[f'dem_{y}']-o[f'rep_{y}']).idxmin(),votes=int((o[f'ballots_{y}']-o[f'dem_{y}']-o[f'rep_{y}']).min())),
               nogov_pct_median=float((100*(o[f'ballots_{y}']-o[f'govtotal_{y}'])/o[f'ballots_{y}']).median()),
               nogov_pct_range=[float((100*(o[f'ballots_{y}']-o[f'govtotal_{y}'])/o[f'ballots_{y}']).min()),float((100*(o[f'ballots_{y}']-o[f'govtotal_{y}'])/o[f'ballots_{y}']).max())])
# raw-file anomaly: the same checks run on PASS A (bulk FullDataFile)
TX['bulk_file_passA']={y:dict(gov_gt_ballots=A.index[A[f'govtotal_{y}']>A[f'ballots_{y}']].tolist(),
    primary_DR_senate_gt_primary_ballots=A.index[A[f'prim_demsen_{y}']+A[f'prim_repsen_{y}']>A[f'prim_ballots_{y}']].tolist(),
    detail={c_:dict(govtotal=int(A.loc[c_,f'govtotal_{y}']),ballots=int(A.loc[c_,f'ballots_{y}']),prim_DR_senate=int(A.loc[c_,f'prim_demsen_{y}']+A.loc[c_,f'prim_repsen_{y}']),prim_ballots=int(A.loc[c_,f'prim_ballots_{y}'])) for c_ in A.index if A.loc[c_,f'govtotal_{y}']>A.loc[c_,f'ballots_{y}'] or A.loc[c_,f'prim_demsen_{y}']+A.loc[c_,f'prim_repsen_{y}']>A.loc[c_,f'prim_ballots_{y}']}) for y in ('2022','2026')}
o['flag']=''
for c_ in FLOOR.index: o.loc[c_,'flag']='floor'
for c_ in CEIL.index: o.loc[c_,'flag']=(o.loc[c_,'flag']+'; ' if o.loc[c_,'flag'] else '')+'ceiling'
for c_ in flag: o.loc[c_,'flag']=(o.loc[c_,'flag']+'; ' if o.loc[c_,'flag'] else '')+'narrowed-out'
for t_,y_ in (('22','2022'),('26','2026')):
    F[y_+'_share'],rs_=fit(o['S'+t_],o['P'+t_]); e_=o['S'+t_]-np.asarray(rs_.fittedvalues)
    F[y_+'_share'].update(mean_abs=float(np.mean(np.abs(e_))),max_abs=float(np.max(np.abs(e_))),max_county=str(e_.abs().idxmax()),max_signed=float(e_[e_.abs().idxmax()]),rmse=float(np.sqrt(np.mean(e_**2))),
        identity_max_diff_vs_gap_residuals=float(np.max(np.abs(e_-o['res'+t_]))))
    o['Sfit'+t_]=np.asarray(rs_.fittedvalues); o['Sres'+t_]=e_
o.to_pickle('/tmp/ar_o.pkl')
cols=['pop2025','pop2020base','region','pdd','flag','reg_2022','ballots_2022','dem_2022','rep_2022','other_2022','govtotal_2022','prim_ballots_2022','prim_demsen_2022','prim_repsen_2022','S22','P22','G22',
      'reg_2026','ballots_2026','dem_2026','rep_2026','other_2026','govtotal_2026','prim_ballots_2026','prim_demsen_2026','prim_repsen_2026','S26','P26','G26','dS','dP','dG','loss','residual','implied_extra_votes','gap_primary_scaled','fit22','res22','fit26','res26','P2p22','P2p26']
out=o[cols].copy(); out.insert(0,'proxy_label','PROXY: Democratic primary-ballot share (Dem U.S. Senate primary votes / total primary ballots), not party registration (Arkansas has no party registration)')
out.insert(1,'status_2026','2026 general UNOFFICIAL: not yet certified statewide; Arkansas SOS results feed version v234, last updated 2026-11-19 10:36 CST')
out.round(6).to_csv(O+'data/AR_Governor_2022_2026_DeltaG_by_County.csv')
J=dict(fits=F,sensitivity_two_party_senate_primary=SENS,narrow=NARROW,regions=RG,K=K,pooled=PO,overballot=TX,adjudicated_figures_used=ADJ_USED)
json.dump(J,open(O+'data/AR_results_summary.json','w'),indent=1,default=lambda x: x.item() if hasattr(x,'item') else str(x))
print(json.dumps(dict(fits={k:F[k] for k in ('2022','2026','dG_on_dP','2022_narrowed','2026_narrowed')},K=K,PO={k:v for k,v in PO.items() if k!='totals'},TX=TX,narrow=flag,RG={t:{k:v for k,v in RG[t].items() if k!='per_region'} for t in ('22','26')},sens=SENS),indent=0,default=str))
