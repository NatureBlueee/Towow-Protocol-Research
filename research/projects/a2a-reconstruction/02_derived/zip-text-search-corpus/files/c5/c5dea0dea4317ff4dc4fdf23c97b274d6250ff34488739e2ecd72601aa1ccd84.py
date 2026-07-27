from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION_START
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from pathlib import Path

SRC=Path('/mnt/data/Towow_Unified_Paper_v1.0_formal/qa/reference_base.docx')
OUT=Path('/mnt/data/Towow_Unified_Paper_v1.0_formal/qa/reference_formal.docx')
doc=Document(SRC)

SERIF='Noto Serif CJK SC'
SANS='Noto Sans CJK SC'
MONO='Liberation Mono'


def set_font(style, name, size=None, bold=None, italic=None, color=None):
    style.font.name=name
    try:
        style._element.rPr.rFonts.set(qn('w:eastAsia'), name)
        style._element.rPr.rFonts.set(qn('w:ascii'), name)
        style._element.rPr.rFonts.set(qn('w:hAnsi'), name)
    except Exception:
        pass
    if size is not None:
        style.font.size=Pt(size)
    if bold is not None:
        style.font.bold=bold
    if italic is not None:
        style.font.italic=italic
    if color is not None:
        style.font.color.rgb=RGBColor(*color)

def get_style(doc, name):
    try:
        return doc.styles[name]
    except KeyError:
        for st in doc.styles:
            if st.name == name or st.style_id == name.replace(' ', ''):
                return st
        raise

# Page setup embedded in reference doc
for sec in doc.sections:
    sec.page_width=Cm(21.0)
    sec.page_height=Cm(29.7)
    sec.top_margin=Cm(2.35)
    sec.bottom_margin=Cm(2.25)
    sec.left_margin=Cm(2.45)
    sec.right_margin=Cm(2.25)
    sec.header_distance=Cm(1.1)
    sec.footer_distance=Cm(1.1)

# Base paragraphs
for nm in ['Normal','Body Text']:
    st=get_style(doc,nm)
    set_font(st,SERIF,10.5)
    pf=st.paragraph_format
    pf.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
    pf.line_spacing=1.35
    pf.space_after=Pt(5)
    pf.widow_control=True
    pf.first_line_indent=Cm(0.74)

st=get_style(doc,'First Paragraph')
set_font(st,SERIF,10.5)
st.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
st.paragraph_format.line_spacing=1.35
st.paragraph_format.space_after=Pt(5)
st.paragraph_format.first_line_indent=Cm(0)
st.paragraph_format.widow_control=True

st=get_style(doc,'Compact')
set_font(st,SERIF,10)
st.paragraph_format.line_spacing=1.15
st.paragraph_format.space_after=Pt(2)
st.paragraph_format.first_line_indent=Cm(0)

st=get_style(doc,'Block Text')
set_font(st,SERIF,9.8)
st.paragraph_format.left_indent=Cm(0.75)
st.paragraph_format.right_indent=Cm(0.5)
st.paragraph_format.space_before=Pt(3)
st.paragraph_format.space_after=Pt(6)
st.paragraph_format.line_spacing=1.25
st.paragraph_format.first_line_indent=Cm(0)

# Front matter
st=get_style(doc,'Title')
set_font(st,SANS,22,bold=True,color=(25,25,25))
st.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER
st.paragraph_format.space_before=Pt(90)
st.paragraph_format.space_after=Pt(18)
st.paragraph_format.keep_with_next=True

st=get_style(doc,'Subtitle')
set_font(st,SERIF,14,bold=False,color=(55,55,55))
st.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER
st.paragraph_format.space_after=Pt(32)
st.paragraph_format.keep_with_next=True

for nm,sz in [('Author',11),('Date',10.5)]:
    st=get_style(doc,nm)
    set_font(st,SERIF,sz)
    st.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER
    st.paragraph_format.space_after=Pt(8)

# Headings
heading_cfg={
    'Heading 1':(16,18,8),
    'Heading 2':(13,14,5),
    'Heading 3':(11.5,10,4),
    'Heading 4':(10.8,8,3),
    'Heading 5':(10.5,6,2),
    'Heading 6':(10.5,5,2),
}
for nm,(size,before,after) in heading_cfg.items():
    st=get_style(doc,nm)
    set_font(st,SANS,size,bold=True,color=(20,20,20))
    pf=st.paragraph_format
    pf.space_before=Pt(before)
    pf.space_after=Pt(after)
    pf.keep_with_next=True
    pf.keep_together=True
    pf.widow_control=True
    pf.first_line_indent=Cm(0)
    pf.alignment=WD_ALIGN_PARAGRAPH.LEFT

