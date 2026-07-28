#!/usr/bin/env python3
"""forge-think MCP server — 多步对抗淬炼引擎 + 可迭代 SOP 库。

server 不调任何 LLM。每回合推理由 host 当前 agent 自己完成;server 负责:
  - 编排(forge_start/step)、记账(trace)、持久化(防掉线)、启动恢复(可续)
  - 可热重载的 SOP 库(forge_sop_*):沉淀踩坑经验/公司规定/项目约束

命名说明:避开 think/reason/推演 等通用词(跟 LLM 内在能力抢权重),用 forge(锻造/淬炼)。
触发词用符号+生僻动词(/forge、@forge-think、开炉),不用"X 模式"状态描述。

工具(9 个):
  手册:forge_help
  推演:forge_start / forge_step / forge_review / forge_stop
  SOP: forge_sop_save / forge_sop_list / forge_sop_get / forge_sop_delete
"""
import json
import os
import uuid
from datetime import datetime
from typing import Optional, List, Literal

from pydantic import BaseModel, Field, model_validator
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "forge_think",
    instructions=(
        "forge-think — 多步对抗淬炼引擎。【触发】用户说「用 forge-think」「使用 forge-think」「开启 forge-think」「开炉」「启动锻造」"
        "或遇到需要深度推演/多步打磨/对抗审查的任务时,主动调 forge-think。"
        "把深度推演/多步打磨外包成结构化 tool,适用于技术选型、代码审查、根因排查、方案打磨、决策。"
        "9 个 tool:forge_help(使用手册,先调它)、"
        "forge_start/step/review/stop(seq/chain/deliberate 三模式淬炼)、"
        "forge_sop_save/list/get/delete(可学习的 SOP 库,沉淀踩坑/规定/约束)。"
        "第一次用先调 forge_help 拿完整指引。"
    ),
)

SESSION_DIR = os.path.join(os.path.expanduser("~"), ".forge-mcp", "sessions")
SOP_DIR = os.path.join(os.path.expanduser("~"), ".forge-mcp", "sops")
DEFAULT_SOPS_MARKER = os.path.join(SOP_DIR, ".defaults-installed-v1")

