# forge-think

> Structured multi-step orchestration for MCP agents: adversarial lenses, reusable SOP workflows, and persistent traces.

让复杂任务经历一次可复盘的锤炼，而不是让一个回答决定结果。forge-think 为 MCP agent 提供三种工作方式：开放探索、业务方法论驱动的流程，以及多视角圆桌审查。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 为什么用它

强模型并不缺“多想一步”的能力；真正容易缺失的是：面对复杂问题时，是否走了正确的判断路径，是否让不同立场攻击过方案，以及是否把有效经验沉淀下来供下一次复用。

forge-think 把这些能力做成一个轻量的外部编排层：

- **开放探索**：根因和路径未知时，沿证据逐步推进、随时推翻假设。
- **业务方法论**：把公司已经验证的判断顺序固化为 SOP，不把答案写死。
- **圆桌审查**：让安全、性能、业务、极简等不同立场依次改写同一份方案。
- **可复盘过程**：每一步都留下 trace，掉线或重启后仍可继续。

server 不调用 LLM。每一步仍由当前 host agent 生成；server 只负责编排、记录和持久化。

## 开始使用

```bash
git clone https://github.com/halflifezyf2680/forge-think.git
cd forge-think
pip install -r requirements.txt
```

需要 Python 3.10+。将本地 stdio server 配置到你的 MCP host，配置文件可直接参考 [`examples/`](examples/)：

- Claude Desktop：[`claude_desktop_config.json`](examples/claude_desktop_config.json)
- OpenCode：[`opencode_config.json`](examples/opencode_config.json)

配置完成后，直接说「用 forge-think」「开启 forge-think」「开炉」或「启动锻造」。首次处理复杂任务时，让 host 先调用 `forge_help`；它提供面向 agent 的模式选择、圆桌、SOP 和 Agent Team 操作手册。

## 开箱即用的 SOP

首次启动时，forge-think 会在 `~/.forge-mcp/sops/` 安装三条可编辑的默认 SOP。它们不是演示配置，而是可立即运行、可按团队实践改写的起点。

| SOP | 适用场景 | 固化的判断方法 |
|---|---|---|
| `evidence-first-triage` | 故障、异常、争议 | 先建立事实基线，再按系统关系形成可证伪假设，最后选择最小风险动作 |
| `decision-under-constraints` | 架构、产品、技术取舍 | 显式列出约束和假设，用反方攻击候选方案，再收敛为可执行决策 |
| `agent-first-application-design` | LLM 驱动应用设计 | 从输入契约、上下文工程、工具契约、执行闭环到 eval 的完整设计方法论 |

默认 SOP 只在首次启动时安装。之后你可以查看、编辑、删除或替换；后续启动**绝不覆盖**你的修改，也不会把已删除的默认 SOP 悄悄恢复。

## 选择工作方式

| 任务状态 | 选择 | 为什么 |
|---|---|---|
| 根因未知、路径未成形、可能随时推翻假设 | `seq` | 同一专家沿发现逐步探索，允许改变方向 |
| 有固定业务/实践方法论，需要在不同具体问题上稳定复用 | `chain` + SOP | 让 agent 每次都走相同的判断路径，但根据当前证据得出不同答案 |
| 已有计划、设计或结论，需要从不同立场挑漏洞并收敛 | `deliberate` | 基线加圆桌 lenses，依次重写同一份产出 |

一步能想清或纯事实查询时，不要使用 forge-think。

## 把真实业务体系写进 SOP

### 对抗“范式匹配输出”

LLM 输出时天然倾向于从训练中最常见、最通用的范式继续生成：通用故障排查、标准三层架构、页面 + API + 规则分支、平均化的最佳实践。这在信息不足时有用，但也容易脱离真实系统、组织约束和历史演化，得到看似合理却中庸、同质化，甚至在关键处退化的结论。

