from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Polygon
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
F=ROOT/'figures'; F.mkdir(exist_ok=True)

def box(ax, xy, wh, text, fc='#f7f7f7', ec='#303030', fs=10, lw=1.2):
    x,y=xy; w,h=wh
    p=FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.02,rounding_size=0.02',fc=fc,ec=ec,lw=lw)
    ax.add_patch(p); ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=fs,wrap=True)
    return p

def arrow(ax,p1,p2,text=None,rad=0,style='-|>'):
    a=FancyArrowPatch(p1,p2,arrowstyle=style,mutation_scale=14,lw=1.2,color='#333333',connectionstyle=f'arc3,rad={rad}')
    ax.add_patch(a)
    if text:
        x=(p1[0]+p2[0])/2; y=(p1[1]+p2[1])/2
        ax.text(x,y+0.025,text,ha='center',va='bottom',fontsize=8)

def save(fig,name):
    fig.tight_layout(); fig.savefig(F/name,dpi=220,bbox_inches='tight'); plt.close(fig)

# 1. Three nested loops
fig,ax=plt.subplots(figsize=(11,6.2)); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis('off')
box(ax,(0.03,0.72),(0.20,0.16),'Private tensions,\nworld models and\npartial expressions',fc='#eef4ff')
box(ax,(0.30,0.72),(0.23,0.16),'Loop I\nSemantic constitution\n(schema / roles / variables)',fc='#fff2df')
box(ax,(0.61,0.72),(0.25,0.16),'Loop II\nFeasible-region discovery\n(cuts / columns / probes)',fc='#e9f7ef')
box(ax,(0.35,0.38),(0.31,0.18),'Materialized joint-action\narrangement (editable view)',fc='#f4ecff',lw=1.8)
box(ax,(0.13,0.08),(0.27,0.16),'Loop III\nNormative closure\n(recognition / commitment)',fc='#ffecef')
box(ax,(0.60,0.08),(0.27,0.16),'Execution, evidence,\nverification, acceptance\nand settlement',fc='#e8f5f5')
arrow(ax,(0.23,0.80),(0.30,0.80),'interpret')
arrow(ax,(0.53,0.80),(0.61,0.80),'propose grammar')
arrow(ax,(0.74,0.72),(0.61,0.56),'candidate + certificates')
arrow(ax,(0.50,0.56),(0.50,0.38),'materialize')
arrow(ax,(0.35,0.47),(0.27,0.24),'recognize')
arrow(ax,(0.40,0.16),(0.60,0.16),'compile')
arrow(ax,(0.74,0.24),(0.61,0.38),'findings',rad=-0.15)
arrow(ax,(0.35,0.38),(0.18,0.72),'new unknowns',rad=-0.2)
ax.text(0.5,0.96,'The Coordination Constitution Problem',ha='center',fontsize=17,fontweight='bold')
ax.text(0.5,0.92,'The protocol must construct the model, discover feasibility, and create valid social facts.',ha='center',fontsize=10)
save(fig,'coordination_constitution_loops.png')

# 2. Boundary oracle / body-edge duality
fig,ax=plt.subplots(figsize=(11,5.8)); ax.set_xlim(0,10); ax.set_ylim(0,6); ax.axis('off')
# private body polygon
poly=np.array([[0.8,1.0],[1.5,4.7],[3.5,5.2],[4.5,3.5],[3.7,1.2],[2.0,0.7]])
ax.add_patch(Polygon(poly,closed=True,fc='#dfefff',ec='#24527a',lw=2))
ax.text(2.6,3.0,'Private feasible body $K_i$\n(not centralized)',ha='center',va='center',fontsize=12)
# candidate points and cuts
points=[(4.9,4.7),(4.6,2.0),(3.3,5.5)]
for j,p in enumerate(points,1):
    ax.plot(*p,'o',ms=7,color='#b14a3b')
    ax.text(p[0]+0.1,p[1]+0.1,f'$y_{j}$',fontsize=10)
# boundary lines
ax.plot([3.8,5.6],[5.4,4.0],lw=2,color='#b14a3b')
ax.plot([3.8,5.3],[1.3,2.4],lw=2,color='#b14a3b')
ax.text(4.9,5.15,'separating cut',fontsize=9,rotation=-36)
ax.text(4.4,1.55,'counterexample',fontsize=9,rotation=31)
# oracle box
box(ax,(5.8,2.2),(1.65,1.6),'Boundary oracle\n\nmembership\nseparation\nsupport/value\nauthority',fc='#fff3dd')
arrow(ax,(4.9,3.0),(5.8,3.0),'query')
arrow(ax,(5.8,2.65),(4.6,2.25),'cut / certificate',rad=-0.15)
# master
box(ax,(8.0,2.0),(1.6,2.0),'Shared master\n\nkeeps only\nrelevant cuts,\ncolumns and\nversions',fc='#e7f6ea')
arrow(ax,(7.45,3.0),(8.0,3.0),'update')
ax.text(5,5.75,'Body–Boundary Duality as a Privacy-Preserving Coordination Primitive',ha='center',fontsize=16,fontweight='bold')
ax.text(5,0.15,'For convex bodies, all support/separation answers determine the body; finite adaptive queries recover only decision-relevant boundaries.',ha='center',fontsize=9)
save(fig,'body_boundary_duality.png')

