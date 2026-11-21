"""Layout QA on the five wiki pages, using GitHub's GFM renderer output saved in verification/layout_qa/<page>.html
(rendered with: gh api markdown -f mode=gfm -f context=mbenson8989/Arkansas-Election-Analysis -F text=@wiki/<page>.md).
Checks: every pipe table renders as <table> with consistent column counts; no stray markdown in rendered text; heading order;
Home 'Pages' list links all five slugs; in-wiki anchors exist; every Graphs image points at a file in repo/; banner is one short blockquote."""
import re, os, sys, html, json
from html.parser import HTMLParser
W='/workspace/arkansas-elections/'; WK=W+'wiki/'; Q=W+'verification/layout_qa/'
PAGES=['Home','Reverse-Math','Locked-Arkansas-Formula','Floor-and-Ceiling','Graphs']+(['Arkansas-County-PDF-Information'] if json.load(open('/workspace/arkansas-elections/scripts/publish_config.json'))['pdf_page_published'] else [])
def slugify(h): return re.sub(r'[^\w\- ]','',h.strip().lower()).replace(' ','-')
issues=[]; report={}
heads={}
for p in PAGES:
    src=open(WK+p+'.md').read(); out=open(Q+p+'.html').read(); rep={}
    # --- tables
    blocks=re.findall(r'(?:^\|.*\n)+',src,flags=re.M); rep['md_tables']=len(blocks)
    tabs=re.findall(r'<table[^>]*>.*?</table>',out,flags=re.S); rep['html_tables']=len(tabs)
    if len(blocks)!=len(tabs): issues.append((p,'table count',len(blocks),len(tabs)))
    for i,(b,t) in enumerate(zip(blocks,tabs)):
        rows=re.findall(r'<tr>(.*?)</tr>',t,flags=re.S); counts=[len(re.findall(r'<t[hd][ >]',r)) for r in rows]
        mdcounts=[len(re.split(r'(?<!\\)\|',l.strip()))-2 for l in b.strip().splitlines()]
        if len(set(counts))!=1: issues.append((p,f'table {i+1} ragged rendered rows',sorted(set(counts))))
        if len(set(mdcounts))!=1: issues.append((p,f'table {i+1} ragged markdown rows',sorted(set(mdcounts))))
        if len(rows)!=len(b.strip().splitlines())-1: issues.append((p,f'table {i+1} row count',len(rows),len(b.strip().splitlines())-1))
    # --- stray markdown in rendered text (outside code)
    txt=re.sub(r'<code>.*?</code>','',out,flags=re.S); txt=re.sub(r'<table[^>]*>.*?</table>',lambda m:re.sub(r'</?t[hdr][^>]*>',' ',m.group(0)),txt,flags=re.S)
    vis=html.unescape(re.sub(r'<[^>]+>','',txt))
    for pat,name in ((r'\*\*','unclosed/raw bold **'),(r'(?<![\w_])__[A-Za-z0-9]','raw __'),(r'\]\(','raw markdown link ]('),(r'\\n','literal \\n'),(r'^\s*\|','raw pipe row'),(r'\|\s*---','raw table separator'),(r'(?<![\w>])#{1,6} ','raw heading #')):
        for m in re.finditer(pat,vis,flags=re.M): issues.append((p,name,vis[max(0,m.start()-40):m.end()+40].replace('\n',' ')))
    if re.search(r'(?<!\\)\|',re.sub(r'(?m)^\|.*$','',re.sub(r'`[^`]*`','',src))): issues.append((p,'pipe outside a table in source'))
    for ln,l in enumerate(src.splitlines(),1):
        if l.count('**')%2: issues.append((p,'odd ** count on line',ln,l[:80]))
    # --- headings
    hs=re.findall(r'<h([1-6])[^>]*>(.*?)</h\1>',out,flags=re.S); lv=[int(h[0]) for h in hs]
    rep['headings']=[(l,html.unescape(re.sub(r'<[^>]+>','',t)).strip()) for l,t in hs]
    if lv.count(1)!=1 or lv[0]!=1: issues.append((p,'h1 must be single and first',lv[:3]))
    for a,b in zip(lv,lv[1:]):
        if b>a+1: issues.append((p,'heading level skip',a,b))
    heads[p]={slugify(t) for _,t in rep['headings']}
    # --- banner: one short blockquote
    bq=re.findall(r'(?m)^> .*$',src); rep['banner_chars']=len(bq[0]) if bq else 0
    first=[l for l in src.splitlines() if l.strip()][1] if src else ''
    if not first.startswith('> '): issues.append((p,'banner not directly under title'))
    if len(bq)<1 or rep['banner_chars']>320: issues.append((p,'banner too long or missing',rep['banner_chars']))
    report[p]=rep
# --- links: in-wiki page slugs and anchors
for p in PAGES:
    src=open(WK+p+'.md').read()
    for t,u in re.findall(r'\[([^\]]+)\]\(([^)\s]+)\)',src):
        if u.startswith('http'):
            if 'github.com/mbenson8989/Nebraska' in u and u!='https://github.com/mbenson8989/Nebraska-Election-Analysis-/wiki/Cedar-Audit' and not u.endswith('/wiki'): issues.append((p,'Cedar link wrong',u))
            continue
        pg,_,anc=u.partition('#'); pg=pg or p
        if pg not in PAGES: issues.append((p,'broken wiki link',u))
        elif anc and anc not in heads[pg]: issues.append((p,'broken anchor',u,sorted(heads[pg])))
home=open(WK+'Home.md').read().split('## Contents')[1].split('##')[0]
for s in PAGES:
    if f']({s})' not in home: issues.append(('Home','Contents list missing',s))
# --- Graphs images
RAW='https://raw.githubusercontent.com/mbenson8989/Arkansas-Election-Analysis/main/'
for pg in PAGES:
    imgs=re.findall(r'!\[[^\]]*\]\(([^)]+)\)',open(WK+pg+'.md').read()); report[pg]['images']=imgs
    for u in imgs:
        if not u.startswith(RAW) or not os.path.isfile(W+'repo/'+u[len(RAW):]): issues.append((pg,'image file missing in repo/',u))
    rimg=re.findall(r'<img [^>]*>',open(Q+pg+'.html').read())
    if len(rimg)!=len(imgs): issues.append((pg,'rendered image count',len(rimg),len(imgs)))
sb=open(WK+'_Sidebar.md').read()
for pg in PAGES:
    if f'/wiki/{pg})' not in sb: issues.append(('_Sidebar','missing',pg))
json.dump(dict(report=report,issues=issues),open(Q+'layout_qa_report.json','w'),indent=1,ensure_ascii=False)
for p in PAGES: print(p,{k:v for k,v in report[p].items() if k!='headings' and k!='images'})
print('ISSUES',len(issues)); [print(' ',i) for i in issues]
sys.exit(1 if issues else 0)