DEFAULT_SOPS = (
    {
        "name": "evidence-first-triage",
        "description": "面对故障、异常或争议时先建事实基线，再用可证伪假设收敛。",
        "category": "diagnosis",
        "tags": ["triage", "debug", "evidence"],
        "source": "forge-think built-in",
        "steps": [
            "建立事实基线：区分已证实事实、直接观察、推断和未知项；补齐影响范围、时间线、近期变更、系统归属和现有证据。",
            "把症状映射到当前系统的派生链、关键入口、关键路由、数据流和所有权；优先检查最能解释影响范围的关系，而不是从局部症状猜起。",
            "列出并排序可证伪假设；每项说明支持证据、反证、最低成本验证方式、预期信号和验证风险。",
            "基于证据选择下一步最小且可回滚的动作；明确权限、数据安全、变更窗口和必须升级给人工的边界。",
            "输出当前结论、未证实假设、恢复或验收证据，以及应回写到架构资料、监控或本 SOP 的经验。",
        ],
    },
    {
        "name": "decision-under-constraints",
        "description": "在约束、风险和不确定性下比较方案，并把关键决策收敛为可执行结论。",
        "category": "decision",
        "tags": ["decision", "architecture", "risk"],
        "source": "forge-think built-in",
        "steps": [
            "明确决策目标、成功标准、不可违反的约束、影响对象和仍缺失的信息；区分必须由用户或业务方确认的事项。",
            "列出可行方案及其关键假设；按收益、实现成本、运行成本、风险、可逆性和与现有系统的契合度比较。",
            "以反方视角攻击当前最优方案：寻找失败场景、边界条件、依赖变化和被低估的迁移或维护成本。",
            "在现有证据下给出推荐方案、放弃方案的理由、最小验证动作、回滚边界和需要确认的决策点。",
            "把结论整理成可执行下一步，并记录哪些新证据会触发重新决策。",
        ],
    },
    {
        "name": "agent-first-application-design",
        "description": "用输入工程、上下文工程、工具契约和评估闭环设计可靠的 LLM 驱动应用。",
        "category": "llm-application",
        "tags": ["agent", "architecture", "context-engineering", "evaluation"],
        "source": "forge-think built-in",
        "steps": [
            "先判断是否真的需要 agent：列出任务中的复杂判断、非结构化信息、例外处理和多步行动；同时说明哪些子任务用单次模型调用、检索或确定性工作流更简单可靠，避免为 agent 而 agent。",
            "定义每个 agent 节点的输入契约：目标、成功标准、用户意图、当前状态、业务规则、可信数据源、新鲜度要求和必须保留的历史决策；区分必需上下文、按需上下文和禁止/低信号上下文，并标明来源与责任方。",
            "设计上下文工程策略：以最小高信号 token 集为目标，确定哪些信息在启动时注入，哪些只保留文件路径/ID/查询引用并在运行时 just-in-time 检索，怎样压缩长历史、写结构化记忆、清除过期工具输出，以及上下文不足时如何检索、提问或停止。",
            "设计 agent-computer interface：把数据读取、行动、编排工具分开；每个工具明确适用边界、无歧义参数、权限/可逆性、错误语义和 token-efficient 的结构化返回。检查工具是否重叠、是否会诱导错误选择，以及工具结果怎样被转译为下一步可消费的上下文。",
            "设计执行闭环与安全边界：明确感知、规划、行动、验证、恢复和退出条件；划定持久化状态、确定性程序、guardrails、人工确认和高风险动作的边界，并说明失败阈值或不可逆动作何时必须升级。",
            "建立评估闭环：从真实用户任务和失败案例构造 capability 与 regression 任务集；为结果、环境状态、工具调用轨迹和成本/轮次选择合适的确定性、模型或人工 grader；定义上线前基线、上线后监控和将新失败回写到 eval/SOP 的机制。",
            "输出最小可行架构：agent 与确定性组件分工、输入/上下文流、工具契约、状态与权限边界、评估计划、成本预算，以及仍未证实且会改变设计的关键假设。",
        ],
    },
)

# ───────────────────────── 数据模型 ─────────────────────────

class Lens(BaseModel):
    role: str = Field(..., description="带立场的角色,如 '偏执的性能工程师'")
    instruction: str = Field(..., description="具体改造指令,如 '压测复杂度并优化'")


class ForgeStartInput(BaseModel):
    task: str = Field(..., description="淬炼的核心任务/目标(必填)", min_length=1)
    mode: Literal["seq", "chain", "deliberate"] = Field(
        ...,
        description="淬炼模式:seq=模型自主控步(传 role;不自动 done,要 forge_stop 收尾);"
                    "chain=自定义步骤链(传 steps 或 sop;跑完自动 done)。"
                    "用 chain 时若不确定有无合适 SOP,先调 forge_sop_list 查库,再决定传 sop 还是自定义 steps;"
                    "deliberate=多视角 lens 迭代(传 baseline_role+lenses;跑完自动 done)")
    role: Optional[str] = Field(None, description="[seq] 角色,可选,默认'资深专家'")
    steps: Optional[List[str]] = Field(None, description="[chain] 步骤指令序列(与 sop 二选一)")
    sop: Optional[str] = Field(None, description="[chain] 已存 SOP 的 name,从库加载 steps(与 steps 二选一)。不知道名字时必须先调 forge_sop_list 查候选,再把匹配的 name 传入此字段")
    baseline_role: Optional[str] = Field(None, description="[deliberate·必填] 生成基线初稿的角色")
    lenses: Optional[List[Lens]] = Field(None, description="[deliberate·必填] 审查视角数组")

    @model_validator(mode="after")
    def _check_mode_params(self):
        if self.mode == "chain" and not (self.steps or self.sop):
            raise ValueError("chain 模式必须提供 steps 或 sop")
        if self.mode == "deliberate" and not (self.baseline_role and self.lenses):
            raise ValueError("deliberate 模式必须提供 baseline_role 和 lenses")
        return self


