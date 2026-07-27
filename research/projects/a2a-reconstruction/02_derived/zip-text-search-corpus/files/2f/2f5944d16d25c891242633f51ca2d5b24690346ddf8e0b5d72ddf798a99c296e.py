from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

out = Path('/mnt/data/Towow_A2A_Independent_Research_v0.7/figures/fig02_lifecycle.png')
W,H=2400,980
img=Image.new('RGB',(W,H),'white')
d=ImageDraw.Draw(img)
font_path='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
font=ImageFont.truetype(font_path,34)
font_small=ImageFont.truetype(font_path,25)
font_label=ImageFont.truetype(font_path,27)

labels=[
'0 身份与\n权威根','1 Mandate\n与策略','2 本地世界\n编译','3 机会发现\n问题构成','4 协调机制\n选择','5 RelationVersion\n与 probe',
'6 能力 / 伙伴\n资源组装','7 认领 / 承诺\n合同化','8 Operation\n与 Effect','9 Adoption /\nAcceptance','10 数据派生\n与学习','11 Defeater\n退出 / 重开'
]
box_w,box_h=320,135
margin_x=80
gap=(W-2*margin_x-6*box_w)/5
y_top=120
y_bottom=650
coords={}
for i in range(6):
    x=margin_x+i*(box_w+gap)
    coords[i]=(x,y_top,x+box_w,y_top+box_h)
for j,i in enumerate(range(6,12)):
    # bottom row right to left (6 on right, 11 on left)
    x=margin_x+(5-j)*(box_w+gap)
    coords[i]=(x,y_bottom,x+box_w,y_bottom+box_h)

def rounded_box(rect,label):
    d.rounded_rectangle(rect,radius=24,outline='black',width=3,fill='white')
    x0,y0,x1,y1=rect
    lines=label.split('\n')
    total=sum(d.textbbox((0,0),line,font=font)[3]-d.textbbox((0,0),line,font=font)[1] for line in lines)+(len(lines)-1)*6
    y=(y0+y1-total)/2
    for line in lines:
        bb=d.textbbox((0,0),line,font=font)
        tw=bb[2]-bb[0]; th=bb[3]-bb[1]
        d.text(((x0+x1-tw)/2,y),line,font=font,fill='black')
        y+=th+6
for i,l in enumerate(labels): rounded_box(coords[i],l)

def arrow_line(points,width=4,dashed=False,label=None,label_pos=None):
    # draw segments
    if dashed:
        for p1,p2 in zip(points,points[1:]):
            x1,y1=p1;x2,y2=p2
            import math
            L=math.hypot(x2-x1,y2-y1)
            if L==0: continue
            ux=(x2-x1)/L;uy=(y2-y1)/L
            pos=0; dash=18; gapd=13
            while pos<L:
                end=min(pos+dash,L)
                d.line((x1+ux*pos,y1+uy*pos,x1+ux*end,y1+uy*end),fill='black',width=width)
                pos=end+gapd
    else:
        d.line(points,fill='black',width=width,joint='curve')
    # arrowhead at last segment
    import math
    p1=points[-2]; p2=points[-1]
    ang=math.atan2(p2[1]-p1[1],p2[0]-p1[0])
    L=20
    a1=ang+2.55; a2=ang-2.55
    poly=[p2,(p2[0]+L*math.cos(a1),p2[1]+L*math.sin(a1)),(p2[0]+L*math.cos(a2),p2[1]+L*math.sin(a2))]
    d.polygon(poly,fill='black')
    if label:
        if label_pos is None:
            xs=[p[0] for p in points]; ys=[p[1] for p in points]
            label_pos=(sum(xs)/len(xs),sum(ys)/len(ys))
        bb=d.textbbox((0,0),label,font=font_label)
        tx=label_pos[0]-(bb[2]-bb[0])/2; ty=label_pos[1]-(bb[3]-bb[1])/2
        # white backing
        d.rectangle((tx-8,ty-4,tx+(bb[2]-bb[0])+8,ty+(bb[3]-bb[1])+4),fill='white')
        d.text((tx,ty),label,font=font_label,fill='black')

# top sequential arrows
for i in range(5):
    a=coords[i];b=coords[i+1]
    arrow_line([(a[2],(a[1]+a[3])/2),(b[0],(b[1]+b[3])/2)])
# transition 5 to 6 down right
r5=coords[5];r6=coords[6]
arrow_line([((r5[0]+r5[2])/2,r5[3]),((r5[0]+r5[2])/2,470),((r6[0]+r6[2])/2,470),((r6[0]+r6[2])/2,r6[1])],label='形成后进入执行准备',label_pos=(2035,435))
# bottom sequential arrows right-to-left 6->11
for i in range(6,11):
    a=coords[i]; b=coords[i+1]
    arrow_line([(a[0],(a[1]+a[3])/2),(b[2],(b[1]+b[3])/2)])
# dashed 5 -> 4 above boxes
r4=coords[4]
arrow_line([((r5[0]+r5[2])/2,r5[1]),((r5[0]+r5[2])/2,65),((r4[0]+r4[2])/2,65),((r4[0]+r4[2])/2,r4[1])],dashed=True,label='条件改变',label_pos=((r4[0]+r5[2])/2,35))
# dashed 8 -> 5 (reality counterexample) via central gap
r8=coords[8]
arrow_line([((r8[0]+r8[2])/2,r8[1]),((r8[0]+r8[2])/2,535),((r5[0]+r5[2])/2,535),((r5[0]+r5[2])/2,r5[3])],dashed=True,label='现实反例',label_pos=(1700,505))
# dashed 11 -> 2 around left edge and mid gap
r11=coords[11];r2=coords[2]
arrow_line([((r11[0]+r11[2])/2,r11[1]),((r11[0]+r11[2])/2,565),(35,565),(35,355),((r2[0]+r2[2])/2,355),((r2[0]+r2[2])/2,r2[3])],dashed=True,label='scoped reopen',label_pos=(470,325))
# row captions
caption=ImageFont.truetype(font_path,29)
d.text((80,25),'开放形成与制度构成',font=caption,fill='black')
d.text((80,875),'执行、采用、学习与局部重开（底行从右向左）',font=caption,fill='black')
img.save(out,dpi=(160,160))
print(out, img.size)
