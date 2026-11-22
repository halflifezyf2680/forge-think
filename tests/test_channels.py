#!/usr/bin/env python3
"""端到端验证 MCP 返回通道:工具结果只走 content(text)单通道,不再有 structuredContent 重复载荷。

通过 stdio 启动真实 server 进程,用 MCP client 协议层调用,断言:
  1. result.content 恰好 1 个 TextContent,文本是合法 JSON(带 session_id)
  2. result.structuredContent 为 None(旧实现这里是 {"result": "<同一JSON字符串>"})
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server_py = Path(__file__).resolve().parents[1] / "server.py"
    params = StdioServerParameters(command=sys.executable, args=[str(server_py)])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 通道检查:所有 9 个 tool 的 outputSchema 均不应声明(单通道标志)
            tools = await session.list_tools()
            with_schema = [t.name for t in tools.tools if t.outputSchema is not None]
            assert not with_schema, f"仍声明 outputSchema 的 tool: {with_schema}"
            print(f"[list_tools] {len(tools.tools)} 个 tool,全部无 outputSchema ✓")

            # help:text 单通道
            r = await session.call_tool("forge_help", {})
            assert r.structuredContent is None, "forge_help 出现 structuredContent"
            assert len(r.content) == 1 and r.content[0].type == "text"
            print(f"[forge_help] content={len(r.content)} 块, structuredContent=None ✓")

            # start(deliberate):文本可解析为 JSON 且含 session_id
            r = await session.call_tool("forge_start", {
                "params": {
                    "task": "通道验证", "mode": "deliberate",
                    "baseline_role": "架构师",
                    "lenses": [{"role": "审查员", "instruction": "挑毛病"}],
                }
            })
            assert r.structuredContent is None, "forge_start 出现 structuredContent"
            body = json.loads(r.content[0].text)
            sid = body["session_id"]
            assert body["next_step"]["type"] == "baseline"
            print(f"[forge_start] 单通道 ✓ session={sid} next_type={body['next_step']['type']}")

            # step:推进并确认仍单通道
            r = await session.call_tool("forge_step", {"params": {"session_id": sid, "output": "基线方案 v1"}})
            assert r.structuredContent is None, "forge_step 出现 structuredContent"
            body = json.loads(r.content[0].text)
            assert body["next_step"]["type"] == "lens_critique"
            print(f"[forge_step ] 单通道 ✓ next_type={body['next_step']['type']}")

            # sop_list:JSON 返回同样单通道
            r = await session.call_tool("forge_sop_list", {"params": {}})
            assert r.structuredContent is None, "forge_sop_list 出现 structuredContent"
            body = json.loads(r.content[0].text)
            print(f"[sop_list  ] 单通道 ✓ count={body['count']}")

            # 错误路径:Error 字符串返回同样只走 text 单通道
            r = await session.call_tool("forge_step", {"params": {"session_id": "不存在", "output": "x"}})
            assert r.structuredContent is None, "错误返回出现 structuredContent"
            assert r.content[0].text.startswith("Error:")
            print(f"[error path] 单通道 ✓ '{r.content[0].text[:24]}...'")

            await session.call_tool("forge_stop", {"params": {"session_id": sid}})
            print("\n全部通过:所有返回只走 content(text) 单通道,structuredContent 已消除")


if __name__ == "__main__":
    asyncio.run(main())