# Abstract
for nm in ['Abstract','Bibliography','Footnote Text','Footnote Block Text']:
    st=get_style(doc,nm)
    set_font(st,SERIF,9.5 if nm!='Abstract' else 10.2)
    st.paragraph_format.line_spacing=1.25
    st.paragraph_format.space_after=Pt(3)
    st.paragraph_format.first_line_indent=Cm(0.7 if nm=='Abstract' else 0)
    st.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY

st=get_style(doc,'Abstract Title')
set_font(st,SANS,15,bold=True)
st.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER
st.paragraph_format.space_before=Pt(12)
st.paragraph_format.space_after=Pt(10)

# Captions and figures
for nm in ['Caption','Image Caption','Table Caption']:
    st=get_style(doc,nm)
    set_font(st,SERIF,9,italic=False,color=(60,60,60))
    st.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER
    st.paragraph_format.line_spacing=1.1
    st.paragraph_format.space_before=Pt(3)
    st.paragraph_format.space_after=Pt(8)
    st.paragraph_format.keep_with_next=False
    st.paragraph_format.first_line_indent=Cm(0)

st=get_style(doc,'Figure')
set_font(st,SERIF,10)
st.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER
st.paragraph_format.space_before=Pt(7)
st.paragraph_format.space_after=Pt(2)
st.paragraph_format.first_line_indent=Cm(0)

# Table style
st=get_style(doc,'Table')
set_font(st,SERIF,8.4)

# TOC
st=get_style(doc,'TOC Heading')
set_font(st,SANS,16,bold=True)
st.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER
st.paragraph_format.space_before=Pt(8)
st.paragraph_format.space_after=Pt(12)

# Character styles
set_font(get_style(doc,'Default Paragraph Font'),SERIF,10.5)
set_font(get_style(doc,'Verbatim Char'),MONO,8.8)
set_font(get_style(doc,'Hyperlink'),SERIF,10.5,color=(30,60,120))

# Add source code style if absent
if 'Source Code' not in [x.name for x in doc.styles]:
    st=doc.styles.add_style('Source Code',1)
else:
    st=get_style(doc,'Source Code')
set_font(st,MONO,8.6)
st.paragraph_format.left_indent=Cm(0.45)
st.paragraph_format.right_indent=Cm(0.25)
st.paragraph_format.space_before=Pt(3)
st.paragraph_format.space_after=Pt(5)
st.paragraph_format.line_spacing=1.05
st.paragraph_format.first_line_indent=Cm(0)

# Set default language to zh-CN for key styles
for nm in ['Normal','Body Text','First Paragraph','Title','Subtitle','Heading 1','Heading 2','Heading 3','Heading 4','Caption','Bibliography']:
    st=get_style(doc,nm)
    rpr=st._element.get_or_add_rPr()
    lang=rpr.find(qn('w:lang'))
    if lang is None:
        lang=OxmlElement('w:lang')
        rpr.append(lang)
    lang.set(qn('w:val'),'zh-CN')
    lang.set(qn('w:eastAsia'),'zh-CN')

# Set document default fonts too
styles_el=doc.styles.element
docdefaults=styles_el.find(qn('w:docDefaults'))
if docdefaults is not None:
    rprdefault=docdefaults.find(qn('w:rPrDefault'))
    if rprdefault is not None:
        rpr=rprdefault.find(qn('w:rPr'))
        if rpr is not None:
            rfonts=rpr.find(qn('w:rFonts'))
            if rfonts is None:
                rfonts=OxmlElement('w:rFonts'); rpr.insert(0,rfonts)
            for attr,val in [('ascii',SERIF),('hAnsi',SERIF),('eastAsia',SERIF),('cs',SERIF)]:
                rfonts.set(qn('w:'+attr),val)

# metadata
props=doc.core_properties
props.title='主权智能主体的共同现实形成'
props.subject='面向超级个体与一人公司的生成式协调理论、协议与运行系统'
props.author='通爻研究计划'
props.keywords='Agent Entity; OPC; 生成式协调; 主权代理; 共同现实'
props.comments='Formal unified research paper, version 1.0'

doc.save(OUT)
print(OUT)