# 3. Full protocol stack
fig,ax=plt.subplots(figsize=(11,7)); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis('off')
levels=[
 ('Human / organizational surface','Compiled world UI, review, edits, recognition, dispute',0.84,'#f4ecff'),
 ('Coordination medium','Versioned schema, arrangement graph, stances, probes, findings',0.69,'#e8f5f5'),
 ('Synthesis engine','LLM proposal + boundary oracles + optimization + ECVI',0.54,'#fff2df'),
 ('Authority kernel','Delegation, policy, invariants, commitment compiler, audit',0.39,'#ffecef'),
 ('Interoperability','A2A transport · MCP tools · Harness execution · event APIs',0.24,'#eef4ff'),
 ('External trust adapters','Platform identity / e-sign / escrow / insurance / chain / arbitration',0.09,'#e9f7ef'),
]
for title,desc,y,fc in levels:
    box(ax,(0.08,y),(0.84,0.105),f'{title}\n{desc}',fc=fc,fs=10.5,lw=1.4)
for i in range(len(levels)-1):
    arrow(ax,(0.50,levels[i][2]),(0.50,levels[i+1][2]+0.105))
ax.text(0.5,0.98,'Towow Generative Coordination Production Stack',ha='center',va='top',fontsize=17,fontweight='bold')
ax.text(0.5,0.015,'The research object is the coordination semantics and runtime; trust systems such as Wowok attach below through adapters.',ha='center',fontsize=9)
save(fig,'production_stack.png')

# 4. Ideal vs reality
fig,ax=plt.subplots(figsize=(11,6)); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis('off')
box(ax,(0.05,0.14),(0.40,0.70),'IDEAL MODEL\n\n• exact local oracles\n• truthful principals\n• complete arrangement grammar\n• convex / finitely enumerable constraints\n• stable probability estimates\n• reliable communication\n• enforceable trust adapter\n\nResult: provable convergence or finite termination\nunder explicit assumptions',fc='#e9f7ef',fs=11)
box(ax,(0.55,0.14),(0.40,0.70),'REAL DEPLOYMENT\n\n• LLM-generated approximate oracles\n• strategic or mistaken reports\n• evolving schemas and preferences\n• nonconvex, language-rich constraints\n• distribution shift and model drift\n• offline nodes and partial trust\n• jurisdiction-specific enforcement\n\nResult: bounded claims, abstention, audits,\nshadow mode and reversible rollout',fc='#fff2df',fs=11)
arrow(ax,(0.45,0.50),(0.55,0.50),'compilation gap')
ax.text(0.5,0.94,'Essence and Implementation Must Be Separated',ha='center',fontsize=17,fontweight='bold')
ax.text(0.5,0.07,'Every engineering compromise must state which ideal property it weakens and how the loss is measured.',ha='center',fontsize=9)
save(fig,'ideal_vs_reality.png')

# 5. lifecycle
fig,ax=plt.subplots(figsize=(12,4.8)); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis('off')
labels=[('Tension','not yet an intent'),('Schema','shared variables'),('Arrangement','editable candidate'),('Recognition','principal adopts'),('Commitment','directed obligation'),('Execution','external effects'),('Evidence','what occurred'),('Acceptance','who makes it count'),('Settlement','close or dispute')]
xs=np.linspace(0.035,0.965,len(labels))
for i,((title,sub),x) in enumerate(zip(labels,xs)):
    fc=['#eef4ff','#fff2df','#f4ecff','#ffecef','#ffecef','#e8f5f5','#e8f5f5','#e9f7ef','#e9f7ef'][i]
    box(ax,(x-0.047,0.38),(0.094,0.25),f'{title}\n{sub}',fc=fc,fs=8.7,lw=1.1)
    if i<len(labels)-1: arrow(ax,(x+0.047,0.505),(xs[i+1]-0.047,0.505))
ax.text(0.5,0.87,'Possibility Must Not Silently Become Obligation',ha='center',fontsize=17,fontweight='bold')
ax.text(0.5,0.17,'Each transition has a different authority, evidence rule, failure mode and rollback semantics.',ha='center',fontsize=9)
save(fig,'normative_lifecycle.png')