class ForgeStepInput(BaseModel):
    session_id: str = Field(..., description="forge_start 返回的 session_id")
    output: str = Field(..., description="host 这一回合生成的产出文本", min_length=1)


class ForgeSessionInput(BaseModel):
    session_id: str = Field(..., description="session_id")


class ForgeSopSaveInput(BaseModel):
    name: str = Field(..., description="SOP 名(唯一标识,同名覆盖=编辑)", min_length=1)
    steps: List[str] = Field(..., description="步骤指令序列(至少 1 步)", min_length=1)
    description: str = Field(..., description="一句话说明这个 SOP 干啥(供 list/路由识别)", min_length=1)
    category: Optional[str] = Field(None, description="主分类,如 frontend/backend/devops(供 list 过滤)")
    tags: Optional[List[str]] = Field(None, description="多标签,如 ['debug','console'](供 list 过滤)")
    project: Optional[str] = Field(None, description="关联项目(可选)")
    source: Optional[str] = Field(None, description="来源说明,如 '踩坑提炼' '公司规定'(可选)")


class ForgeSopListInput(BaseModel):
    category: Optional[str] = Field(None, description="按主分类过滤")
    tag: Optional[str] = Field(None, description="按标签过滤")
    q: Optional[str] = Field(None, description="关键词模糊匹配 name/description")


class ForgeSopNameInput(BaseModel):
    name: str = Field(..., description="SOP 名")


# ───────────────────────── session 存储 ─────────────────────────

_SESSIONS: dict = {}  # session_id -> session dict(内存,快速响应)


def _persist_session(session: dict) -> None:
    """落盘到 ~/.forge-mcp/sessions/<id>.json(防掉线/重启丢失)。走 home,不依赖 host cwd。"""
    os.makedirs(SESSION_DIR, exist_ok=True)
    path = os.path.join(SESSION_DIR, f"{session['session_id']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(session, f, ensure_ascii=False, indent=2)


def _load_persisted_sessions() -> None:
    """启动时从磁盘加载历史 session 回内存(server 重启后可续可复盘,无需专门 tool)。"""
    if not os.path.isdir(SESSION_DIR):
        return
    for fn in os.listdir(SESSION_DIR):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(SESSION_DIR, fn), "r", encoding="utf-8") as f:
                s = json.load(f)
            _SESSIONS[s["session_id"]] = s
        except Exception:
            continue


_load_persisted_sessions()  # 模块加载(即 server 启动)时自动恢复历史 session


# ───────────────────────── SOP 库(文件 IO,热重载) ─────────────────────────

def _sop_path(name: str) -> str:
    return os.path.join(SOP_DIR, f"{name}.json")


def _sop_load(name: str) -> Optional[dict]:
    path = _sop_path(name)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _sop_write(sop: dict) -> None:
    os.makedirs(SOP_DIR, exist_ok=True)
    with open(_sop_path(sop["name"]), "w", encoding="utf-8") as f:
        json.dump(sop, f, ensure_ascii=False, indent=2)


def _install_default_sops() -> None:
    """首次启动安装内置 SOP；之后永不覆盖用户的编辑或删除。"""
    if os.path.exists(DEFAULT_SOPS_MARKER):
        return
    os.makedirs(SOP_DIR, exist_ok=True)
    now = datetime.now().isoformat(timespec="seconds")
    for template in DEFAULT_SOPS:
        if _sop_load(template["name"]) is not None:
            continue
        _sop_write({**template, "created": now, "updated": now})
    with open(DEFAULT_SOPS_MARKER, "w", encoding="utf-8") as f:
        f.write(now)


_install_default_sops()


# ───────────────────────── step 构造 ─────────────────────────

