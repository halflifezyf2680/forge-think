# forge-think

[English](README.md) | [中文](README_zh-CN.md)

> Structured multi-step orchestration for MCP agents: adversarial lenses, reusable SOP workflows, and persistent traces.

Force complex tasks through a rigorous, multi-step refinement process instead of letting a single, one-shot LLM response decide the outcome. `forge-think` provides three primary orchestration modes for MCP agents: Open Exploration, Business SOPs, and Roundtable Review.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Why forge-think?

Strong models don't lack the ability to "think one step further". What they lack when facing complex problems is the correct reasoning path, adversarial reviews from different standpoints, and the ability to persist proven decision trees for reuse. When relying on single-shot prompts, a model's entire reasoning process naturally regresses to the mean, generating generic paradigms.

`forge-think` acts as a lightweight, external orchestration layer to fix this:

- **Open Exploration (`seq`)**: When the root cause is unknown, step-by-step debugging allows the agent to gather evidence and pivot its hypotheses on the fly.
- **Business SOPs (`chain`)**: Encode your team's verified decision trees into Standard Operating Procedures. Prevent the LLM from falling back on generic paradigms by forcing it to respect specific architectural constraints.
- **Roundtable Review (`deliberate`)**: Apply adversarial lenses (e.g., Security, Performance, Minimalist) to successively critique and rewrite the proposed solution until it reaches a solid consensus.
- **Persistent Traces**: Every step leaves a trace. You can resume the process even if the connection drops or the server restarts.

**Note**: The server itself doesn't make any LLM calls. It strictly manages orchestration, state, and persistence, relying on your Host Agent (like Claude Desktop) for the actual generation.

## Getting Started

```bash
git clone https://github.com/halflifezyf2680/forge-think.git
cd forge-think
pip install -r requirements.txt
```

Requires Python 3.10+. Configure the local stdio server in your MCP host. Example configurations are in [`examples/`](examples/):

- Claude Desktop: [`claude_desktop_config.json`](examples/claude_desktop_config.json)
- OpenCode: [`opencode_config.json`](examples/opencode_config.json)

Once configured, simply prompt your host: "Use forge-think" or "Start forge-think". For complex tasks, ask the host to call `forge_help` first to get the operational manual.

## Out-of-the-Box SOPs

On first launch, `forge-think` installs three editable default SOPs in `~/.forge-mcp/sops/`. 

| SOP | Scenario | Hardcoded Reasoning Path |
|---|---|---|
| `evidence-first-triage` | Incidents, exceptions | Establish a factual baseline first, form falsifiable hypotheses, then choose the lowest-risk action. |
| `decision-under-constraints` | Architecture, tech trade-offs | Explicitly list constraints, attack the candidate solution, and converge to a decision. |
| `agent-first-application-design` | LLM app design | Full methodology from input contracts to eval loops. |

## How is this different from `sequentialthinking`?

Tools like the official `sequentialthinking` MCP simply allow the model to break down its own thoughts step-by-step. However, if the model lacks your specific business context, thinking longer just produces **"logically rigorous generic nonsense."** 

`forge-think` doesn't just ask the model to think more; it forces the model onto the rails of your actual business logic by injecting strict external constraints (adversarial personas and team-verified SOPs).

*(For full documentation on Lenses, Rules vs SOPs, and Dev instructions, please refer to the Chinese documentation [README_zh-CN.md](README_zh-CN.md))*

## License

[MIT](LICENSE)
