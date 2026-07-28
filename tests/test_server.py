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
from server import ForgeStartInput, ForgeStepInput, ForgeSessionInput


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