SOP 的价值不在于保存“复现 → 修复 → 验证”这种通用检查清单，而在于把团队已经验证过的**真实业务思路**写进每一次推理：哪些关系优先、哪些证据可信、哪些历史包袱不能忽略、哪些约束必须先于“标准做法”考虑。它不替模型回答，而是在模型进行通用范式匹配前，给出一条更贴近现实的判断轨道。

这也是为什么一个好的 SOP 往往比继续补充泛化知识更有价值：它用项目特有的事实、经验和思维方式，打破通用答案的能力均化，让同一个模型在不同具体问题上走向更贴合业务的结论。

### 把真实体系写进判断路径

例如数据库故障分诊，泛化的数据库知识只能告诉模型慢查询、锁等待或连接池耗尽都可能发生；真正决定排查质量的，是团队已核实的系统事实：

- 订单库由哪个共享库或历史分支派生，哪些服务拥有它。
- 查询入口、`Repository/DAO`、迁移目录、路由或分片配置位于哪里。
- 哪些上游关系最能解释影响范围，哪些下游服务会受波及。
- 谁拥有反证、变更权限和升级决策权。

把这些事实写进 SOP 后，agent 面对每次不同故障都会先沿派生链、关键入口和关键路由取证，再排序假设、选择最小风险动作、判断何时升级。变化的是证据和结论，不变的是贴近真实体系的判断质量。

同一原则也适用于 LLM-first 应用设计。Rules 可以禁止某些实现，Skill 可以提供 agent 设计知识；但 SOP 能在每一次设计中持续追问：这项能力真的必须退回页面、API、规则分支或后台任务吗？是否应该由 agent 的目标、工具、状态、验证和恢复闭环承担？哪些部分仍必须保持确定性？

可靠的 LLM 应用设计不止这些架构名词。默认 SOP 还要求为每个 agent 节点定义输入契约和上下文工程策略：哪些业务规则、当前状态、可信来源和历史决策必须进入上下文；哪些只保留引用、在运行时 just-in-time 检索；如何压缩长历史、写结构化记忆、清除过期工具输出；输入不足时是检索、提问还是停止。它还要求把工具当作 agent-computer interface 设计，并从真实失败构造 capability / regression eval，验证结果、环境状态、工具轨迹和成本，而不是只检查最终文案是否“看起来不错”。

### Rules、Skills 与 SOP

| 机制 | 解决什么 | 例子 |
|---|---|---|
| Rules | 全局边界和硬约束 | 禁止直连生产、变更必须可回滚、不得泄露数据 |
| Skills | 领域知识与工具能力 | 数据库运维知识、监控工具、迁移能力 |
| SOP | 某类任务的业务定向判断方法论 | 先看哪些证据、怎样形成假设、何时升级、如何验收 |

当前 SOP 是持久化的 `steps[]`，仅由 `chain` 运行。它约束的是思考路径，不是固定答案；圆桌 lenses 则是一次 `deliberate` 调用的临时参数，当前不能保存为 SOP。

## 用圆桌做内部 Grill Me

如果你正在用 [`grill-me`](https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me)，你会熟悉它的价值：像魔鬼记者一样不断追问，把计划里没有说清的分支逼出来。但不是每个分支都值得把真人拖进一轮采访。对代码、文档、已有决策和明确约束已经能回答的问题，反复要求用户逐条作答只会制造交互疲劳。

`deliberate` 是这部分工作的低摩擦替代：让同一个 host 按不同审查立场自问自答，先消化已有上下文能够解决的质询，只把会真正改变方向、且答案只能由真人提供的事项升级给用户。它不是模拟真正独立的多 agent，而是一场可控的内部圆桌。

一个有效圆桌通常包含：

- **需求质询者**：找出未说明的目标、约束和假设，并从已有上下文补全可回答部分。
- **魔鬼代言人**：攻击最可能失败的前提、反例和被低估的代价。
- **落地审查员**：检查实施、回滚、监控、验收和维护责任。
- **信息边界审查员**：只能基于已有证据收敛；将会改变方案、但答案只能由用户提供的事项列为“需要用户确认”。

