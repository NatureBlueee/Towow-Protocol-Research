from pathlib import Path
import csv,re,unicodedata
import fitz
from docx import Document
from docx.oxml.ns import qn

ROOT=Path('/mnt/data/Towow_Unified_Paper_v1.0_formal')
PDF=ROOT/'qa/toc_pass1/通爻_主权智能主体共同现实形成_正式论文_v1.0.pdf'
DOCX=ROOT/'通爻_主权智能主体共同现实形成_正式论文_v1.0.docx'
MAN=ROOT/'qa/toc_manifest.tsv'
OUTMAP=ROOT/'qa/toc_page_map.tsv'

def norm(s:str)->str:
    s=unicodedata.normalize('NFKC',s)
    s=s.replace('–','-').replace('—','-').replace('‑','-').replace('：',':').replace('，',',')
    s=''.join(ch for ch in s if not ch.isspace())
    return s

pdf=fitz.open(PDF)
page_text=[norm(p.get_text('text')) for p in pdf]
# Find body start using abstract's first sentence
needle=norm('当大模型和 Agent 从信息处理工具转变为能够调用账户')
body_start=next((i for i,t in enumerate(page_text) if needle in t),None)
if body_start is None:
    raise RuntimeError('Could not locate body start')
print('body starts on PDF page',body_start+1)

rows=[]
with MAN.open(encoding='utf-8') as f:
    r=csv.DictReader(f,delimiter='\t')
    rows=list(r)

found=[]; cur=body_start
for row in rows:
    target=norm(row['text'])
    hit=None
    # sequential exact search; allow same page for multiple headings
    for i in range(cur,len(pdf)):
        if target in page_text[i]:
            hit=i; break
    if hit is None:
        # fallback using long prefix and suffix, still sequential
        prefix=target[:min(22,len(target))]
        suffix=target[-min(14,len(target)):]
        for i in range(cur,len(pdf)):
            if prefix in page_text[i] and (len(target)<25 or suffix in page_text[i]):
                hit=i; break
    if hit is None:
        # fallback: remove punctuation
        simple=''.join(ch for ch in target if ch.isalnum() or '\u4e00'<=ch<='\u9fff')
        pref=simple[:min(18,len(simple))]
        for i in range(cur,len(pdf)):
            st=''.join(ch for ch in page_text[i] if ch.isalnum() or '\u4e00'<=ch<='\u9fff')
            if pref and pref in st:
                hit=i; break
    if hit is None:
        print('NOT FOUND',row['index'],row['text'])
        found.append((row,None))
    else:
        found.append((row,hit+1)); cur=hit

missing=[x for x in found if x[1] is None]
print('mapped',len(found)-len(missing),'missing',len(missing),'last page',max(p for _,p in found if p))
if missing:
    raise RuntimeError('Some TOC headings were not mapped')

# Write map
with OUTMAP.open('w',encoding='utf-8',newline='') as f:
    w=csv.writer(f,delimiter='\t')
    w.writerow(['index','level','text','page_bookmark','page'])
    for row,page in found:
        w.writerow([row['index'],row['level'],row['text'],row['page_bookmark'],page])

# Patch bookmark-contained page number text in DOCX
D=Document(DOCX)
root=D._element
name_to_page={row['page_bookmark']:str(page) for row,page in found}
starts={b.get(qn('w:name')):b for b in root.iter(qn('w:bookmarkStart')) if b.get(qn('w:name')) in name_to_page}
if len(starts)!=len(name_to_page):
    print('bookmark starts',len(starts),'expected',len(name_to_page))
for name,page in name_to_page.items():
    b=starts[name]
    parent=b.getparent(); pos=parent.index(b)
    patched=False
    for sib in list(parent)[pos+1:]:
        if sib.tag==qn('w:bookmarkEnd'):
            break
        for t in sib.iter(qn('w:t')):
            t.text=page; patched=True; break
        if patched: break
    if not patched:
        raise RuntimeError(f'page text not found for {name}')
D.save(DOCX)
print('patched',len(name_to_page),'TOC page numbers')
