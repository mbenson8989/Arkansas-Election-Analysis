import pandas as pd, numpy as np, json, re, glob
W='/workspace/arkansas-elections/'; O=W+'repo/'; WK=W+'wiki/'
o=pd.read_pickle('/tmp/ar_o.pkl'); J=json.load(open(O+'data/AR_results_summary.json')); C=json.load(open(W+'verification/compare_report.json'))
A=pd.read_csv(W+'verification/passA_counties.csv',index_col='county')
RAW='https://raw.githubusercontent.com/mbenson8989/Arkansas-Election-Analysis/main/'
REPO='https://github.com/mbenson8989/Arkansas-Election-Analysis'
CEDAR='https://github.com/mbenson8989/Nebraska-Election-Analysis-/wiki/Cedar-Audit'
f=lambda n:f"{int(round(n)):,}"; sgi=lambda n:(f"{int(round(n)):+,}").replace('-','−'); p2=lambda v:f"{v:.2f}"; sg=lambda v:(f"{v:+.2f}").replace('-','−'); pc=lambda v:f"{v:.2f}%"
F=J['fits']; K=J['K']; PO=J['pooled']; RG=J['regions']; NAR=J['narrow']; TX=J['overballot']; SENS=J['sensitivity_two_party_senate_primary']
CEIL=K['ceiling']; FLOOR=K['floor']; LOSS=[c for c in o.index if o.loc[c,'loss']]; NARC=NAR['counties']
T=PO['totals']; N=len(o)
PLABEL="Democratic primary-ballot share (proxy — Arkansas has no party registration)"
BANNER=(f"> **P = {PLABEL}.** **2026 general-election figures are UNOFFICIAL** (not yet certified statewide; Arkansas SOS results feed v234, Nov 19 2026). "
        "Governor race only. These pages measure a pattern; they make no claim about intent, fraud or cause.")
PAGES=[('Home','Home'),('Bottom-Up Reverse Math','Reverse-Math'),('Locked Arkansas Formula','Locked-Arkansas-Formula'),('Floor and Ceiling Counties','Floor-and-Ceiling'),('Graphs','Graphs')]
REL=lambda here:"\n---\n**Related:** "+" · ".join([f"[{t}]({s})" for t,s in PAGES if s!=here]+[f"[Cedar County Audit (Nebraska)]({CEDAR})"])+"\n"
img=lambda fn,cap:f"![{cap}]({RAW}{fn})\n\n*{cap}*\n"
mark=lambda c:('†' if o.loc[c,'loss'] else '')+('‡' if c in('White','Conway') else '')+('§' if c=='Yell' else '')
nA=C['total_comparisons']; mA=C['matched']; mmA=C['mismatched']
ob22=TX['2022']; ob26=TX['2026']; y=o.loc['Yell']
yell_gap=int(y.govtotal_2022-y.ballots_2022); yell_dr=int(y.dem_2022+y.rep_2022-y.ballots_2022)
# -------------------------------------------------- full table
def full_table():
    h=("| County | Region | Population 2025 | Dem Senate primary 2022 | Primary ballots 2022 | P 2022 | Dem gov 2022 | Ballots 2022 | S 2022 | G 2022 | "
       "Dem Senate primary 2026 | Primary ballots 2026 | P 2026 | Dem gov 2026 | Ballots 2026 | S 2026 | G 2026 | ΔG |\n|"+"---|"*18+"\n")
    for c,r in o.iterrows():
        h+=(f"| {c}{mark(c)} | {r.region} | {f(r.pop2025)} | {f(r.prim_demsen_2022)} | {f(r.prim_ballots_2022)} | {p2(r.P22)} | {f(r.dem_2022)} | {f(r.ballots_2022)} | {p2(r.S22)} | {sg(r.G22)} | "
            f"{f(r.prim_demsen_2026)} | {f(r.prim_ballots_2026)} | {p2(r.P26)} | {f(r.dem_2026)} | {f(r.ballots_2026)} | {p2(r.S26)} | {sg(r.G26)} | {sg(r.dG)} |\n")
    return h