def _build_steps(params: ForgeStartInput) -> List[dict]:
    """按 mode 构造待执行 step 序列。每 step = {role, instruction, type}。"""
    if params.mode == "chain":
        steps = params.steps
        if params.sop:
            sop = _sop_load(params.sop)
            if not sop:
                raise ValueError(f"SOP '{params.sop}' 不存在;先 forge_sop_save 创建,或 forge_sop_list 查看")
            steps = sop.get("steps")
            if not steps:
                raise ValueError(f"SOP '{params.sop}' 没有 steps")
        if not steps:
            raise ValueError("chain 模式必须提供 steps 或 sop")
        return [{"role": "专家", "instruction": s, "type": "step"} for s in steps]

    if params.mode == "deliberate":
        seq = [{"role": params.baseline_role,
                "instruction": "基于你的专业能力,针对任务直接产出一份高质量初步方案/文本,不要废话。",
                "type": "baseline"}]
        seq += [{"role": l.role, "instruction": l.instruction, "type": "lens"} for l in params.lenses]
        return seq

    if params.mode == "seq":
        role = params.role or "资深专家"
        return [{"role": role,
                 "instruction": "推演一步(可推翻重来、可改主意)。直接给出这一步的思考。",
                 "type": "seq"}]
    raise ValueError(f"未知 mode: {params.mode}")


def _step_response(session: dict, step: Optional[dict], done: bool, current_text: str = "") -> str:
    resp = {
        "session_id": session["session_id"],
        "status": session["status"],
        "index": session["index"],
        "total": "?" if session["mode"] == "seq" else len(session["steps"]),
        "done": done,
        "current_text": current_text,
    }
    if step and not done:
        resp["next_step"] = {"role": step["role"], "instruction": step["instruction"], "type": step["type"]}
        resp["guidance"] = (
            f"请以「{step['role']}」的身份,对上面的 current_text 执行:{step['instruction']}。"
            f"完成后把结果作为 output 调用 forge_step。"
        )
    else:
        resp["guidance"] = "淬炼完成。可调用 forge_review 复盘全过程。"
    return json.dumps(resp, ensure_ascii=False, indent=2)


# ───────────────────────── tools ─────────────────────────

