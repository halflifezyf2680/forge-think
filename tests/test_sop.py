"""测试 SOP 库 CRUD + forge_start(sop=...) 跑流程。直接调 tool 函数。"""
import asyncio
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import server
from server import (ForgeSopSaveInput, ForgeSopListInput, ForgeSopNameInput,
                    ForgeStartInput, ForgeStepInput)


async def main():
    # ── 内置 SOP：首次安装，之后不覆盖用户版本 ──
    original_sop_dir = server.SOP_DIR
    original_marker = server.DEFAULT_SOPS_MARKER
    with tempfile.TemporaryDirectory() as tmp:
        server.SOP_DIR = tmp
        server.DEFAULT_SOPS_MARKER = str(Path(tmp) / ".defaults-installed-v1")
        server._install_default_sops()
        names = {p.stem for p in Path(tmp).glob("*.json")}
        expected = {s["name"] for s in server.DEFAULT_SOPS}
        assert names == expected
        agent_design = next(s for s in server.DEFAULT_SOPS if s["name"] == "agent-first-application-design")
        agent_design_text = "\n".join(agent_design["steps"])
        assert "输入契约" in agent_design_text
        assert "上下文工程" in agent_design_text
        assert "just-in-time" in agent_design_text
        assert "评估闭环" in agent_design_text

        # 首次安装后用户的编辑不能被下一次启动覆盖。
        evidence = Path(tmp) / "evidence-first-triage.json"
        saved = json.loads(evidence.read_text(encoding="utf-8"))
        saved["description"] = "用户改写的版本"
        evidence.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        server._install_default_sops()
        assert json.loads(evidence.read_text(encoding="utf-8"))["description"] == "用户改写的版本"
        print(f"[defaults]      installed={len(names)} user_edit_preserved=True")
    server.SOP_DIR = original_sop_dir
    server.DEFAULT_SOPS_MARKER = original_marker

    # 清理可能的同名残留(delete 不存在不抛异常,返回 Error str)
    await server.forge_sop_delete(ForgeSopNameInput(name="frontend-debug"))

    # 1. 创建
    r = await server.forge_sop_save(ForgeSopSaveInput(
        name="frontend-debug",
        steps=["复现并定位", "查 console 报错", "查 network 请求", "改代码", "验证修复"],
        description="前端千团调试流程,反复踩坑提炼",
        category="frontend", tags=["debug", "console"], source="踩坑提炼"))
    d = json.loads(r)
    print(f"[save 创建]   {d['action']:4} name={d['name']} steps={d['steps_count']}")

    # 2. 同名再 save = 更新(加一步、改 desc)
    r = await server.forge_sop_save(ForgeSopSaveInput(
        name="frontend-debug",
        steps=["复现并定位", "查 console", "查 network", "查 elements", "改代码", "验证"],
        description="前端千团调试流程(更新版)",
        category="frontend", tags=["debug"]))
    d = json.loads(r)
    print(f"[save 更新]   {d['action']:4} steps={d['steps_count']}")

    # 3. list 全部
    d = json.loads(await server.forge_sop_list(ForgeSopListInput()))
    print(f"[list 全部]   count={d['count']}")

    # 4. list category
    d = json.loads(await server.forge_sop_list(ForgeSopListInput(category="frontend")))
    print(f"[list cat=frontend] count={d['count']}")

    # 5. list tag
    d = json.loads(await server.forge_sop_list(ForgeSopListInput(tag="debug")))
    print(f"[list tag=debug]   count={d['count']}")

    # 6. list 不存在的 tag
    d = json.loads(await server.forge_sop_list(ForgeSopListInput(tag="nonexistent")))
    print(f"[list tag=不存在]  count={d['count']}")

    # 7. get
    d = json.loads(await server.forge_sop_get(ForgeSopNameInput(name="frontend-debug")))
    print(f"[get]         name={d['name']} created存在={'created' in d} steps={len(d['steps'])}")

    # 8. forge_start 用 sop 跑(从库加载 steps)
    d = json.loads(await server.forge_start(ForgeStartInput(
        task="调试一个按钮点击没反应", mode="chain", sop="frontend-debug")))
    sid = d["session_id"]
    print(f"[start sop]   session={sid} total={d['total']} first='{d['next_step']['instruction']}'")

    # 跑一步看推进
    d = json.loads(await server.forge_step(ForgeStepInput(
        session_id=sid, output="复现了:点按钮无反应,console 无报错")))
    print(f"[step 1]      done={d['done']} next='{d.get('next_step', {}).get('instruction')}'")

    # 9. start 不存在的 sop
    r = await server.forge_start(ForgeStartInput(task="x", mode="chain", sop="no-such-sop"))
    print(f"[start 不存在 sop] -> {r[:50]}")

    # 10. delete + 确认
    d = json.loads(await server.forge_sop_delete(ForgeSopNameInput(name="frontend-debug")))
    print(f"[delete]      {d['action']} name={d['name']}")
    r = await server.forge_sop_get(ForgeSopNameInput(name="frontend-debug"))
    print(f"[get 已删]    -> {r}")


asyncio.run(main())