top=CEIL[0]; a=o.loc[top]
six=o.head(6)
# ==================================================== HOME
home=f"""# Arkansas 2022 vs 2026 Governor Race: ΔG Method (proxy version)

{BANNER}

Method developed by Morissa Benson (CD3 Vice Chair, Nebraska GOP). It began with her [Cedar County Audit]({CEDAR}) on the [Nebraska Election Analysis wiki](https://github.com/mbenson8989/Nebraska-Election-Analysis-/wiki). That audit is where the ΔG method and the reverse step come from. This wiki applies the same arithmetic to all {N} Arkansas counties. Arkansas publishes no party-registration counts (party choice on the registration form is optional), so the registration share is replaced by a primary-ballot proxy, as in the South Carolina version. Data: Arkansas Secretary of State election results ([arkansas.tally-enr.com](https://arkansas.tally-enr.com/), linked from [sos.arkansas.gov](https://www.sos.arkansas.gov/elections/research/election-results)). Population comes from the U.S. Census Bureau. Compiled Nov 19, 2026. Code and data: [Arkansas-Election-Analysis]({REPO}).

## Contents

1. [Cedar County Audit]({CEDAR}) (Nebraska wiki): where the method started
2. [Home](Home): this page, statewide summary and verification
3. [Bottom-Up Reverse Math](Reverse-Math): {top} → the six largest counties → all {N} counties, then solved backward for implied extra votes
4. [Locked Arkansas Formula](Locked-Arkansas-Formula): the statewide fitted equation, the equation, the proxy, a blank template, and the Arkansas-only constants
5. [Floor and Ceiling Counties](Floor-and-Ceiling): the floor and ceiling counties, regional constants, narrowed-out counties and the over-ballot check
6. [Graphs](Graphs): slope chart, ΔG by population, the ΔS and ΔP components, forward fit, regional fits and the over-ballot check

## Statewide at a glance

| Measure | 2022 | 2026 (UNOFFICIAL general) | Change |
|---|---|---|---|
| Democratic U.S. Senate primary votes | {f(T['prim_demsen_2022'])} | {f(T['prim_demsen_2026'])} | {sgi(T['prim_demsen_2026']-T['prim_demsen_2022'])} |
| Total primary ballots cast (all ballot types) | {f(T['prim_ballots_2022'])} | {f(T['prim_ballots_2026'])} | {sgi(T['prim_ballots_2026']-T['prim_ballots_2022'])} |
| **P**: {PLABEL} | {pc(PO['P22'])} | {pc(PO['P26'])} | {sg(PO['dP'])} pts |
| Democratic governor votes | {f(T['dem_2022'])} | {f(T['dem_2026'])} | {sgi(T['dem_2026']-T['dem_2022'])} |
| Total ballots cast | {f(T['ballots_2022'])} | {f(T['ballots_2026'])} | {sgi(T['ballots_2026']-T['ballots_2022'])} |
| **S**: Dem share of ballots cast | {pc(PO['S22'])} | {pc(PO['S26'])} | {sg(PO['dS'])} pts |
| **G** = S − P | {sg(PO['G22'])} | {sg(PO['G26'])} | ΔG {sg(PO['dG'])} |

Primaries: May 24, 2022 and March 3, 2026 (Arkansas moved its primary to March in 2026). Both primaries are official in the SOS feed.

## County results in brief

- **S rose in {K['n_S_rose']} counties and fell in {K['n_S_fell']}.** County ΔS ranges from {sg(o.dS.min())} ({o.dS.idxmin()}) to {sg(o.dS.max())} ({o.dS.idxmax()}), median {sg(o.dS.median())}.
- **The proxy moved more than S.** P rose in {N-K['n_P_fell']} counties and fell in {K['n_P_fell']}, from {sg(o.dP.min())} ({o.dP.idxmin()}) to {sg(o.dP.max())} ({o.dP.idxmax()}). Democratic Senate-primary votes rose {(T['prim_demsen_2026']/T['prim_demsen_2022']-1)*100:.0f}% statewide while total primary ballots fell {(1-T['prim_ballots_2026']/T['prim_ballots_2022'])*100:.0f}%.
- **ΔG tracks the proxy change.** Across counties, ΔG = {F['dG_on_dP']['m']/100:.3f} × ΔP + {F['dG_on_dP']['b']:.2f} (R² {F['dG_on_dP']['r2']:.2f}). ΔG rose in {K['n_pos']} counties and fell in {K['n_neg']}; county median {sg(K['median_dG'])} (range {sg(o.dG.min())} {o.dG.idxmin()} to {sg(o.dG.max())} {o.dG.idxmax()}).
- **Ceiling counties** (largest ΔG): {', '.join(f"{c} ({sg(o.loc[c,'dG'])})" for c in CEIL)}. **Floor counties** (lowest 2022 proxy share): {', '.join(f"{c} ({p2(o.loc[c,'P22'])}%)" for c in FLOOR)}. See [Floor and Ceiling Counties](Floor-and-Ceiling).
- **Residual step:** {len(LOSS)} counties lost Democratic Senate-primary votes and run the residual step (median residual {sg(K['median_residual'])}). The other {N-len(LOSS)} are non-loss counties: raw numbers only.
- **Solved backward (hypothesis):** implied extra votes sum to {f(PO['implied_extra_sum'])} across {N} counties ({f(PO['implied_extra_pooled'])} on pooled statewide numbers). The proxy share rose statewide, so there is no registration-loss offset to cover.
- **Arkansas-only constants** (G = m × P/100 + b, {N} counties): 2022 m = {sg(F['2022']['m'])}, b = {sg(F['2022']['b'])} (R² {F['2022']['r2']:.2f}); 2026 m = {sg(F['2026']['m'])}, b = {sg(F['2026']['b'])} (R² {F['2026']['r2']:.2f}). See [Locked Arkansas Formula](Locked-Arkansas-Formula).
- **Over-ballot check:** **Yell County, 2022** has {f(y.govtotal_2022)} governor votes against {f(y.ballots_2022)} ballots cast ({f(yell_gap)} more votes than ballots; Democratic + Republican alone exceed ballots by {f(yell_dr)}). No other county is flagged in either year, and no county has ballots or votes above registered voters. 2026: no county flagged (UNOFFICIAL data). Details on [Floor and Ceiling Counties](Floor-and-Ceiling#over-ballot-check).

## Verification: two independent passes over the raw SOS files

- **Pass A** read the bulk `FullDataFile.json` for each of the 4 elections (host results.tally-enr.com) and built county vote totals by summing precinct rows. Turnout came from the same file's county turnout block.
- **Pass B** used separate code on different files: the results API that the SOS site itself calls (host enr-results-api.totalresults.com). County vote totals came from the published county rows of `GetContestResults`; registered voters and ballots came from `GetTurnout`, read with regex.
- **Result:** {f(nA)} figure comparisons ({N} counties × {C['figures_per_county']} figures). **{f(mA)} matched, {mmA} mismatched.** All {f(C['comparisons_2026'])} comparisons for 2026 matched. Every comparison outside two counties matched ({f(C['matched_outside_mismatch_counties'])} of {f(C['comparisons_outside_mismatch_counties'])}).
- **The {mmA} mismatches are all in White and Conway counties, 2022 (general and primary), and all come from the bulk download file.** In that file, White's precinct rows add up to {f(A.loc['White','govtotal_2022'])} governor votes against {f(A.loc['White','ballots_2022'])} ballots in its own turnout block, and Conway's to {f(A.loc['Conway','govtotal_2022'])} against {f(A.loc['Conway','ballots_2022'])}. Both are impossible. Pass B's figures match the White County Election Commission's certified totals (Sanders 18,010, Jones 4,613, Harrington 502) and a third published county table for all {N} counties (Pass B: 0 differences in 300 figures; Pass A: {C['wikipedia_2022_general_check']['disagree_with_passA']}). Pass B's statewide primary sums equal the published statewide totals; Pass A exceeds them by exactly the White + Conway differences. These pages use the Pass B figures, marked ‡ in tables. {len(C['mismatches_in_analysis_figures'])} of the {mmA} mismatches are in figures used in calculations, and all of those are resolved. The other {mmA-len(C['mismatches_in_analysis_figures'])} (2022 governor-primary votes) are not used in any calculation.
- **Data problem in the SOS feed, 2022 Democratic governor primary:** the feed shows James "Rus" Russell with 11 votes; published results give him 6,421. That is why P uses the Democratic **U.S. Senate** primary, whose statewide totals match the published results in both years.

## Read this before using the numbers

- **The proxy is not registration.** It is the share of all primary ballots (Democratic, Republican and nonpartisan) that carried a vote in the Democratic U.S. Senate primary. Contested local primaries pull voters onto one party's ballot. In 2026 a new rule let only Republican or unaffiliated registrants take a Republican ballot, while the Democratic primary stayed open.
- **The ceiling counties are driven by the proxy.** {top}'s Democratic Senate-primary votes fell from {f(a.prim_demsen_2022)} to {f(a.prim_demsen_2026)}, so P fell {p2(-a.dP)} points. Its S rose {p2(a.dS)} points.
- **2026 general figures are UNOFFICIAL** and still changing; the SOS feed was last updated Nov 19, 2026, 10:36 AM CST.
- **A residual is not evidence of altered votes.** Candidate choice, crossover voting, turnout and primary competitiveness all move these numbers.
{REL('Home')}"""
open(WK+'Home.md','w').write(home)
# ==================================================== REVERSE MATH
def row6(c):
    r=o.loc[c]; return (f"| {c}{mark(c)} | {f(r.pop2025)} | {f(r.prim_demsen_2022)} → {f(r.prim_demsen_2026)} | {pc(r.P22)} → {pc(r.P26)} | {f(r.dem_2022)} → {f(r.dem_2026)} | "
                        f"{f(r.ballots_2022)} → {f(r.ballots_2026)} | {sg(r.dS)} | {sg(r.dP)} | {sg(r.dG)} | {sgi(r.implied_extra_votes)} |\n")