HELP_TEXT = """forge-think — 多步对抗淬炼引擎(9 个 tool)

【先做什么】第一次使用或任务较复杂时，先读本手册，再按任务选择模式。用户说「用 forge-think」「使用 forge-think」「开启 forge-think」「开炉」「启动锻造」时调用；技术选型、代码审查、根因排查、方案打磨等需要多步收敛的任务也应主动调用。
(注:MCP 不能用 /slash 命令触发,只能自然语言 + host 自动判断。一步能想清或纯事实查询时不要用。)

【三模式 · 先选对模式】
  · seq        根因未知、路径未成形、可能随时推翻假设 → 同一专家沿发现逐步探索；不会自动 done，够了就 forge_stop。
  · chain      已有固定步骤、业务方法论或 SOP → 每一步基于上一轮完整产出继续更新；全部完成自动 done。
  · deliberate 已有计划/设计/结论，需要不同立场挑漏洞并收敛 → 基线 + 多个 lens 依次改写；全部完成自动 done。

【低摩擦内部 Grill】
  grill-me 式用户访谈的低摩擦替代是 deliberate，不是 seq。对现有上下文、代码和约束已足够的问题，用 lens 自问自答：需求质询者 → 魔鬼代言人 → 落地审查员 → 信息边界审查员。
  最后一位必须遵守:只能用已有证据收敛；无法确认且会改变方案的事项列为「需要用户确认」，不得猜测。
  业务优先级、预算、用户偏好、授权范围、外部事实或不可逆决策只能由用户确认，必须明确提问，不能用内部 Grill 替代。

【怎样构造高质量 lens】
  每个 lens = 立场鲜明的 role + 具体可执行的 instruction。role 负责从哪个角度审，instruction 负责如何改写上一轮完整文本。
  例:安全审查员(找注入/越权/数据泄露并修正) → 性能工程师(分析复杂度和资源占用并优化) → 极简 reviewer(删过度设计)。
  deliberate 的 baseline_role 和 lenses 是本次调用的临时圆桌，任意数量、任意顺序，当前不会自动保存。

【SOP 库 · 业务定向方法论】
  LLM 容易按训练中最常见的通用范式输出，脱离真实系统、历史演化和组织约束，产生看似合理但中庸或同质化的结论。
  SOP 不是固定答案或普通 checklist，而是把团队已验证的真实业务思路写进判断顺序:哪些关系优先、哪些证据可信、如何形成假设、怎样控制风险、何时升级、如何验收。它用项目事实打破通用范式输出，不替模型回答。
  当前 SOP 是持久化的 steps[]，只用于 chain: forge_start(mode="chain", sop="名字", task=...)。它不保存/加载 deliberate 的 lenses。
  首次启动会安装 3 条可编辑的默认 SOP: evidence-first-triage(证据驱动分诊)、decision-under-constraints(约束下决策)、agent-first-application-design(输入契约、上下文工程、工具契约和 eval)。之后绝不覆盖用户修改或删除。
  适合沉淀:数据库故障分诊、发布事故处置、合规审查、LLM-first 架构设计等固定业务/实践流程。
  · forge_sop_save   创建/更新(同名覆盖=编辑)
  · forge_sop_list   按 category/tag/关键词找候选 SOP
  · forge_sop_get    运行或编辑前查看完整步骤
  · forge_sop_delete 删除不可恢复的 SOP

【与 Agent Team 的关系】
  forge-think 不替代 Agent Team。team 负责拆任务、并行探索和独立交叉验证；任一 agent 或 coordinator 都可调用 forge-think 做本地收敛。
  同类任务的多个成员可共享同一条 chain SOP，避免重复摸索；某个成员需要方案审查时可另外开一次临时 deliberate 圆桌。

【成本和持久化】
  server 不调用 LLM。每一步仍由 host 生成，因此每多一步仍有正常模型成本；但 SOP 可减少重新摸索、试错、无效工具调用和 team 返工，从而降低总任务成本。
  session 持久化不消耗额外模型 token:server 只把 host 已输出的文本写入 ~/.forge-mcp/sessions/，不会为存档再生成一次文本或调用模型。保留 session_id，重启后可继续推进或 forge_review 复盘。

【调用协议】
  1. forge_start(按模式传参) → 取得 session_id 和 next_step。
  2. 以 next_step.role 的身份执行 next_step.instruction；deliberate/chain 后续步必须针对 current_text 输出完整更新文本。
  3. forge_step(session_id, output) 提交；循环至 done。seq 需要主动 forge_stop。
  4. forge_review 用于查看完整 trace；从本次成功/失败中提炼可复用流程时，用 forge_sop_save 沉淀。
"""


@mcp.tool(
    name="forge_help",
    annotations={"title": "forge-think 使用手册", "readOnlyHint": True, "destructiveHint": False,
                 "idempotentHint": True, "openWorldHint": False},
)
async def forge_help() -> str:
    """forge-think 使用手册:触发词、何时用、三模式决策指南、SOP 库、调用流程。

    用 forge-think 前先调这个,拿到完整指引。无参数,直接调用。
    """
    return HELP_TEXT


@mcp.tool(
    name="forge_start",
    annotations={"title": "启动淬炼 session", "readOnlyHint": False, "destructiveHint": False,
                 "idempotentHint": False, "openWorldHint": False},
)
async def forge_start(params: ForgeStartInput) -> str:
    """启动一个淬炼 session,返回第一步要做什么。

    ⚠️ 第一次用 forge-think 先调 forge_help 拿手册(触发词 + 三模式决策指南 + SOP 库 + 流程)。

    三种模式(按 mode 选,各需不同参数,传错在 input 校验阶段就被拒):
    - **seq**(模型自主控步):开放式探索,模型自己决定步数。
      传 role(可选,默认"资深专家")。**永不自动 done**,host 够了就调 forge_stop。
      适用:选型权衡、根因推演、想一步改一步。
    - **chain**(自定义步骤链):固定管线,每步对上一步产出操作。
      传 steps(自定义步骤)或 sop(已存 SOP 的 name,从库加载)。跑完所有 step **自动 done**。
      适用:固定流程、跑沉淀的 SOP。
    - **deliberate**(多视角 lens 迭代):多角色依次打磨同一份产出。
      传 baseline_role + lenses(都必填)。baseline + 所有 lens 跑完 **自动 done**。
      适用:代码审查、方案打磨、多对立立场。

    host 拿到 next_step(角色+指令)后,自己以该身份生成产出,调 forge_step 提交,循环到 done。

    Returns:
        JSON:session_id + 第一步 next_step(role/instruction/type)+ guidance
    """
    try:
        steps = _build_steps(params)
    except ValueError as e:
        return f"Error: {e}"

    sid = uuid.uuid4().hex[:12]
    session = {
        "session_id": sid,
        "task": params.task,
        "mode": params.mode,
        "steps": steps,
        "trace": [],
        "index": 0,
        "status": "running",
    }
    _SESSIONS[sid] = session
    _persist_session(session)
    return _step_response(session, steps[0], done=False)


