---
title: "the common anatomy of open-source agents"
date: 2026-11-02
tags: [application-architecture]
---

Codex, Gemini CLI, OpenCode, Goose, OpenHands, Hermes Agent, OpenClaw, OpenWorker, Open WebUI, and LibreChat look like different products. Some are terminal coding agents. Some are web chat platforms. Some are always-on assistants reachable from Slack, Telegram, or WhatsApp. Their current public docs show this spread clearly: [Codex exposes an app-server, SDK, and CLI](https://developers.openai.com/blog/codex-as-a-platform); Gemini CLI is a terminal agent; OpenCode runs a TUI over a local server; OpenHands provides agents, conversations, tools, workspaces, events, and an agent server; LibreChat and Open WebUI expose agents and tools in self-hosted chat UIs; OpenClaw and Hermes focus on gateways, messaging channels, memory, and scheduled automations.

But underneath, they share the same shape.

If you have built a basic LangChain-style agent, you know the core loop: call the model, run the tools it asks for, return tool results, call the model again. Production agents keep that loop, but surround it with sessions, approvals, context management, storage, streaming, recovery, access control, and process boundaries.

A useful way to read these systems is not by language or framework, but by responsibilities.

## What we did

We compared the ten products by responsibilities. A responsibility is a unit of work the system has to do: send the request to the model, run a tool, persist the conversation. A module is a unit of code: a crate, a package, a directory. Each team cuts and names its modules its own way.

We wrote one list of 154 responsibilities and read each product's code at a pinned commit. We started from a blank page on the shape of the modules. We had no reference architecture and no template of boxes to fill.

This distinctive way to compare architectures lets us __discover__ each team's decisions: where it drew a boundary, what it kept together, what it split apart. The method has three advantages:
- Products with very different code become comparable.
- Every claim points to a file.
- When separate teams keep two responsibilities together, that is a sign.

Then we clustered the responsibilities. Two responsibilities belong together when the products keep them in the same module. We named the clusters, ranked them by importance, and drew the twenty-nine most important. The grouping and the positions come from the code. The names, the ranking and the cut at twenty-nine are our judgment.

![The twenty-nine clusters of responsibilities: the main line from the user to the model runs down the middle, the tool side branches left from Turn control, the prompt side right]({{ '/assets/images/agent-clusters.svg' | relative_url }})


That provides a wider glance. The rest of this article follows the main flow only: the path of one prompt from the user to the model and back, with the branch for tools. 

## The main line

For one user prompt, most agent systems follow this path:

```text
User
→ Front end
→ Gateway
→ Access control
→ Session runtime
→ Session store
→ Turn control
→ Prompt assembly
→ Context management
→ Provider adapter
→ Model transport
→ LLM
```

Then, if the model calls tools, the flow branches into tool dispatch, approval and execution.


```
    User
     │
     ├──► Front end ───────┐
     ├──► Chat channels ───┤
     └──► Agent protocols ─┤
               ┌───────────▼────────────┐
               │ Gateway                │
               └───────────┬────────────┘
               ┌───────────▼────────────┐
               │ Access control         │
               └───────────┬────────────┘
               ┌───────────▼────────────┐
               │ Session runtime        │
               └───────────┬────────────┘
               ┌───────────▼────────────┐
               │ Session store          │
               └───────────┬────────────┘
               ┌───────────▼────────────┐       ┌──────────────────┐
               │ Turn control           ├──────►│ Tool dispatch    │
               │                        │◄──┐   └────────┬─────────┘
               └───────────┬────────────┘   │   ┌────────▼─────────┐
               ┌───────────▼────────────┐   │   │ Approval policy  │
               │ Prompt assembly        │   │   └────────┬─────────┘
               └───────────┬────────────┘   │   ┌────────▼─────────┐
               ┌───────────▼────────────┐   │   │ Built-in tools   │
               │ Context management     │   │   │ Process executor │
               └───────────┬────────────┘   │   │ MCP client       │
               ┌───────────▼────────────┐   │   │ Sub-agent        │
               │ Provider adapter       │   │   └────────┬─────────┘
               └───────────┬────────────┘   └────────────┘ tool results
               ┌───────────▼────────────┐
               │ Model transport        │
               └───────────┬────────────┘
                           ▼
                          LLM
```

A **turn** is the work caused by one user message. A **round** is one model call plus the tool calls it produces. One turn may contain many rounds.

The simple agent loop lives in **Turn control**. Everything else exists to make that loop usable in a real product.

## Turn control is the center

Turn control is the engine. It decides what happens next:

1. Build the prompt.
2. Send it to the model.
3. Stream text and tool calls back to the user.
4. Run approved tools.
5. Add tool results to the history.
6. Call the model again.
7. Stop when the model gives a final answer.

That sounds small, but it owns many hard cases.

It must notice when the provider cut off the output and ask the model to continue. It must stop loops that are burning time or tokens. It must handle retries, rate limits, cancellations, user interrupts, and empty model replies. It must emit events like “text delta,” “tool started,” “approval needed,” “tool finished,” and “turn done.”

Those events are what every UI renders. A terminal, web app, IDE extension, phone client, or Slack bot may look different, but they are usually watching the same stream.

## Sessions make the loop durable

A toy agent can keep state in memory. A real agent needs a session runtime and a session store.

The **session store** keeps the transcript: user messages, model messages, tool calls, tool results, approvals, errors, usage, and sometimes branches. Many systems store this as an append-only log or event stream. Others store message rows in a database. Either way, the store must answer a simple question: “What exact history should the next model call see?”

The **session runtime** owns live execution. It makes sure one conversation has only one active turn at a time. It lets different conversations run in parallel. It buffers events so a client can reconnect. It may queue a new user message while the current turn is still running, or inject it as a steering message at a safe point.

This is where basic agent code turns into infrastructure.

If the process crashes mid-turn, the runtime has to recover. A model may have streamed half a tool call. A shell command may have started. A tool result may not have been written back. A pending approval may still be waiting for a user.

The common invariant is: **before the next model call, the history must be valid.** If the model called a tool, there must be a tool result, even if that result is an error saying the previous run was interrupted.

## Prompt assembly is more than a system prompt

Prompt assembly builds the model input for every round.

It includes the base instructions, agent persona, tool guidance, current date, OS, working directory, editor state, files, attachments, memory, and project instructions such as `AGENTS.md` or `GEMINI.md`.

Most systems also have some version of:

- **Agent definitions**: named agents with their own prompt, model, tools, and permissions.
- **Modes**: plan, build, read-only, auto, guarded, full access.
- **Memory**: facts or preferences carried across conversations.
- **Skills**: procedures the model can load when needed.
- **Hooks**: code that runs before or after steps.
- **Nudges**: reminders added during a turn, such as budget left or files changed.

This is why “the prompt” is not one string. It is a constructed view of many sources.

The hard part is keeping it small enough.

## Context is a budget

Every system eventually hits the context window. The prompt, instructions, history, tool schemas, tool results, memory, attachments, and room for the answer all compete for the same budget.

The common strategy is:

1. Estimate tokens before the call.
2. Measure actual usage after the call.
3. Keep recent user intent verbatim.
4. Compress or drop older history.
5. Bound tool output before it enters the prompt.
6. Keep the cached prefix stable when possible.

Tool results are often the biggest source of context growth. A shell command can print thousands of lines. A web fetch can return a whole page. A file search can dump too much source code. Good systems return a preview to the model and keep the full output somewhere else, giving the model a path or handle if it needs more.

Many systems also hide rarely used tools until needed. [LibreChat calls this deferred tools](https://www.librechat.ai/docs/features/agents): the model gets a search tool instead of every MCP schema up front. Open WebUI has a similar tool-search mechanism for large MCP setups.

The design lesson is simple: context management is not one summarizer. It is a set of gates around everything that enters the next model call.

## Tools all pass through the same checkpoint

Tools are where agents become dangerous and useful.

A tool may be a safe function, a file edit, a shell command, a browser action, an HTTP call, an MCP tool, provider-hosted web search, or a whole sub-agent. [MCP itself is an open specification](https://developers.openai.com/plugins/concepts/mcp-server) for connecting AI clients to external tools and data; MCP servers can expose tools, resources, prompts, and instructions, and clients discover tool schemas before the model calls them.

Most systems split tool work into four stages.

First, **tool dispatch** decides which tool schemas the model sees. After the model responds, it validates tool arguments, repairs malformed calls when possible, routes each call, runs safe calls in parallel, and turns failures into tool results the model can read.

Second, **approval policy** decides whether a call may run. This is separate from execution. Approval can use modes, rules, remembered grants, risk classifiers, model judges, admin policy, or human review. [Codex app-server, for example, supports approval flows](https://learn.chatgpt.com/docs/app-server?translationFallback=ko-KR) for command execution and file changes; OpenAI’s Codex safety writeup also describes auto-review for some sandbox-boundary requests.

Third, **execution** runs the call. Built-in tools run in the harness process. Shell tools use a process executor. MCP tools run in another process or remote server. [Open WebUI’s docs](https://docs.openwebui.com/features/extensibility/plugin/tools/) make this distinction clear: native tools, workspace tools, MCP/HTTP tools, OpenAPI tools, and terminal integrations have different execution boundaries and risks.

Fourth, **result shaping** bounds the output before it returns to the prompt.

Approval and sandboxing are complementary. A sandbox limits damage after a tool starts. Approval decides whether it starts at all.

## Sub-agents are child turns

Sub-agents look fancy, but architecturally they are simple.

From the parent’s point of view, a sub-agent is a tool call. From the system’s point of view, it is a child session with its own turn control, prompt, tools, permissions, budget, and final result.

The important rule is that a child usually gets **less power than the parent**, not more. It may have fewer tools, read-only access, a smaller budget, no ability to spawn more agents, and stricter approval behavior.

Most products keep sub-agent depth shallow. That avoids runaway trees, confusing approval paths, and summaries of summaries. When teams need more structure, they tend to add boards, workflows, or handoff graphs beside the parent-child tree rather than allowing arbitrary recursion.

## Process shape changes the product

The same architecture can run in very different process layouts.

```
 1. ONE PROCESS                        2. A LOCAL SERVER AND ITS CLIENTS

 ┌────────────────────────────┐        ┌─────────────┐   ┌──────────────────┐
 │ Front end, agent loop,     │        │ Terminal UI │   │ Desktop app, IDE,│
 │ tools                      │        └──────┬──────┘   │ web app, phone   │
 └─────────────┬──────────────┘               │          └───────┬──────────┘
 ┌─────────────▼──────────────┐               └────────┬─────────┘
 │ Child processes:           │           ┌────────────▼───────────┐
 │ shells, MCP servers        │           │ Server or daemon:      │
 └────────────────────────────┘           │ sessions, turns, tools │
                                          └────────────┬───────────┘
                                          ┌────────────▼───────────┐
                                          │ Child processes,       │
                                          │ sandbox                │
                                          └────────────────────────┘


 3. REPLICAS WITH SHARED STATE         4. EXECUTION ELSEWHERE

          ┌──────────┐                 ┌────────────────────────┐
          │ Browsers │                 │ Server: the model loop │
          └────┬─────┘                 └─────┬──────────────────┘
      ┌────────┴────────┐                    ├──► Container per conversation
 ┌────▼──────┐    ┌─────▼─────┐              │
 │ Replica 1 │    │ Replica N │              ├──► Remote executor or dev box
 └────┬──────┘    └─────┬─────┘              │
      ├─────────────────┤                    └──► The user's device or browser
      │                 │
 ┌────▼───────────┐ ┌───▼───────────┐
 │ Redis: pub/sub,│ │ Database:     │
 │ stream buffers,│ │ conversations │
 │ jobs           │ └───────────────┘
 └────────────────┘
```

### 1. One process

A terminal agent can put the UI, session, turn loop, and tools in one process. This is simple, fast, and easy to debug. It is good for scripts and CI.

The cost is that the turn often dies with the process. Reconnection usually means re-reading the stored transcript, not resuming a live stream.

### 2. Local server plus clients

Many coding agents use a local server. The server owns sessions, tools, permissions, and execution. The terminal, web UI, desktop app, IDE extension, or mobile client attaches to it.

[OpenCode documents this explicitly](https://docs.opencode.ai/docs/server/): running `opencode` starts a TUI and a server, where the TUI is a client; the server exposes an OpenAPI endpoint and supports multiple clients. Codex app-server similarly exists for product integrations that need authentication, conversation history, approvals, and streamed agent events.

This gives you background turns, reconnection, multiple front ends, and a clean language boundary between UI and engine. It costs you a protocol, auth, lifecycle management, pairing, versioning, and more debugging complexity.

### 3. Replicas with shared state

Web chat platforms need many users and multiple server replicas. They put conversations in a database and live streams or jobs in shared infrastructure such as Redis.

This shape is about tenancy, permissions, roles, quotas, sharing, retention, and admin policy. The agent loop is still there, but the hard parts move toward access control and operations.

### 4. Execution elsewhere

Some systems keep the model loop central but run tools elsewhere: a Docker container, remote dev machine, cloud worker, browser, phone, or user laptop.

[OpenHands makes this separation explicit](https://github.com/OpenHands/docs/blob/main/sdk/arch/overview.mdx) with local, container, and remote workspaces, plus an agent server exposing REST and WebSocket endpoints for conversations, files, bash, events, desktop, and VS Code integrations.

This gives isolation and access to the right files or devices. It costs provisioning time, remote latency, credential handling, and more failure modes.

## Different products emphasize different boxes

The shared anatomy stays the same, but each kind of product puts weight in different places.

**Coding agents** care most about workspace tools, shell execution, file diffs, language-server feedback, sandboxing, approvals, and restoring files when a conversation rewinds. Their hardest problems are tool safety and context from large repos.

**Chat-channel assistants** care about gateways, sender identity, routing, scheduled work, unattended turns, and approvals over Slack, Telegram, Discord, or email. [Hermes describes a single gateway process](https://github.com/attentiondotnet/hermes-agent) for Telegram, Discord, Slack, WhatsApp, Signal, and CLI; OpenClaw describes a self-hosted gateway that connects chat apps to coding agents.

**Self-hosted chat platforms** care about users, roles, tenants, shared agents, admin policy, files, MCP configuration, and long-term storage. [LibreChat’s agent docs](https://www.librechat.ai/docs/features/agents) show this platform shape: web search, file search, file context, artifacts, MCP, deferred tools, programmatic tool calling, memory, approvals, marketplace, scheduled chats, and an agents API.

**Agent SDKs and canvases** care about composability. They expose conversations, events, tool systems, workspaces, model interfaces, and server APIs so other products can build on top.

## What to decide when building your own

If you are going beyond a basic agent loop, these are the design questions that matter:

1. **Where does a conversation live?** In memory, JSONL, SQLite, Postgres, Mongo, or an event log?
2. **Who owns a live turn?** One process, a local daemon, a replica, or a remote worker?
3. **Can two turns run in one conversation?** Usually no. Enforce that with a lock, lease, or writer fence.
4. **What can tools do without asking?** Define modes, rules, grants, and admin floors.
5. **What is your execution boundary?** Host process, child process, sandbox, container, remote machine, or browser?
6. **How does context shrink?** Summaries, pruning, tool-result previews, deferred tools, or provider compaction?
7. **What happens after a crash?** Resume, fail orphaned tools, or ask the user to retry.
8. **What events does the UI need?** Stream text, tool activity, approvals, cost, usage, errors, and final state.
9. **Can agents delegate?** If yes, make sub-agents child turns with smaller permissions.
10. **What must never depend on the model remembering?** Put those rules in code around the loop.

The core loop is still the heart: model, tools, results, repeat. But the system around it is what makes an agent usable. The mature products all discovered the same surrounding organs: sessions, stores, prompts, context managers, adapters, transports, tool dispatchers, approval engines, executors, sub-agents, logs, and process boundaries.

That is the common anatomy.