def grp(name,d):
    t=d.sum(numeric_only=True); S22=100*t.dem_2022/t.ballots_2022; S26=100*t.dem_2026/t.ballots_2026; P22=100*t.prim_demsen_2022/t.prim_ballots_2022; P26=100*t.prim_demsen_2026/t.prim_ballots_2026
    return (f"| {name} | {len(d)} | {pc(S22)} → {pc(S26)} | {pc(P22)} → {pc(P26)} | {sg(S26-S22)} | {sg(P26-P22)} | {sg((S26-P26)-(S22-P22))} | "
            f"{sg(d.dG.median())} ({sg(d.dG.min())} to {sg(d.dG.max())}) | {sgi(d.implied_extra_votes.sum())} |\n")
rest=o.iloc[6:]
rm=f"""# Bottom-Up Reverse Math

{BANNER}

The same arithmetic at three levels: one county, then the six largest, then the whole state. It is then solved backward for implied extra votes. S = Democratic governor votes ÷ total ballots cast. The method comes from the [Cedar County Audit]({CEDAR}) in Nebraska.

## Step 1: {top} County (the ceiling county)

| Step | Value |
|---|---|
| Democratic share of ballots (S) | {pc(a.S22)} (2022: {f(a.dem_2022)} of {f(a.ballots_2022)}) → {pc(a.S26)} (2026: {f(a.dem_2026)} of {f(a.ballots_2026)}): **{sg(a.dS)} points** |
| Proxy P [{PLABEL}] | {pc(a.P22)} ({f(a.prim_demsen_2022)} of {f(a.prim_ballots_2022)}) → {pc(a.P26)} ({f(a.prim_demsen_2026)} of {f(a.prim_ballots_2026)}): **{sg(a.dP)} points** |
| ΔG = ΔS − ΔP | {p2(a.dS)} − ({sg(a.dP)}) = **{sg(a.dG)} points**, the largest in Arkansas |
| Reverse step: ΔG − proxy-share loss | {p2(a.dG)} − {p2(abs(a.dP))} = **{sg(a.residual)}** (the residual) |
| Implied extra votes | {f(a.dem_2026)} − {pc(a.S22)} × {f(a.ballots_2026)} = **about {sgi(a.implied_extra_votes)}** |
| Primary-scaled gap (Nebraska "gap in votes", for comparison) | {f(a.dem_2026)} − {f(a.dem_2022)} × ({f(a.prim_demsen_2026)} ÷ {f(a.prim_demsen_2022)}) = about {sgi(a.gap_primary_scaled)} |

{top}'s ΔG is large because its proxy share collapsed: Democratic Senate-primary votes fell from {f(a.prim_demsen_2022)} to {f(a.prim_demsen_2026)} while total primary ballots went from {f(a.prim_ballots_2022)} to {f(a.prim_ballots_2026)}. Its residual, {sg(a.residual)}, is close to the state's typical ΔS (median {sg(o.dS.median())}).

## Step 2: the six largest counties

Largest to smallest population.

| County | Population | Dem Senate primary 2022 → 2026 [PROXY] | P 2022 → 2026 [PROXY] | Dem gov votes 2022 → 2026 | Ballots 2022 → 2026 | ΔS (pts) | ΔP (pts) | ΔG (pts) | Implied extra votes |
|---|---|---|---|---|---|---|---|---|---|
{''.join(row6(c) for c in six.index)}
ΔG is negative in {'all' if (six.dG<0).all() else int((six.dG<0).sum())} {'six largest counties' if (six.dG<0).all() else 'of the six largest counties'}. {'None' if not six.loss.any() else ', '.join(c for c in six.index if six.loc[c,'loss'])} of the six lost Democratic Senate-primary votes. Pulaski has the lowest ΔG in the state ({sg(o.loc['Pulaski','dG'])}): its proxy rose {p2(o.loc['Pulaski','dP'])} points while S rose {p2(o.loc['Pulaski','dS'])}.

## Step 3: all {N} counties

| Group | Counties | Dem share of ballots | Proxy P [PROXY] | ΔS | ΔP | Pooled ΔG | County median ΔG (range) | Implied extra votes |
|---|---|---|---|---|---|---|---|---|
{grp('Six largest counties',six)}{grp('Other counties',rest)}{grp('All Arkansas counties',o)}
- ΔG rose in {K['n_pos']} of {N} counties and fell in {K['n_neg']}. The county-level SD of ΔG is {p2(K['sd_dG'])} points, against an SD of ΔS of {p2(K['sd_dS'])}.
- **County size.** Smaller counties have higher ΔG: r = {sg(K['size_slope']['r'])} against log population (p = {K['size_slope']['p']:.5f}). This comes from the proxy: ΔP rises with county size (r = {sg(K['size_dP']['r'])}), while ΔS does not track size (r = {sg(K['size_dS']['r'])}, p = {K['size_dS']['p']:.2f}).

## Residual step: the {len(LOSS)} counties that lost Democratic primary voters

| County | Population | Dem Senate primary 2022 → 2026 [PROXY] | P change | ΔG | Residual = ΔG − \\|ΔP\\| | Implied extra votes |
|---|---|---|---|---|---|---|
{''.join(f"| {c}{mark(c)} | {f(o.loc[c,'pop2025'])} | {f(o.loc[c,'prim_demsen_2022'])} → {f(o.loc[c,'prim_demsen_2026'])} | {sg(o.loc[c,'dP'])} | {sg(o.loc[c,'dG'])} | {sg(o.loc[c,'residual'])} | {sgi(o.loc[c,'implied_extra_votes'])} |"+chr(10) for c in LOSS)}
{sum(1 for c in LOSS if o.loc[c,'dP']>0)} of these counties lost Democratic primary votes but their proxy share still rose (total primary ballots fell faster); the formula subtracts \\|ΔP\\| either way, as in the Cedar audit. The other {N-len(LOSS)} counties are **non-loss counties** and get raw numbers only.

## Solving backward: implied extra votes (hypothesis)

For each county, implied extra votes = 2026 Democratic votes − (2022 Democratic share of ballots × 2026 ballots). The {N} counties sum to {sgi(PO['implied_extra_sum'])}; on pooled statewide numbers it is {sgi(PO['implied_extra_pooled'])}. Largest: {', '.join(f"{c} ({sgi(o.loc[c,'implied_extra_votes'])})" for c in o.implied_extra_votes.sort_values(ascending=False).head(3).index)}. Smallest: {', '.join(f"{c} ({sgi(o.loc[c,'implied_extra_votes'])})" for c in o.implied_extra_votes.sort_values().head(3).index)}.

> **Hypothesis label.** Turning the residual into "implied extra votes" and calling them injected, switched or offset votes is a hypothesis the arithmetic cannot test. The same number reflects candidate appeal, turnout and crossover voting.

## What the arithmetic cannot tell you

- Who cast the ballots, or why S moved.
- Whether a primary-ballot shift reflects party loyalty or one contested local race. {top}'s collapse in Democratic Senate-primary votes is exactly the kind of move a local race can cause.
- Anything certified about 2026: the general-election figures are UNOFFICIAL.

## Full county table ({N} counties, largest to smallest population)

† lost Democratic Senate-primary votes (residual step) · ‡ 2022 figures from Pass B; the SOS bulk file is internally impossible for this county (see [Home](Home)) · § Yell 2022: governor votes exceed ballots cast (over-ballot flag). P = {PLABEL}. 2026 general figures UNOFFICIAL.

{full_table()}{REL('Reverse-Math')}"""
open(WK+'Reverse-Math.md','w').write(rm)
# ==================================================== LOCKED
f22,f26=F['2022'],F['2026']
_d=F['dG_on_dP']; FE=dict(n=_d['n'],b=_d['b'],b_se=_d['b_se'],k=-_d['m']/100,k_se=_d['m_se']/100,r2=_d['r2'])
WX=o.index[0]; WXpred=FE['b']+FE['k']*(o.loc[WX,'P22']-o.loc[WX,'P26'])
json.dump(dict(FE=FE,example=WX,drop=float(o.loc[WX,'P22']-o.loc[WX,'P26']),pred=float(WXpred),actual=float(o.loc[WX,'dG'])),open(W+'verification/fitted_equation.json','w'),indent=1)
def frow(name,d): return f"| {name} | {d['n']} | {sg(d['m'])} ({p2(d['m_se'])}) | {sg(d['b'])} ({p2(d['b_se'])}) | {d['r2']:.3f} | {p2(d['resid_se'])} | {d['within1']*100:.0f}% / {d['within2']*100:.0f}% / {d['within3']*100:.0f}% | {p2(d['med_abs'])} |\n"
lk=f"""# Locked Arkansas Formula

{BANNER}

## Arkansas fitted equation (final)

```
Arkansas equation:  ΔG = {sg(FE['b'])} + {FE['k']:.2f} × (Dem primary-proxy drop, points)
Four decimals:      ΔG = {FE['b']:+.4f} + {FE['k']:.4f} × (Dem primary-proxy drop, points)
```

| Item | Rounded | 4 decimals |
|---|---|---|
| Constant (intercept) | {sg(FE['b'])} | {FE['b']:+.4f} |
| Constant standard error | {p2(FE['b_se'])} | {FE['b_se']:.4f} |
| Multiplier (slope) | {FE['k']:.2f} | {FE['k']:.4f} |
| Multiplier standard error | {p2(FE['k_se'])} | {FE['k_se']:.4f} |
| R² | {FE['r2']:.2f} | {FE['r2']:.4f} |
| n (counties) | {FE['n']} | {FE['n']} |

Fitted by least squares across all {FE['n']} counties (n = {FE['n']}): 2022 to 2026 governor race, ballots-cast denominator, locked gap formula. **Proxy:** Arkansas has no party registration, so the registration share is replaced by P = {PLABEL}: Democratic U.S. Senate primary votes ÷ total primary ballots cast. Primary-proxy drop = P 2022 − P 2026, in points (negative where the proxy rose). 2026 general-election figures are UNOFFICIAL; this line should be re-fitted after certification.

**What it means:** across Arkansas's counties, each 1-point drop in the Democratic primary-proxy share goes with about {FE['k']:.2f} points of ΔG, starting from about {sg(FE['b'])} when the proxy does not change. Where the proxy rose, the drop is negative and ΔG falls by about the same amount. The fit explains about {FE['r2']*100:.0f}% of the county-to-county differences in ΔG. This line describes the county pattern; it does not prove anything.

**Worked example: {WX}** (largest county). P went from {p2(o.loc[WX,'P22'])} to {p2(o.loc[WX,'P26'])}, a primary-proxy drop of {(o.loc[WX,'P22']-o.loc[WX,'P26']):+.4f} points (the proxy rose). Predicted ΔG = {FE['b']:+.4f} + {FE['k']:.4f} × ({(o.loc[WX,'P22']-o.loc[WX,'P26']):+.4f}) = {sg(WXpred)}. Actual ΔG = {sg(o.loc[WX,'dG'])}. Difference from the fitted line (actual − predicted) = {sg(o.loc[WX,'dG']-WXpred)}. This difference is not the line-11 residual in the template below, which is ΔG minus the proxy-share loss and applies only to counties that lost Democratic Senate-primary votes.

## The equation

- **S** (Democratic vote share) = Democratic governor votes ÷ total ballots cast × 100. Ballots cast is the SOS county turnout figure.
- **P** ({PLABEL}) = Democratic U.S. Senate primary votes ÷ total primary ballots cast × 100, from the same year's preferential primary (May 24, 2022; March 3, 2026).
- **G** = S − P
- **ΔG** = G(2026) − G(2022) = (S2026 − S2022) − (P2026 − P2022)
- **Reverse step (residual).** Run it only where Democratic Senate-primary votes fell. Residual = ΔG − \\|P2026 − P2022\\|.
- **Solved backward: implied extra votes** = D2026 − (S2022 ÷ 100) × ballots2026
- **Primary-scaled gap** (the Nebraska wiki's "gap in votes" line, for comparison) = D2026 − D2022 × (DemPrimary2026 ÷ DemPrimary2022)

### Why this proxy

- Arkansas has no meaningful party registration to count: party choice on the registration form is optional, and the SOS publishes no registration totals by party.
- The SOS files give one ballots-cast figure per county for the whole primary (Democratic, Republican and nonpartisan judicial ballots together). They do not give ballots by party. The denominator is that total, so P is the Democratic share of **all** primary ballots.
- The numerator needs a Democratic contest that is statewide and contested in both years. The governor primary fails: the 2026 Republican governor primary was not on the ballot (Sanders was unopposed), and the SOS feed's 2022 Democratic governor primary is missing almost all of James "Rus" Russell's 6,421 votes. The Democratic U.S. Senate primary was contested statewide in both years (2022: James, Whitfield, Foster; 2026: Shoffner, Dunbar), and its statewide totals in the feed match the published results exactly ({f(T['prim_demsen_2022'])} and {f(T['prim_demsen_2026'])}).
- Senate-primary votes undercount Democratic ballots by the Democratic voters who skipped that race.
- Sensitivity: using the two-party Senate-primary share (Dem ÷ (Dem + Rep), South Carolina style) instead gives county ΔG values that correlate {SENS['dG_two_party']['corr_with_main_dG']:.3f} with the main ones.

## Blank template

| Line | Item | 2022 | 2026 |
|---|---|---|---|
| 1 | Democratic governor votes | ______ | ______ |
| 2 | Total ballots cast (SOS county turnout) | ______ | ______ |
| 3 | S = line 1 ÷ line 2 × 100 | ______ | ______ |
| 4 | Democratic U.S. Senate primary votes **[PROXY]** | ______ | ______ |
| 5 | Total primary ballots cast **[PROXY]** | ______ | ______ |
| 6 | P = line 4 ÷ line 5 × 100 **[PROXY: not party registration]** | ______ | ______ |
| 7 | G = line 3 − line 6 | ______ | ______ |
| 8 | ΔG = G 2026 − G 2022 | | ______ |
| 9 | Proxy-share change = P 2026 − P 2022 | | ______ |
| 10 | Did Democratic Senate-primary votes fall? (line 4: 2026 < 2022) | | Yes / No |
| 11 | If yes: residual = line 8 − \\|line 9\\| | | ______ |
| 12 | Implied extra votes = line 1 (2026) − line 3 (2022) ÷ 100 × line 2 (2026) | | ______ |
| 13 | Primary-scaled gap = line 1 (2026) − line 1 (2022) × (line 4 2026 ÷ line 4 2022) | | ______ |
| 14 | Fitted G for this county = m × (line 6 ÷ 100) + b, Arkansas constants for that year | ______ | ______ |
| 15 | Distance from the Arkansas line = line 7 − line 14 | ______ | ______ |

## Worked example: {top} (ceiling county, lost Democratic primary voters)

| Line | Item | 2022 | 2026 |
|---|---|---|---|
| 1 | Democratic governor votes | {f(a.dem_2022)} | {f(a.dem_2026)} |
| 2 | Total ballots cast | {f(a.ballots_2022)} | {f(a.ballots_2026)} |
| 3 | S | {p2(a.S22)} | {p2(a.S26)} |
| 4 | Democratic U.S. Senate primary votes [PROXY] | {f(a.prim_demsen_2022)} | {f(a.prim_demsen_2026)} |
| 5 | Total primary ballots [PROXY] | {f(a.prim_ballots_2022)} | {f(a.prim_ballots_2026)} |
| 6 | P [PROXY] | {p2(a.P22)} | {p2(a.P26)} |
| 7 | G | {sg(a.G22)} | {sg(a.G26)} |
| 8 | ΔG | | {sg(a.dG)} |
| 9 | Proxy-share change | | {sg(a.dP)} |
| 10 | Primary votes fell? | | Yes ({f(a.prim_demsen_2022)} → {f(a.prim_demsen_2026)}) |
| 11 | Residual | | {sg(a.residual)} |
| 12 | Implied extra votes | | {sgi(a.implied_extra_votes)} |
| 13 | Primary-scaled gap | | {sgi(a.gap_primary_scaled)} |
| 14 | Fitted G | {sg(a.fit22)} | {sg(a.fit26)} |
| 15 | Distance from the Arkansas line | {sg(a.res22)} | {sg(a.res26)} |

## Arkansas-only constants (forward fit)

The forward surplus equation is fit by least squares across all {N} Arkansas counties, each county weighted equally: **G = m × (P ÷ 100) + b**. It uses Arkansas data only. No other state's constant is reused.

| Fit | n | m (SE) | b (SE) | R² | Residual SE | Within ±1 / ±2 / ±3 pts | Median abs. residual |
|---|---|---|---|---|---|---|---|
{frow('2022, all counties',f22)}{frow('2026, all counties (UNOFFICIAL)',f26)}{frow('2022, narrowed',F['2022_narrowed'])}{frow('2026, narrowed',F['2026_narrowed'])}{frow('2022, ballot-weighted',F['2022_wtd'])}{frow('2026, ballot-weighted',F['2026_wtd'])}{frow('2022 + 2026 pooled',F['pooled'])}
**The locked Arkansas constants are the all-county fits: 2022 m = {sg(f22['m'])}, b = {sg(f22['b'])}; 2026 m = {sg(f26['m'])}, b = {sg(f26['b'])}.** The 2026 constant is built on UNOFFICIAL general-election figures and should be re-locked after certification. Narrowed fits leave out {', '.join(NARC)} (see [Floor and Ceiling Counties](Floor-and-Ceiling#counties-narrowed-out-of-the-fit)).

- **The 2022 and 2026 lines are almost the same.** In a pooled model with year terms, the slope changes by {sg(F['year_interaction']['d_slope'])} (p = {F['year_interaction']['p_d_slope']:.2f}) and the intercept by {sg(F['year_interaction']['d_intercept'])} (p = {F['year_interaction']['p_d_intercept']:.2f}).
- **What m means.** G already contains −P, so m = −100 would mean S does not move with P at all. Arkansas's m of {p2(f22['m'])} (2022) and {p2(f26['m'])} (2026) means S rises roughly {1+f22['m']/100:.2f} to {1+f26['m']/100:.2f} points for each point of proxy share. It is not an "injection multiplier."
- **Reverse-factoring constant across counties.** Regressing ΔG on ΔP gives ΔG = {F['dG_on_dP']['m']/100:.3f} × ΔP + {F['dG_on_dP']['b']:.2f} (SE of intercept {p2(F['dG_on_dP']['b_se'])}; R² {F['dG_on_dP']['r2']:.3f}; residual SE {p2(F['dG_on_dP']['resid_se'])}). A slope close to −1 means ΔG moves almost point for point, in the opposite direction, with ΔP. The intercept, **{sg(F['dG_on_dP']['b'])} points**, is the typical county rise in S once the proxy change is removed.

## Rules for using this formula

1. **Always label P as a proxy.** Arkansas has no party registration. Every table and chart that uses P must say so.
2. **If a county lost Democratic Senate-primary voters, run the residual step.** In Arkansas that is {len(LOSS)} counties. The other {N-len(LOSS)} are **non-loss counties** and get raw numbers only.
3. **The starting point is different in every state.** Arkansas's constants come from Arkansas's own counties. Its P is a primary share, so its G values aren't comparable with states that have real party registration.
4. **Always pull out the ceiling and floor counties.** In Arkansas the ceiling county is {top} ({sg(a.dG)}), and the lowest ΔG is {K['floor_by_dG']} ({sg(o.loc[K['floor_by_dG'],'dG'])}). The floor (most Republican baseline) is {', '.join(FLOOR)}. See [Floor and Ceiling Counties](Floor-and-Ceiling).
5. **Re-run after certification.** The 2026 general figures are UNOFFICIAL.

**Terms used in this wiki** (full definitions on [Floor and Ceiling Counties](Floor-and-Ceiling#terminology)):
- **Ceiling counties**: the five largest ΔG ({', '.join(CEIL)}).
- **Floor counties**: the most Republican baseline, the five lowest 2022 proxy shares ({', '.join(FLOOR)}).
- **Non-loss counties**: no drop in Democratic Senate-primary votes ({N-len(LOSS)} counties). Raw numbers only.
- **Narrowed-out counties**: counties that distort the fit ({', '.join(NARC)}).
{REL('Locked-Arkansas-Formula')}"""
open(WK+'Locked-Arkansas-Formula.md','w').write(lk)
# ==================================================== FLOOR AND CEILING
def crow(c):
    r=o.loc[c]; return f"| {c}{mark(c)} | {r.region} | {f(r.pop2025)} | {pc(r.P22)} → {pc(r.P26)} | {pc(r.S22)} → {pc(r.S26)} | {sg(r.dP)} | {sg(r.dS)} | {sg(r.dG)} | {'Yes' if r.loss else 'No'} |\n"
