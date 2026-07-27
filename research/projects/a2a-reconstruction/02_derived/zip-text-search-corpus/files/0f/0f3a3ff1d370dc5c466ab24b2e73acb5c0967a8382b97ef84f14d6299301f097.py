from pathlib import Path
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt

P=Path('/mnt/data/Towow_Unified_Paper_v1.0_formal/通爻_主权智能主体共同现实形成_正式论文_v1.0.docx')
doc=Document(P)
body=doc._element.body

W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
SERIF='Noto Serif CJK SC'; SANS='Noto Sans CJK SC'

# Remove existing dynamic TOC SDT
for child in list(body):
    if child.tag==qn('w:sdt'):
        body.remove(child)
        break

# Find insertion point: immediately after Date paragraph
insert_idx=None
for i,ch in enumerate(list(body)):
    if ch.tag==qn('w:p'):
        sty=ch.find('./'+qn('w:pPr')+'/'+qn('w:pStyle'))
        if sty is not None and sty.get(qn('w:val'))=='Date':
            insert_idx=i+1
            break
if insert_idx is None:
    insert_idx=4

# Find max bookmark id
max_id=0
for b in body.iter(qn('w:bookmarkStart')):
    v=b.get(qn('w:id'))
    if v and v.isdigit(): max_id=max(max_id,int(v))
next_id=max_id+1

# Gather heading paragraphs from body in document order, depth 1-2
headings=[]
for ch in list(body):
    if ch.tag!=qn('w:p'): continue
    pstyle=ch.find('./'+qn('w:pPr')+'/'+qn('w:pStyle'))
    if pstyle is None: continue
    sid=pstyle.get(qn('w:val')) or ''
    if sid not in ('Heading1','Heading2'): continue
    text=''.join(t.text or '' for t in ch.iter(qn('w:t'))).strip()
    if not text: continue
    level=1 if sid=='Heading1' else 2
    headings.append((level,text,ch))


def add_bookmark(p, name, bid):
    start=OxmlElement('w:bookmarkStart'); start.set(qn('w:id'),str(bid)); start.set(qn('w:name'),name)
    end=OxmlElement('w:bookmarkEnd'); end.set(qn('w:id'),str(bid))
    # after pPr if present
    pPr=p.find(qn('w:pPr'))
    idx=1 if pPr is not None else 0
    p.insert(idx,start); p.append(end)


def add_font(rPr,font,size,bold=False,color='333333'):
    rfonts=OxmlElement('w:rFonts')
    for a in ('ascii','hAnsi','eastAsia','cs'): rfonts.set(qn('w:'+a),font)
    rPr.append(rfonts)
    sz=OxmlElement('w:sz'); sz.set(qn('w:val'),str(int(size*2))); rPr.append(sz)
    szcs=OxmlElement('w:szCs'); szcs.set(qn('w:val'),str(int(size*2))); rPr.append(szcs)
    if bold:
        b=OxmlElement('w:b'); rPr.append(b)
        bcs=OxmlElement('w:bCs'); rPr.append(bcs)
    col=OxmlElement('w:color'); col.set(qn('w:val'),color); rPr.append(col)


def make_title():
    p=OxmlElement('w:p'); pPr=OxmlElement('w:pPr'); p.append(pPr)
    jc=OxmlElement('w:jc'); jc.set(qn('w:val'),'center'); pPr.append(jc)
    sp=OxmlElement('w:spacing'); sp.set(qn('w:before'),'120'); sp.set(qn('w:after'),'260'); pPr.append(sp)
    keep=OxmlElement('w:keepNext'); pPr.append(keep)
    r=OxmlElement('w:r'); rPr=OxmlElement('w:rPr'); add_font(rPr,SANS,16,True,'2E5D8C'); r.append(rPr)
    t=OxmlElement('w:t'); t.text='目录'; r.append(t); p.append(r)
    return p


def make_entry(level,text,anchor,page_anchor):
    p=OxmlElement('w:p'); pPr=OxmlElement('w:pPr'); p.append(pPr)
    # spacing and indents
    ind=OxmlElement('w:ind')
    if level==2:
        ind.set(qn('w:left'),'420'); ind.set(qn('w:hanging'),'0')
    else:
        ind.set(qn('w:left'),'0')
    pPr.append(ind)
    sp=OxmlElement('w:spacing')
    sp.set(qn('w:before'),'55' if level==1 else '0')
    sp.set(qn('w:after'),'20')
    sp.set(qn('w:line'),'230'); sp.set(qn('w:lineRule'),'auto')
    pPr.append(sp)
    # right tab with dot leader at 9,150 twips
    tabs=OxmlElement('w:tabs'); tab=OxmlElement('w:tab')
    tab.set(qn('w:val'),'right'); tab.set(qn('w:leader'),'dot'); tab.set(qn('w:pos'),'9150')
    tabs.append(tab); pPr.append(tabs)
    if level==1:
        keep=OxmlElement('w:keepNext'); pPr.append(keep)
    # hyperlink heading text
    hl=OxmlElement('w:hyperlink'); hl.set(qn('w:anchor'),anchor); hl.set(qn('w:history'),'1')
    r=OxmlElement('w:r'); rPr=OxmlElement('w:rPr'); add_font(rPr,SERIF,9.2 if level==1 else 8.6,level==1,'252525')
    r.append(rPr); t=OxmlElement('w:t'); t.text=text; r.append(t); hl.append(r); p.append(hl)
    # tab
    rt=OxmlElement('w:r'); rPrt=OxmlElement('w:rPr'); add_font(rPrt,SERIF,8.6,False,'555555'); rt.append(rPrt)
    tabchar=OxmlElement('w:tab'); rt.append(tabchar); p.append(rt)
    # page placeholder wrapped in bookmark
    bs=OxmlElement('w:bookmarkStart'); bs.set(qn('w:id'),str(page_anchor[1])); bs.set(qn('w:name'),page_anchor[0]); p.append(bs)
    rp=OxmlElement('w:r'); rPrp=OxmlElement('w:rPr'); add_font(rPrp,SERIF,8.6,False,'555555'); rp.append(rPrp)
    tp=OxmlElement('w:t'); tp.text='000'; rp.append(tp); p.append(rp)
    be=OxmlElement('w:bookmarkEnd'); be.set(qn('w:id'),str(page_anchor[1])); p.append(be)
    return p

nodes=[make_title()]
manifest=[]
for i,(level,text,p) in enumerate(headings,1):
    anchor=f'toc_h_{i:03d}'
    add_bookmark(p,anchor,next_id); next_id+=1
    page_bm=f'toc_p_{i:03d}'; page_bid=next_id; next_id+=1
    nodes.append(make_entry(level,text,anchor,(page_bm,page_bid)))
    manifest.append((i,level,text,anchor,page_bm))

# Insert all TOC nodes in order
for offset,node in enumerate(nodes):
    body.insert(insert_idx+offset,node)

# Save a manifest for page-number patching
man=Path('/mnt/data/Towow_Unified_Paper_v1.0_formal/qa/toc_manifest.tsv')
with man.open('w',encoding='utf-8') as f:
    f.write('index\tlevel\ttext\tanchor\tpage_bookmark\n')
    for row in manifest:
        f.write('\t'.join(map(str,row))+'\n')

doc.save(P)
print('inserted',len(manifest),'TOC entries')