@mcp.tool(
    name="forge_step",
    annotations={"title": "提交产出并推进", "readOnlyHint": False, "destructiveHint": False,
                 "idempotentHint": False, "openWorldHint": False},
)
async def forge_step(params: ForgeStepInput) -> str:
    """提交 host 这一回合的产出,记入 trace,推进到下一步。

    - chain/deliberate:推进到下一个 step;全部完成返回 done=true
    - seq:永不自动 done(模型自主控步),host 想停就调 forge_stop
    """
    s = _SESSIONS.get(params.session_id)
    if not s:
        return f"Error: 未知 session_id '{params.session_id}'"
    if s["status"] == "stopped":
        return "Error: session 已停止,无法继续"
    if s["status"] == "done":
        return "Error: session 已完成,无需再推进"

    cur_step = s["steps"][0] if s["mode"] == "seq" else s["steps"][s["index"]]
    s["trace"].append({
        "role": cur_step["role"],
        "instruction": cur_step["instruction"],
        "output": params.output,
    })
    s["index"] += 1
    _persist_session(s)

    if s["mode"] == "seq":
        return _step_response(s, s["steps"][0], done=False, current_text=params.output)

    if s["index"] < len(s["steps"]):
        return _step_response(s, s["steps"][s["index"]], done=False, current_text=params.output)

    s["status"] = "done"
    _persist_session(s)
    return _step_response(s, None, done=True, current_text=params.output)


@mcp.tool(
    name="forge_review",
    annotations={"title": "复盘淬炼过程", "readOnlyHint": True, "destructiveHint": False,
                 "idempotentHint": True, "openWorldHint": False},
)
async def forge_review(params: ForgeSessionInput) -> str:
    """返回 session 的所有中间步(角色/指令/产出)+ 当前状态。用于复盘。"""
    s = _SESSIONS.get(params.session_id)
    if not s:
        return f"Error: 未知 session_id '{params.session_id}'"
    return json.dumps({
        "session_id": s["session_id"], "task": s["task"], "mode": s["mode"],
        "status": s["status"], "steps_done": len(s["trace"]), "trace": s["trace"],
    }, ensure_ascii=False, indent=2)


@mcp.tool(
    name="forge_stop",
    annotations={"title": "终止淬炼 session", "readOnlyHint": False, "destructiveHint": False,
                 "idempotentHint": False, "openWorldHint": False},
)
async def forge_stop(params: ForgeSessionInput) -> str:
    """强制终止 session(状态置 stopped)。已完成的步保留,可后续 forge_review 复盘。"""
    s = _SESSIONS.get(params.session_id)
    if not s:
        return f"Error: 未知 session_id '{params.session_id}'"
    s["status"] = "stopped"
    _persist_session(s)
    return json.dumps({
        "session_id": s["session_id"], "status": s["status"], "steps_done": len(s["trace"]),
        "final_output": s["trace"][-1]["output"] if s["trace"] else None,
        "note": "已停止。可用 forge_review 复盘全部中间步。",
    }, ensure_ascii=False, indent=2)


# ───────────────────────── SOP 库 tools(文件 IO,热重载) ─────────────────────────