REGS=['Northwest','Central','Northeast','South']
RGN={'Northwest':'Northwest + Western','Central':'Central + West Central','Northeast':'White River + East','South':'Southwest + Southeast'}
def rrow(t,g):
    p=RG[t]['per_region'][g]; return f"| {g} | 20{t} | {p['n']} | {sg(p['m'])} | {sg(p['b'])} | {p['r2']:.2f} |\n"
dgr=RG['dG_by_region']
fc=f"""# Floor and Ceiling Counties

{BANNER}

## How to read floor and ceiling counties

- **Ceiling counties** have the five largest ΔG. {'All five' if all(o.loc[c,'loss'] for c in CEIL) else str(sum(o.loc[c,'loss'] for c in CEIL))+' of the five'} lost Democratic Senate-primary votes, so their ΔG is mostly a fall in the proxy, not a rise in S.
- **Floor counties** have the most Republican baseline: the five lowest 2022 proxy shares.
- The lowest ΔG in the state is {K['floor_by_dG']} ({sg(o.loc[K['floor_by_dG'],'dG'])}), where the proxy rose sharply.

## Terminology

- **Ceiling counties**: the five largest ΔG: {', '.join(CEIL)}.
- **Floor counties**: the five lowest 2022 proxy shares P: {', '.join(FLOOR)}.
- **Non-loss counties**: no drop in Democratic Senate-primary votes from 2022 to 2026 ({N-len(LOSS)} counties). Raw numbers only.
- **Loss counties**: Democratic Senate-primary votes fell ({len(LOSS)} counties). These run the residual step.
- **Narrowed-out counties**: counties left out of the narrowed fit because they distort it ({', '.join(NARC)}).

## Ceiling and floor detail

**Ceiling counties (largest ΔG)**

| County | Region | Population | P 2022 → 2026 [PROXY] | S 2022 → 2026 | ΔP | ΔS | ΔG | Lost Dem primary votes? |
|---|---|---|---|---|---|---|---|---|
{''.join(crow(c) for c in CEIL)}
**Floor counties (lowest 2022 proxy share)**

| County | Region | Population | P 2022 → 2026 [PROXY] | S 2022 → 2026 | ΔP | ΔS | ΔG | Lost Dem primary votes? |
|---|---|---|---|---|---|---|---|---|
{''.join(crow(c) for c in FLOOR)}
**Lowest five ΔG**: {', '.join(f"{c} ({sg(o.loc[c,'dG'])})" for c in K['lowest5_dG'])}.

## Regional constants

Regions group Arkansas's eight planning and development districts (Ark. Code § 14-166-202) into four: {', '.join(f"{g} ({RGN[g]})" for g in REGS)}.

| Region | Year | n | m | b | R² |
|---|---|---|---|---|---|
{''.join(rrow(t,g) for t in ('22','26') for g in REGS)}
- **2022:** separate regional lines fit better than one statewide line (p = {RG['22']['p_full']:.7f}; {RG['22']['p_full_narrowed']:.4f} after narrowing).
- **2026:** p = {RG['26']['p_full']:.4f} with all counties, {RG['26']['p_full_narrowed']:.2f} after narrowing: the regional difference rests on the narrowed-out counties.
- **ΔG by region (median):** {', '.join(f"{g} {sg(dgr[g]['median'])}" for g in REGS)}. Kruskal-Wallis p = {RG['dG_kruskal']['p']:.2f}: no clear regional difference in ΔG.

## Counties narrowed out of the fit

Rule: {NAR['rule']}.

| County | Cook's D 2022 | Studentized 2022 | Cook's D 2026 | Studentized 2026 | P 2022 | G 2022 | P 2026 | G 2026 |
|---|---|---|---|---|---|---|---|---|
{''.join(f"| {c} | {d['cooks22']:.3f} | {sg(d['stud22'])} | {d['cooks26']:.3f} | {sg(d['stud26'])} | {p2(d['P22'])} | {sg(d['G22'])} | {p2(d['P26'])} | {sg(d['G26'])} |"+chr(10) for c,d in NAR['detail'].items())}
## Over-ballot check

Checks in each year: total governor votes > ballots cast; Democratic + Republican governor votes > ballots cast; ballots cast > registered voters; governor votes > registered voters; Democratic + Republican Senate-primary votes > primary ballots.

| Check | 2022 | 2026 (UNOFFICIAL) |
|---|---|---|
| Governor votes > ballots cast | {', '.join(ob22['gov_gt_ballots']) or 'none'} | {', '.join(ob26['gov_gt_ballots']) or 'none'} |
| Dem + Rep governor votes > ballots cast | {', '.join(ob22['DR_gt_ballots']) or 'none'} | {', '.join(ob26['DR_gt_ballots']) or 'none'} |
| Ballots cast > registered voters | {', '.join(ob22['ballots_gt_reg']) or 'none'} | {', '.join(ob26['ballots_gt_reg']) or 'none'} |
| Governor votes > registered voters | {', '.join(ob22['govtotal_gt_reg']) or 'none'} | {', '.join(ob26['govtotal_gt_reg']) or 'none'} |
| Dem + Rep Senate-primary votes > primary ballots | {', '.join(ob22['primary_DR_senate_gt_primary_ballots']) or 'none'} | {', '.join(ob26['primary_DR_senate_gt_primary_ballots']) or 'none'} |
| Closest margin, ballots − governor votes | {ob22['min_margin_ballots_minus_gov']['county']} ({sgi(ob22['min_margin_ballots_minus_gov']['votes'])}) | {ob26['min_margin_ballots_minus_gov']['county']} ({sgi(ob26['min_margin_ballots_minus_gov']['votes'])}) |

- **Yell County, 2022 (flag):** {f(y.govtotal_2022)} governor votes ({f(y.rep_2022)} Sanders, {f(y.dem_2022)} Jones, {f(y.other_2022)} Harrington) against {f(y.ballots_2022)} ballots cast and {f(y.reg_2022)} registered voters. Both passes and the published county table show the same vote counts. Every other statewide race in Yell also has more votes than {f(y.ballots_2022)}, so the published ballots-cast figure looks too low rather than one race too high. Yell's 2022 S ({pc(y.S22)}) is computed on that ballots figure.
- **SOS bulk file (Pass A), 2022:** White and Conway precinct rows also exceed their own ballots cast (see [Home](Home)). These are file errors; the certified county totals do not exceed ballots.

## Data sources

| Data | Source | Link |
|---|---|---|
| 2022 general (election 1844) | Arkansas SOS results system | https://arkansas.tally-enr.com/#election=1844 |
| 2022 preferential primary, May 24 (election 1843) | Arkansas SOS results system | https://arkansas.tally-enr.com/#election=1843 |
| 2026 general, Nov 3 (UNOFFICIAL; feed v234) | Arkansas SOS results system | https://arkansas.tally-enr.com/#election=11b07106-031e-4d7c-911a-d01fb473d6dd |
| 2026 preferential primary, Mar 3 (feed v3318, official) | Arkansas SOS results system | https://arkansas.tally-enr.com/#election=7f77a178-af02-40ec-92db-c5cc50882c68 |
| Pass A bulk files | FullDataFile.json per election | https://results.tally-enr.com/results/arkansas/1844/FullDataFile.json (same pattern for each election) |
| Pass B API files | GetContestResults, GetTurnout, GetElectionInfo, GetContestSearchList | https://enr-results-api.totalresults.com/Turnout/GetTurnout?cId=arkansas&electionID=1844 (same pattern) |
| Election list | Arkansas SOS election results page | https://www.sos.arkansas.gov/elections/research/election-results |
| White County certified 2022 totals (check) | White County Citizen, Nov 18, 2022 | https://www.whitecountycitizen.com/official-general-election-results-for-white-county/article_f6723bd8-8f0f-5a19-979e-da6c15e93f2e.html |
| Third county table and statewide primary totals (check) | Wikipedia 2022 and 2026 governor and U.S. Senate election articles | https://en.wikipedia.org/wiki/2022_Arkansas_gubernatorial_election |
| Party choice optional | EAC NVRA state instructions, Arkansas | https://www.eac.gov/nvra-instructions-arkansas-english |
| County population, July 1, 2025 (sort order only) | U.S. Census Bureau Vintage 2025 estimates | https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/counties/totals/co-est2025-alldata.csv |
| Regions | Ark. Code § 14-166-202 planning and development districts | https://law.justia.com/codes/arkansas/title-14/subtitle-10/chapter-166/subchapter-2/section-14-166-202/ |
{REL('Floor-and-Ceiling')}"""
open(WK+'Floor-and-Ceiling.md','w').write(fc)
# ==================================================== GRAPHS
CH=[('Slope chart: G, 2022 → 2026','AR_Slope_G2022_to_G2026.png','County G (S − P), 2022 → 2026. Red = ceiling counties; blue = floor counties.'),
    ('ΔG by county, population order','AR_DeltaG_by_Population.png',f'ΔG for all {N} counties, largest to smallest population, with the ceiling and floor counties marked.'),
    ('What ΔG is made of: ΔS vs ΔP','AR_DeltaG_Components_dS_vs_dP_by_Population.png','ΔS (change in Democratic share of ballots) and −ΔP (minus the change in the proxy) for each county. ΔG = ΔS − ΔP.'),
    ('Democratic share of ballots and the proxy, population order','AR_Stacked_Share_and_Proxy_by_Population.png','Bars: Democratic share of ballots, with the 2026 gain stacked on top. Markers: proxy P in 2022 and 2026.'),
    ('Forward fit: Arkansas-only constants','AR_Forward_Fit_G_vs_P_2022_2026.png','G vs P, 2022 and 2026, with the all-county and narrowed least-squares lines. Black outline = narrowed-out counties.'),
    ('ΔG vs ΔP','AR_DeltaG_vs_DeltaP_Scatter.png',f"ΔG against the proxy change ΔP. Slope {F['dG_on_dP']['m']/100:.3f}; the intercept ({sg(F['dG_on_dP']['b'])}) is the typical rise in S once ΔP is removed."),
    ('Regional constants','AR_Regional_Fits.png','Separate fits for Northwest, Central, Northeast and South, 2022 (top) and 2026 (bottom), against the statewide line.'),
    ('Over-ballot check','AR_Overballot_Check_by_Population.png','Ballots cast minus (Democratic + Republican governor votes), as a share of ballots. Yell 2022 is below zero; no county is below zero in 2026.')]
