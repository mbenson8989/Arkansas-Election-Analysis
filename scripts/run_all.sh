#!/bin/bash
# Re-run the whole pipeline on the saved raw files. (To re-download sources first: python3 scripts/fetch_sources.py)
set -e
cd /workspace/arkansas-elections
python3 scripts/pass_a.py
python3 scripts/pass_b.py > /dev/null
python3 scripts/compare_passes.py > /dev/null
python3 scripts/analysis.py > /dev/null
python3 scripts/charts.py
python3 scripts/build_wiki.py
python3 scripts/build_readme.py
python3 scripts/verify_wiki.py
# layout QA: render each page with GitHub's GFM renderer (read-only API call; creates nothing), then check tables/links/images
for p in Home Reverse-Math Locked-Arkansas-Formula Floor-and-Ceiling Graphs; do gh api markdown -f mode=gfm -f context=mbenson8989/Arkansas-Election-Analysis -F text=@wiki/$p.md > verification/layout_qa/$p.html; done
python3 scripts/layout_qa.py | tail -1
rm -rf repo/raw repo/scripts repo/verification && cp -r raw scripts verification repo/
python3 -c "import json;r=json.load(open('verification/compare_report.json'));print('compare:',r['total_comparisons'],'comparisons',r['matched'],'matched',r['mismatched'],'mismatched;',len(r['mismatches_in_analysis_figures']),'in analysis figures, all resolved for pass B:',r['all_analysis_mismatches_resolved_for_passB'],'; unresolved:',r['unresolved'])"
