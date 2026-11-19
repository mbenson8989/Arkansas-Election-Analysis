import json
W='/workspace/arkansas-elections/'; J=json.load(open(W+'repo/data/AR_results_summary.json')); C=json.load(open(W+'verification/compare_report.json'))
F=J['fits']; sg=lambda v:(f"{v:+.2f}").replace('-','−')
r=f"""# Arkansas Election Analysis: 2022 vs 2026 Governor (ΔG method, proxy version)

> **P = Democratic primary-ballot share (proxy — Arkansas has no party registration).** **2026 general-election figures are UNOFFICIAL** (not yet certified statewide; Arkansas SOS results feed v234, last updated Nov 19, 2026, 10:36 AM CST).

County-level analysis of the Arkansas governor race, 2022 vs 2026, for all 75 counties. It uses the ΔG method from Morissa Benson's [Cedar County Audit](https://github.com/mbenson8989/Nebraska-Election-Analysis-/wiki/Cedar-Audit). The full write-up is on the **[wiki](https://github.com/mbenson8989/Arkansas-Election-Analysis/wiki)**.

- **S** = Democratic governor votes ÷ total ballots cast
- **P** (proxy) = Democratic U.S. Senate primary votes ÷ total primary ballots cast, preferential primary of the same year (May 24, 2022; March 3, 2026)
- **G** = S − P; **ΔG** = G2026 − G2022; residual = ΔG − \\|ΔP\\| for counties whose Democratic primary votes fell; implied extra votes = D2026 − S2022 × ballots2026
- **Arkansas-only constants** (G = m·P/100 + b, 75 counties): 2022 m = {sg(F['2022']['m'])}, b = {sg(F['2022']['b'])}; 2026 m = {sg(F['2026']['m'])}, b = {sg(F['2026']['b'])} (2026 UNOFFICIAL)

**Status:** 2022 general and both primaries are official in the Arkansas SOS results feed. **2026 general: UNOFFICIAL.** No statewide certification was found on Nov 19, 2026; some counties (e.g. Jefferson, Nov 13) have certified locally.

## Contents

| Path | What |
|---|---|
| `*.png` | The 8 charts used on the wiki (AR_ prefix) |
| `data/AR_Governor_2022_2026_DeltaG_by_County.csv` | All 75 counties, every input and computed figure, sorted by population |
| `data/AR_results_summary.json` | Fits, narrowed fits, regional tests, floor and ceiling, over-ballot checks |
| `verification/` | Pass A and Pass B county tables, the figure-by-figure comparison ({C['total_comparisons']:,} comparisons, {C['matched']:,} matched), adjudication of every mismatch |
| `raw/` | Untouched SOS files: bulk FullDataFile.json and API responses for 4 elections, download log with URLs and times, reference files, Census file |

**Not in this repo:** `raw/2026/FullDataFile.json` (55.4 MB, over GitHub's 50 MB guideline) is excluded by `.gitignore`. Download it from the Arkansas SOS results host: https://results.tally-enr.com/results/arkansas/11b07106-031e-4d7c-911a-d01fb473d6dd/FullDataFile.json (the copy used here was feed version v234, SHA-256 `96920d3abe3e929e4805675b27e1771f837e282692365a464d861c66e2065101`; the feed is UNOFFICIAL and still updating, so a later download may differ). Pass A needs that file; Pass B and the analysis use the API responses, which are included.
| `scripts/` | `run_all.sh` → `fetch_sources.py` (optional re-download) · `pass_a.py` (bulk file, precinct sums) · `pass_b.py` (results API county rows, regex) · `compare_passes.py` · `analysis.py` · `charts.py` · `build_wiki.py` · `verify_wiki.py` · `layout_qa.py` |

## Verification

Two independent passes over the raw SOS files: {C['total_comparisons']:,} figure comparisons (75 counties × {C['figures_per_county']} figures), {C['matched']:,} matched and {C['mismatched']} mismatched. All 2026 figures matched. The {C['mismatched']} mismatches are White and Conway counties, 2022, where the SOS bulk download file's precinct rows add up to more governor votes than the ballots cast it reports. The {len(C['mismatches_in_analysis_figures'])} that are used in calculations were each resolved for Pass B by independent checks (internal impossibility, White County's certified totals, a third published county table, published statewide primary totals); the rest are 2022 governor-primary counts that no calculation uses. Over-ballot flag in the official figures: Yell County, 2022 (governor votes exceed ballots cast by {J['overballot']['2022']['min_margin_ballots_minus_gov']['votes']*-1}).

These pages measure a pattern. They make no claim about intent, fraud or cause.
"""
open(W+'repo/README.md','w').write(r); print('readme')