gr=f"""# Graphs

{BANNER}

Every chart carries the proxy label, the source and the 2026 UNOFFICIAL status in its footer. Bars run left to right from the largest county to the smallest (Census Vintage 2025).

"""+"".join(f"## {i}. {t}\n\n{img(fn,cap)}\n" for i,(t,fn,cap) in enumerate(CH,1))+f"""## Data behind the charts

- County table: [{REPO}/blob/main/data/AR_Governor_2022_2026_DeltaG_by_County.csv]({REPO}/blob/main/data/AR_Governor_2022_2026_DeltaG_by_County.csv)
- Fits, regional tests, over-ballot checks: [{REPO}/blob/main/data/AR_results_summary.json]({REPO}/blob/main/data/AR_results_summary.json)
- Verification (both passes, figure by figure): [{REPO}/tree/main/verification]({REPO}/tree/main/verification)
{REL('Graphs')}"""
open(WK+'Graphs.md','w').write(gr)
for fn in glob.glob(WK+'*.md'):
    t=open(fn).read(); t=re.sub(r'(?<![\w/.\-=&?])-(\d)',r'−\1',t); open(fn,'w').write(t)
print('built')

# ==================================================== SIDEBAR
open(WK+'_Sidebar.md','w').write("**Arkansas ΔG wiki**\n\n"+"".join(f"- [{t}](https://github.com/mbenson8989/Arkansas-Election-Analysis/wiki/{sl})\n" for t,sl in PAGES)+"- [Cedar County Audit (Nebraska)]("+CEDAR+")\n\n*P is a primary-ballot proxy (no party registration). 2026 general figures UNOFFICIAL.*\n")
