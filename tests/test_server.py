"""测试 forge MCP server 的状态机(直接调 tool 函数,模拟 host 驱动循环)。

不连真 MCP 协议传输(那靠 FastMCP,已成熟),只验证逻辑:
chain 跑完 → done / seq 中途 stop / review 复盘。
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import server
from server import ForgeStartInput, ForgeStepInput, ForgeSessionInput, Lens


async def main():
    # ── chain:2 步,应自动跑到 done ──
    r = await server.forge_start(ForgeStartInput(
        task="把'好用'改写成文案", mode="chain", steps=["写第一版草稿", "精简去水分"]))
    d = json.loads(r)
    sid = d["session_id"]
    print(f"[chain/start ] session={sid}  first='{d['next_step']['instruction']}'  total={d['total']}")

    r = await server.forge_step(ForgeStepInput(session_id=sid, output="草稿:我们的产品超级好用,人人爱用。"))
    d = json.loads(r)
    print(f"[chain/step 1] done={d['done']}  next='{d.get('next_step', {}).get('instruction')}'")

    r = await server.forge_step(ForgeStepInput(session_id=sid, output="精简版:十万用户的选择。"))
    d = json.loads(r)
    print(f"[chain/step 2] done={d['done']}  status={d['status']}")

    r = await server.forge_review(ForgeSessionInput(session_id=sid))
    d = json.loads(r)
    print(f"[chain/review] status={d['status']}  steps_done={d['steps_done']}  trace_len={len(d['trace'])}")
    print()

    # ── deliberate: 2 轮圆桌辩论（基线 -> 独立审查 -> 争议归纳 -> 交叉反驳 -> 总收敛统一） ──
    r = await server.forge_start(ForgeStartInput(
        task="设计高并发安全执行网关",
        mode="deliberate",
        baseline_role="首席架构师",
        lenses=[
            Lens(role="白帽黑客", instruction="找出所有越权与提权漏洞"),
            Lens(role="SRE 性能专员", instruction="排查延迟放大与内存泄漏隐患"),
        ],
        rounds=2,
    ))
    d = json.loads(r)
    sid_delib = d["session_id"]
    print(f"[deliberate/start] session={sid_delib} total={d['total']} first_role='{d['next_step']['role']}' type={d['next_step']['type']}")

    # Step 0: 基线方案
    r = await server.forge_step(ForgeStepInput(session_id=sid_delib, output="基线提案：直接使用多线程执行用户脚本，通过正则过滤危险函数。"))
    d = json.loads(r)
    print(f"[deliberate/step 0 (baseline)] done={d['done']} next_role='{d['next_step']['role']}' type={d['next_step']['type']}")

    # Step 1: 白帽黑客初审
    r = await server.forge_step(ForgeStepInput(session_id=sid_delib, output="黑客异议：正则过滤完全形同虚设，存在AST动态混淆逃逸，必须上沙箱隔离！"))
    d = json.loads(r)
    print(f"[deliberate/step 1 (critique)] done={d['done']} next_role='{d['next_step']['role']}' type={d['next_step']['type']}")

    # Step 2: SRE 初审
    r = await server.forge_step(ForgeStepInput(session_id=sid_delib, output="SRE异议：GIL锁会导致CPU打满，且多线程无法限制内存占用，会导致整机OOM。"))
    d = json.loads(r)
    print(f"[deliberate/step 2 (critique)] done={d['done']} next_role='{d['next_step']['role']}' type={d['next_step']['type']}")

    # Step 3: 主持人争议梳理
    r = await server.forge_step(ForgeStepInput(session_id=sid_delib, output="主持归纳：黑客要求硬隔离沙箱，SRE关注资源超限与性能。焦点：硬隔离带来的冷启动开销能否满足高并发？"))
    d = json.loads(r)
    print(f"[deliberate/step 3 (moderator)] done={d['done']} next_role='{d['next_step']['role']}' type={d['next_step']['type']}")

    # Step 4: 白帽黑客交叉反驳
    r = await server.forge_step(ForgeStepInput(session_id=sid_delib, output="黑客反驳：安全底线不容妥协，但可以退一步接受基于轻量级 cgroups + seccomp 的轻量容器池。"))
    d = json.loads(r)
    print(f"[deliberate/step 4 (rebuttal)] done={d['done']} next_role='{d['next_step']['role']}' type={d['next_step']['type']}")

    # Step 5: SRE 交叉对齐
    r = await server.forge_step(ForgeStepInput(session_id=sid_delib, output="SRE对齐：认可预热容器池方案，毫秒级复用可抵消容器启动开销，同时设置512M内存上限。"))
    d = json.loads(r)
    print(f"[deliberate/step 5 (rebuttal)] done={d['done']} next_role='{d['next_step']['role']}' type={d['next_step']['type']}")

    # Step 6: 首席架构师总收敛
    r = await server.forge_step(ForgeStepInput(session_id=sid_delib, output="终局统一方案：预热轻量级 seccomp 隔离沙箱池 + 512MB 硬限制 + 毫秒级复用调度。"))
    d = json.loads(r)
    print(f"[deliberate/step 6 (synthesis)] done={d['done']} status={d['status']}")

    r = await server.forge_review(ForgeSessionInput(session_id=sid_delib))
    d = json.loads(r)
    print(f"[deliberate/review] status={d['status']} steps_done={d['steps_done']} total_trace={len(d['trace'])}")
    print()

    # ── seq:跑一步就 stop(中断)──
    r = await server.forge_start(ForgeStartInput(task="推演一个开放问题", mode="seq", role="架构师"))
    d = json.loads(r)
    sid2 = d["session_id"]
    print(f"[seq/start   ] session={sid2}  total={d['total']}  first_role='{d['next_step']['role']}'")

    await server.forge_step(ForgeStepInput(session_id=sid2, output="第一步:先拆解问题的关键变量..."))
    r = await server.forge_stop(ForgeSessionInput(session_id=sid2))
    d = json.loads(r)
    print(f"[seq/stop    ] status={d['status']}  steps_done={d['steps_done']}  final={d['final_output'][:30]}...")

    r = await server.forge_review(ForgeSessionInput(session_id=sid2))
    d = json.loads(r)
    print(f"[seq/review  ] 停后仍可复盘: status={d['status']} steps_done={d['steps_done']}")
    print()

    # ── 错误处理:对已 stop 的 session 再 step ──
    r = await server.forge_step(ForgeStepInput(session_id=sid2, output="强行再推"))
    print(f"[error/已停session再step] -> {r}")
    r = await server.forge_step(ForgeSessionInput(session_id="不存在"))
    print(f"[error/未知session]        -> {r}")


asyncio.run(main())
