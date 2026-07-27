#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent

# Constructed cases are deliberately small and explicit. They are design tests
# grounded in QDR coordination concerns/mechanisms and solo-work literature, not
# observations of actual OPC transactions.
CASES=[
 {
  'id':'opc01_standard_software_subscription','title':'标准 SaaS 订阅续费','description':'OPC Agent 在既定预算和条款内续费常用工具。',
  'context':dict(participants=2,schema_completeness=.98,standardization=.98,private_context_intensity=.1,authority_plurality=1,externality_risk=.05,irreversibility=.15,volatility=.1,evidence_burden=.2,platform_frame_sufficient=True,centralizable_within_grants=True,marketplace_available=True,deterministic_interface_available=True),
  'acceptable_modes':['DETERMINISTIC_SERVICE','PLATFORM_MARKET'],'required_controls':['scoped credentials','effect/acceptance separation','reopen trigger'],
  'grounding':['CollapseSafe negative control','QDR: mature rules can support centralized execution']
 },
 {
  'id':'opc02_calendar_scheduling','title':'跨方日程排期','description':'多个已授权日历间寻找可用时段，不改变业务承诺。',
  'context':dict(participants=3,schema_completeness=.95,standardization=.9,private_context_intensity=.3,authority_plurality=1,externality_risk=.05,irreversibility=.05,volatility=.2,evidence_burden=.1,platform_frame_sufficient=True,centralizable_within_grants=True,optimization_problem=True),
  'acceptable_modes':['CENTRAL_OPTIMIZER','DETERMINISTIC_SERVICE'],'required_controls':['scoped credentials','effect/acceptance separation','reopen trigger'],
  'grounding':['central computation is a component, not an excluded alternative']
 },
 {
  'id':'opc03_refund_inside_policy','title':'政策内退款','description':'退款金额、条件和审计证据均在预设规则内。',
  'context':dict(participants=2,schema_completeness=.95,standardization=.95,private_context_intensity=.1,authority_plurality=1,externality_risk=.05,irreversibility=.25,volatility=.1,evidence_burden=.3,platform_frame_sufficient=True,centralizable_within_grants=True,deterministic_interface_available=True),
  'acceptable_modes':['DETERMINISTIC_SERVICE'],'required_controls':['scoped credentials','effect/acceptance separation','reopen trigger'],
  'grounding':['fixed-schema low-risk control']
 },
 {
  'id':'opc04_creator_sponsorship','title':'创作者品牌赞助','description':'报价可标准化，但品牌契合、言论边界、交付修改和声誉风险需形成。',
  'context':dict(participants=2,schema_completeness=.55,standardization=.45,private_context_intensity=.55,authority_plurality=2,externality_risk=.25,irreversibility=.55,volatility=.5,evidence_burden=.45,platform_frame_sufficient=False,centralizable_within_grants=False,human_acceptance_required=True,broker_available=True,capacity_pressure=.7),
  'acceptable_modes':['HUMAN_BROKER','BILATERAL_FORMATION'],'required_controls':['versioned relation schema','scoped mandate','countercondition and refusal','resource reservation','target-world effect witness','acceptance gate','local reopen','staged probe before irreversible effect'],
  'grounding':['solo work: reputation and attention concentrated','QDR: boundary-spanning intermediaries']
 },
 {
  'id':'opc05_custom_ai_data_audit','title':'客户私有数据 AI 审计','description':'服务内容、数据位置、派生权、验收和撤销条件均未闭合。',
  'context':dict(participants=2,schema_completeness=.3,standardization=.2,private_context_intensity=.95,authority_plurality=4,externality_risk=.65,irreversibility=.7,volatility=.6,evidence_burden=.9,platform_frame_sufficient=False,centralizable_within_grants=False,human_acceptance_required=True,broker_available=True,capacity_pressure=.8),
  'acceptable_modes':['HUMAN_BROKER','BILATERAL_FORMATION'],'required_controls':['minimal disclosure / local oracle','affected-party standing and recourse','staged probe before irreversible effect','acceptance gate'],
  'grounding':['QDR: data/evidence and representation','Towow R5C: probe + countercondition']
 },
 {
  'id':'opc06_co_created_course','title':'两位超级个体共创课程','description':'共同品牌、知识产权、招生责任、退款和长期素材权利需要形成。',
  'context':dict(participants=2,schema_completeness=.35,standardization=.25,private_context_intensity=.7,authority_plurality=2,externality_risk=.35,irreversibility=.65,volatility=.55,evidence_burden=.5,platform_frame_sufficient=False,centralizable_within_grants=False,human_acceptance_required=True,capacity_pressure=.6),
  'acceptable_modes':['BILATERAL_FORMATION'],'required_controls':['versioned relation schema','resource reservation','acceptance gate','affected-party standing and recourse','staged probe before irreversible effect'],
  'grounding':['joint artifact rights as conditional commitments','OPC reputation coupling']
 },
 {
  'id':'opc07_three_freelancer_bid','title':'三位独立专家联合投标','description':'能力互补但需明确主承包、资源锁、责任和退出。',
  'context':dict(participants=4,schema_completeness=.45,standardization=.35,private_context_intensity=.6,authority_plurality=4,externality_risk=.3,irreversibility=.55,volatility=.6,evidence_burden=.55,platform_frame_sufficient=False,centralizable_within_grants=False,human_acceptance_required=True,broker_available=True,capacity_pressure=.75),
  'acceptable_modes':['HUMAN_BROKER','TEMPORARY_COALITION'],'required_controls':['versioned relation schema','resource reservation','acceptance gate','staged probe before irreversible effect'],
  'grounding':['QDR polycentric forms','role/authority separation']
 },
 {
  'id':'opc08_white_label_delivery','title':'白标交付合作','description':'一位超级个体代另一位向终端客户交付，存在身份、质量和责任穿透。',
  'context':dict(participants=3,schema_completeness=.4,standardization=.35,private_context_intensity=.75,authority_plurality=3,externality_risk=.55,irreversibility=.65,volatility=.45,evidence_burden=.7,platform_frame_sufficient=False,centralizable_within_grants=False,human_acceptance_required=True,broker_available=False,capacity_pressure=.5),
  'acceptable_modes':['TEMPORARY_COALITION'],'required_controls':['scoped mandate','affected-party standing and recourse','target-world effect witness','acceptance gate'],
  'grounding':['principal/agent/affected customer separation']
 },
 {
  'id':'opc09_micro_saas_integration','title':'两个 Micro-SaaS 的稳定 API 集成','description':'初次形成数据/故障责任后，重复调用应编译。',
  'context':dict(participants=2,schema_completeness=.72,standardization=.75,private_context_intensity=.45,authority_plurality=2,externality_risk=.25,irreversibility=.35,volatility=.25,evidence_burden=.6,platform_frame_sufficient=False,centralizable_within_grants=False,repeated_relation=True,deterministic_interface_available=True),
  'acceptable_modes':['BILATERAL_FORMATION','DETERMINISTIC_SERVICE'],'required_controls':['versioned relation schema','target-world effect witness','local reopen','minimum privilege','version pinning','defeater-triggered local reopen'],
  'grounding':['formation → compile → local reopen']
 },
 {
  'id':'opc10_content_license_catalog','title':'既有内容目录授权','description':'平台条款、许可范围和结算规则已标准化。',
  'context':dict(participants=2,schema_completeness=.9,standardization=.9,private_context_intensity=.2,authority_plurality=1,externality_risk=.1,irreversibility=.3,volatility=.2,evidence_burden=.25,platform_frame_sufficient=True,centralizable_within_grants=True,marketplace_available=True),
  'acceptable_modes':['PLATFORM_MARKET'],'required_controls':['scoped credentials','effect/acceptance separation','reopen trigger'],
  'grounding':['platform-sufficient negative control']
 },
 {
  'id':'opc11_agent_subcontracting_client_data','title':'Agent 委托分包商处理客户数据','description':'OPC 自己有客户合同，但是否可转委托及数据用途不明确。',
  'context':dict(participants=3,schema_completeness=.4,standardization=.3,private_context_intensity=.95,authority_plurality=4,externality_risk=.75,irreversibility=.65,volatility=.5,evidence_burden=.85,platform_frame_sufficient=False,centralizable_within_grants=False,human_acceptance_required=True,broker_available=True,capacity_pressure=.9),
  'acceptable_modes':['HUMAN_BROKER','TEMPORARY_COALITION'],'required_controls':['minimal disclosure / local oracle','affected-party standing and recourse','scoped mandate','acceptance gate'],
  'grounding':['delegation chain','data derivative control','third-party standing']
 },
 {
  'id':'opc12_acceptance_dispute','title':'交付验收争议','description':'双方对完成标准和证据解释不一致，且付款已到期。',
  'context':dict(participants=2,schema_completeness=.65,standardization=.5,private_context_intensity=.5,authority_plurality=2,externality_risk=.2,irreversibility=.75,volatility=.2,evidence_burden=.9,platform_frame_sufficient=True,centralizable_within_grants=False,dispute_active=True,human_acceptance_required=True),
  'acceptable_modes':['HUMAN_ADJUDICATION'],'required_controls':['preserve prior versions','freeze irreversible operations','record standing and remedy scope'],
  'grounding':['Effect ≠ Acceptance','dispute/recourse']
 },
 {
  'id':'opc13_ad_budget_execution','title':'预算内广告投放','description':'策略由人确认，Agent 在封顶预算、品牌和渠道规则内优化。',
  'context':dict(participants=2,schema_completeness=.9,standardization=.8,private_context_intensity=.3,authority_plurality=1,externality_risk=.15,irreversibility=.35,volatility=.65,evidence_burden=.4,platform_frame_sufficient=True,centralizable_within_grants=True,optimization_problem=True),
  'acceptable_modes':['CENTRAL_OPTIMIZER'],'required_controls':['scoped credentials','effect/acceptance separation','reopen trigger'],
  'grounding':['central optimizer within mandate']
 },
 {
  'id':'opc14_private_brand_partnership','title':'个人品牌长期联名','description':'长期身份绑定、声誉与未来内容方向不可被平台字段无损表达。',
  'context':dict(participants=2,schema_completeness=.25,standardization=.15,private_context_intensity=.85,authority_plurality=2,externality_risk=.45,irreversibility=.85,volatility=.75,evidence_burden=.55,platform_frame_sufficient=False,centralizable_within_grants=False,human_acceptance_required=True,broker_available=True,capacity_pressure=.65),
  'acceptable_modes':['HUMAN_BROKER','BILATERAL_FORMATION'],'required_controls':['staged probe before irreversible effect','acceptance gate','local reopen','affected-party standing and recourse'],
  'grounding':['OPC identity-business coupling']
 },
 {
  'id':'opc15_internal_agent_execution','title':'OPC 内部生成月度经营报告','description':'同一 accountability root 内，工具和数据均已授权。',
  'context':dict(participants=1,schema_completeness=.75,standardization=.7,private_context_intensity=.9,authority_plurality=1,externality_risk=.05,irreversibility=.05,volatility=.3,evidence_burden=.4,platform_frame_sufficient=False,centralizable_within_grants=True,self_executable=True),
  'acceptable_modes':['SELF_EXECUTION'],'required_controls':['mandate scope','resource reservation','effect witness'],
  'grounding':['one entity may contain many agents; not every action is A2A']
 },
 {
  'id':'opc16_dynamic_resource_swap','title':'多个超级个体的动态资源互换','description':'时间、渠道、开发和设计资源组合随项目变化。',
  'context':dict(participants=5,schema_completeness=.3,standardization=.2,private_context_intensity=.7,authority_plurality=5,externality_risk=.3,irreversibility=.5,volatility=.85,evidence_burden=.55,platform_frame_sufficient=False,centralizable_within_grants=False,broker_available=True,capacity_pressure=.8),
  'acceptable_modes':['HUMAN_BROKER','TEMPORARY_COALITION'],'required_controls':['resource reservation','countercondition and refusal','local reopen','minimal disclosure / local oracle'],
  'grounding':['dynamic capability formation','QDR mechanism contingency']
 },
 {
  'id':'opc17_tax_filing','title':'标准税务申报','description':'法律框架、字段、截止时间和回执均明确，必要时由专业人士复核。',
  'context':dict(participants=2,schema_completeness=.98,standardization=.98,private_context_intensity=.7,authority_plurality=1,externality_risk=.2,irreversibility=.5,volatility=.1,evidence_burden=.9,platform_frame_sufficient=True,centralizable_within_grants=True,deterministic_interface_available=True),
  'acceptable_modes':['DETERMINISTIC_SERVICE'],'required_controls':['scoped credentials','effect/acceptance separation','reopen trigger'],
  'grounding':['complex/high-evidence yet institutionally specified']
 },
 {
  'id':'opc18_new_market_entry','title':'陌生市场的合作进入','description':'目标客户、当地伙伴、合规和交付结构均需要探索。',
  'context':dict(participants=3,schema_completeness=.2,standardization=.15,private_context_intensity=.6,authority_plurality=3,externality_risk=.5,irreversibility=.6,volatility=.8,evidence_burden=.75,platform_frame_sufficient=False,centralizable_within_grants=False,human_acceptance_required=True,broker_available=True,capacity_pressure=.9),
  'acceptable_modes':['HUMAN_BROKER','TEMPORARY_COALITION'],'required_controls':['versioned relation schema','countercondition and refusal','staged probe before irreversible effect','affected-party standing and recourse'],
  'grounding':['possibility formation under incomplete grammar']
 },
 {
  'id':'opc19_standard_freelance_marketplace','title':'标准化小额自由职业任务','description':'平台已定义范围、托管、交付和争议，任务低风险。',
  'context':dict(participants=2,schema_completeness=.9,standardization=.9,private_context_intensity=.25,authority_plurality=1,externality_risk=.1,irreversibility=.25,volatility=.2,evidence_burden=.3,platform_frame_sufficient=True,centralizable_within_grants=True,marketplace_available=True),
  'acceptable_modes':['PLATFORM_MARKET'],'required_controls':['scoped credentials','effect/acceptance separation','reopen trigger'],
  'grounding':['platform-sufficient control']
 },
 {
  'id':'opc20_repeated_bookkeeping','title':'重复记账流程','description':'首次形成账户映射和审计边界后，月度运行应确定化。',
  'context':dict(participants=2,schema_completeness=.78,standardization=.85,private_context_intensity=.7,authority_plurality=2,externality_risk=.2,irreversibility=.25,volatility=.15,evidence_burden=.75,platform_frame_sufficient=False,centralizable_within_grants=False,repeated_relation=True,deterministic_interface_available=True),
  'acceptable_modes':['BILATERAL_FORMATION','DETERMINISTIC_SERVICE'],'required_controls':['versioned relation schema','minimum privilege','version pinning','defeater-triggered local reopen'],
  'grounding':['formation/compile separation']
 },
 {
  'id':'opc21_public_claim_with_reputation','title':'Agent 代表本人公开发布观点','description':'内容可生成，但最终身份认领和声誉风险不能由模型代行。',
  'context':dict(participants=1,schema_completeness=.6,standardization=.3,private_context_intensity=.85,authority_plurality=2,externality_risk=.45,irreversibility=.8,volatility=.5,evidence_burden=.5,platform_frame_sufficient=False,centralizable_within_grants=False,human_acceptance_required=True,self_executable=False),
  'acceptable_modes':['BILATERAL_FORMATION'],'required_controls':['scoped mandate','acceptance gate','staged probe before irreversible effect'],
  'grounding':['identity/capability/authority/objective orthogonality']
 },
 {
  'id':'opc22_emergency_delivery_replan','title':'临近截止期的紧急重排','description':'已存在合同，但资源失效，需要中心优化并由双方确认变更。',
  'context':dict(participants=2,schema_completeness=.75,standardization=.65,private_context_intensity=.45,authority_plurality=2,externality_risk=.2,irreversibility=.55,volatility=.9,evidence_burden=.5,platform_frame_sufficient=True,centralizable_within_grants=True,optimization_problem=True,human_acceptance_required=True,broker_available=True,capacity_pressure=.9),
  'acceptable_modes':['HUMAN_BROKER','BILATERAL_FORMATION'],'required_controls':['resource reservation','acceptance gate','local reopen'],
  'grounding':['parameter drift can cross a mandate/resource threshold']
 },
 {
  'id':'opc23_customer_support_triage','title':'客户支持工单分流','description':'分类和建议可中心化，退款/承诺等高权利动作回到本地 Gate。',
  'context':dict(participants=2,schema_completeness=.85,standardization=.8,private_context_intensity=.35,authority_plurality=2,externality_risk=.15,irreversibility=.25,volatility=.5,evidence_burden=.4,platform_frame_sufficient=True,centralizable_within_grants=True,optimization_problem=True,human_acceptance_required=False),
  'acceptable_modes':['CENTRAL_OPTIMIZER'],'required_controls':['do not mutate local authority','return ranked candidates with evidence'],
  'grounding':['partial centralization with local authority gates']
 },
 {
  'id':'opc24_training_data_license','title':'将客户资料用于模型训练','description':'服务权、训练权、派生权和再披露权彼此不同。',
  'context':dict(participants=3,schema_completeness=.25,standardization=.2,private_context_intensity=1.0,authority_plurality=4,externality_risk=.85,irreversibility=.9,volatility=.4,evidence_burden=.9,platform_frame_sufficient=False,centralizable_within_grants=False,human_acceptance_required=True,broker_available=True,capacity_pressure=.6),
  'acceptable_modes':['HUMAN_BROKER','TEMPORARY_COALITION'],'required_controls':['minimal disclosure / local oracle','affected-party standing and recourse','scoped mandate','staged probe before irreversible effect','acceptance gate'],
  'grounding':['data use creates derivative data and persistent effects']
 }
]

(HERE/'fixtures.json').write_text(json.dumps({'version':'0.7','cases':CASES,'warning':'Constructed design fixtures; not empirical OPC observations.'},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'cases':len(CASES),'path':str(HERE/'fixtures.json')},ensure_ascii=False))
