"""Share-form check, independent of the pipeline: S = m*(D/100) + b per year, all 75 counties, from raw/ only (scripts/raw_sources.py).
S = Dem governor votes / total ballots x 100. D = Dem U.S. Senate primary votes / total primary ballots x 100 (stand-in; Arkansas has no party registration).
White and Conway 2022 use the API county values (match White County's certified totals); the bulk-file values are reported alongside."""
import sys, json, re, numpy as np
sys.path.insert(0,'/workspace/arkansas-elections/scripts'); import raw_sources as RS
A,B,NAMES=RS.A,RS.B,RS.NAMES
W='/workspace/arkansas-elections/'
F=sorted(NAMES)
def SD(S_,y): return (np.array([100*S_[f'dem_{y}'][f]/S_[f'ballots_{y}'][f] for f in F]), np.array([100*S_[f'dsen_{y}'][f]/S_[f'pballots_{y}'][f] for f in F]))
# locked constants as printed on the page (gap form G = m*(P/100)+b)
pg=open(W+'wiki/Locked-Arkansas-Formula.md').read()
lock={}
for y in ('2022','2026'):
    m=re.search(rf'\| {y}, all counties[^|]*\| 75 \| ([−\-+]?[\d.]+) \(([\d.]+)\) \| ([−\-+]?[\d.]+) \(([\d.]+)\) \| ([\d.]+) \|',pg)
    lock[y]=dict(m=float(m.group(1).replace('−','-')),b=float(m.group(3).replace('−','-').replace('+','')))
out=dict(locked_gap_form=lock,years={})
for y in ('2022','2026'):
    S,D=SD(A,y); Sb,Db=SD(B,y); x=D/100
    diff=[(NAMES[f],round(Sb[i],4),round(S[i],4),round(Db[i],4),round(D[i],4)) for i,f in enumerate(F) if abs(Sb[i]-S[i])>1e-12 or abs(Db[i]-D[i])>1e-12]
    def stats(pred):
        r=S-pred; return dict(mean_abs=float(np.mean(abs(r))),max_abs=float(np.max(abs(r))),max_county=NAMES[F[int(np.argmax(abs(r)))]],max_signed=float(r[int(np.argmax(abs(r)))]),rmse=float(np.sqrt(np.mean(r**2))))
    L=lock[y]
    lit=stats(L['m']*x+L['b'])                       # locked constants read literally as the share form
    conv=stats((L['m']+100)*x+L['b'])                # gap-form constants converted: S = (m+100)*(D/100) + b
    X=np.c_[np.ones(75),x]; beta,*_=np.linalg.lstsq(X,S,rcond=None); e=S-X@beta; s2=e@e/73; se=np.sqrt(np.diag(s2*np.linalg.inv(X.T@X)))
    r2=1-e@e/((S-S.mean())@(S-S.mean())); fit=stats(X@beta)
    # gap-form refit from raw, for the identity check against the charts (G residuals == S residuals)
    G=S-D; bg,*_=np.linalg.lstsq(X,G,rcond=None); eg=G-X@bg
    out['years'][y]=dict(n=75,refit=dict(m=float(beta[1]),b=float(beta[0]),m_se=float(se[1]),b_se=float(se[0]),r2=float(r2),**fit,resid_se=float(np.sqrt(s2))),
        locked_literal_as_share=lit,locked_converted_to_share=dict(m=L['m']+100,b=L['b'],**conv),
        gap_refit=dict(m=float(bg[1]),b=float(bg[0])),max_abs_diff_gap_vs_share_residuals=float(np.max(abs(eg-e))),
        bulk_vs_api_differences=diff,
        per_county={NAMES[f]:dict(S=float(S[i]),D=float(D[i]),pred=float((X@beta)[i]),resid=float(e[i])) for i,f in enumerate(F)})
json.dump(out,open(W+'verification/share_form_check.json','w'),indent=1)
for y,v in out['years'].items():
    print(y,'REFIT',{k:round(v['refit'][k],4) for k in ('m','m_se','b','b_se','r2','mean_abs','max_abs','rmse')},v['refit']['max_county'])
    print('   locked literal',{k:round(v['locked_literal_as_share'][k],3) for k in ('mean_abs','max_abs','rmse')},'| converted',{k:round(v['locked_converted_to_share'][k],3) for k in ('m','b','mean_abs','max_abs','rmse')})
    print('   gap refit',v['gap_refit'],'resid identity diff',v['max_abs_diff_gap_vs_share_residuals'],'bulk/api diffs',v['bulk_vs_api_differences'])