@mcp.tool(
    name="forge_sop_save",
    annotations={"title": "创建/更新 SOP", "readOnlyHint": False, "destructiveHint": False,
                 "idempotentHint": False, "openWorldHint": False},
)
async def forge_sop_save(params: ForgeSopSaveInput) -> str:
    """创建或更新一个 SOP(同名覆盖 = 编辑)。把踩坑经验/公司规定/项目约束沉淀成可复用流程。

    何时用:你(host)从对话上下文识别出一条值得复用的流程(用户说"把这个流程存成 SOP"),
    提取 steps 后调本 tool。同名已存在则更新(保留 created,刷 updated)。

    Returns:
        JSON:action(创建/更新)+ name + steps_count + 可跑的提示
    """
    existing = _sop_load(params.name)
    now = datetime.now().isoformat(timespec="seconds")
    sop = {
        "name": params.name,
        "steps": params.steps,
        "description": params.description,
        "category": params.category,
        "tags": params.tags or [],
        "project": params.project,
        "source": params.source,
        "created": existing["created"] if existing else now,
        "updated": now,
    }
    _sop_write(sop)
    return json.dumps({
        "action": "更新" if existing else "创建",
        "name": params.name,
        "steps_count": len(params.steps),
        "category": params.category,
        "tags": params.tags or [],
        "note": f"可用 forge_start(mode='chain', sop='{params.name}', task=...) 跑这个 SOP",
    }, ensure_ascii=False, indent=2)


@mcp.tool(
    name="forge_sop_list",
    annotations={"title": "列出 SOP", "readOnlyHint": True, "destructiveHint": False,
                 "idempotentHint": True, "openWorldHint": False},
)
async def forge_sop_list(params: ForgeSopListInput) -> str:
    """列出 SOP(支持 category/tag/q 过滤)。用于选 SOP 时缩小范围,再由 host 选最合适的跑。

    每次实时扫盘(热重载:刚 save 的立刻出现)。返回摘要(name/description/category/tags/steps_count)。
    """
    if not os.path.isdir(SOP_DIR):
        return json.dumps({"count": 0, "sops": [], "note": "还没有 SOP,先用 forge_sop_save 创建"}, ensure_ascii=False)

    sops = []
    for fn in os.listdir(SOP_DIR):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(SOP_DIR, fn), "r", encoding="utf-8") as f:
                sops.append(json.load(f))
        except Exception:
            continue

    def match(s):
        if params.category and s.get("category") != params.category:
            return False
        if params.tag and params.tag not in (s.get("tags") or []):
            return False
        if params.q:
            ql = params.q.lower()
            if ql not in s.get("name", "").lower() and ql not in s.get("description", "").lower():
                return False
        return True

    filtered = [s for s in sops if match(s)]
    summary = [{
        "name": s["name"], "description": s.get("description", ""),
        "category": s.get("category"), "tags": s.get("tags", []),
        "steps_count": len(s.get("steps", [])), "updated": s.get("updated"),
    } for s in filtered]
    return json.dumps({"count": len(summary), "sops": summary}, ensure_ascii=False, indent=2)


@mcp.tool(
    name="forge_sop_get",
    annotations={"title": "查看 SOP 详情", "readOnlyHint": True, "destructiveHint": False,
                 "idempotentHint": True, "openWorldHint": False},
)
async def forge_sop_get(params: ForgeSopNameInput) -> str:
    """查看某 SOP 完整内容(含 steps)。编辑前先 get 看现状。"""
    sop = _sop_load(params.name)
    if not sop:
        return f"Error: SOP '{params.name}' 不存在"
    return json.dumps(sop, ensure_ascii=False, indent=2)


@mcp.tool(
    name="forge_sop_delete",
    annotations={"title": "删除 SOP", "readOnlyHint": False, "destructiveHint": True,
                 "idempotentHint": False, "openWorldHint": False},
)
async def forge_sop_delete(params: ForgeSopNameInput) -> str:
    """删除一个 SOP(不可恢复)。"""
    path = _sop_path(params.name)
    if not os.path.isfile(path):
        return f"Error: SOP '{params.name}' 不存在"
    os.remove(path)
    return json.dumps({"action": "deleted", "name": params.name}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