分流原则很简单：

- **已有上下文可回答**：让圆桌内部完成质询、反驳和收敛。
- **答案只能由真人提供**：业务优先级、预算、偏好、授权范围、外部事实和不可逆决策，明确列为“需要用户确认”，再提问。

这样保留 Grill Me 的质询质量，却不要求用户为每一个本可由模型和现有材料回答的问题疲于应答。

圆桌角色没有白名单。可按任务自由组合任意数量和顺序的 lenses；[`examples/lenses.json`](examples/lenses.json) 只展示其结构，并不是自动加载的固定配置。

## 在 Agent Team 中使用

forge-think 不取代 Agent Team：Team 负责拆任务、并行探索和独立交叉验证；任一成员或 coordinator 都可以调用 forge-think，先让局部结论经过收敛再交付。

同类任务的成员可共用一条 SOP。例如支付与订单两个服务发生同类发布故障时，两个 debug agent 都走同一条生产故障分诊方法论；各自使用不同证据、得出不同结论，但不会各自重新发明排查路径。某个成员需要审查修复方案时，再单独开启临时圆桌。

## 成本、持久化与边界

- 每多走一步，host 都会产生正常的模型推理成本；forge-think 不会让推理凭空免费。
- SOP 和圆桌减少的是重新摸索、试错、重复上下文、无效工具调用和 team 返工，从而降低总任务成本。
- `chain(sop=...)` 从本地 JSON 读取步骤，不调用 LLM。
- session 持久化不额外消耗模型 token：server 只写入 host 已输出的文本，不会为存档再生成一次文本。
- SOP 过时或不匹配会制造新绕路，应更新 SOP 或回到开放式 `seq` 探索。

session 和 trace 保存在 `~/.forge-mcp/sessions/`，SOP 保存在 `~/.forge-mcp/sops/`；二者都不依赖当前工作目录。保留 `session_id` 后，server 重启仍可继续推进或复盘。

## 与 Sequential Thinking 的关系

forge-think 继承并强化了结构化 / 顺序思考([Sequential Thinking](https://github.com/modelcontextprotocol/servers/tree/main/src/sequentialthinking))的思路，并新增更适合 agent 工作流的工程能力。

| | Sequential Thinking | forge-think |
|---|---|---|
| 解决的问题 | 单线推理更结构 | 多立场对抗和业务方法论 |
| 视角 | 单角色自省 | 基线加自定义 lenses 的依次审查 |
| 流程 | 每次从头推理 | SOP：定义一次，按需复用 |
| 留档 | 步骤留在上下文 | trace 落盘，掉线可续、可复盘 |

## 工具参考

| 工具 | 作用 |
|---|---|
| `forge_help` | 运行时操作手册：触发词、模式选择、SOP、圆桌和 Team 边界 |
| `forge_start` | 启动 session |
| `forge_step` | 提交本回合产出并推进 |
| `forge_review` | 复盘全部中间步 |
| `forge_stop` | 终止 session，已完成步骤仍可复盘 |
| `forge_sop_save` | 创建或更新 SOP，同名覆盖为编辑 |
| `forge_sop_list` | 列出 SOP，支持 category / tag / 关键词过滤 |
| `forge_sop_get` | 查看 SOP 详情 |
| `forge_sop_delete` | 删除 SOP |

## 为什么叫 forge

`think` / `reason` 容易直接触发模型自身更强的内部推理流程，反而降低 host 调用同名 MCP 的倾向。`forge`(锻造)避开这层竞争，用独立动作词指向反复锤打、逐步成型的外部流程。

## 开发

运行手工 smoke tests，直接调用 tool 函数验证状态机逻辑：

```bash
python tests/test_server.py   # chain 自动 done / seq 中断 / review 复盘
python tests/test_sop.py      # SOP 库 CRUD + forge_start(sop=...)
```

## License

[MIT](LICENSE)
