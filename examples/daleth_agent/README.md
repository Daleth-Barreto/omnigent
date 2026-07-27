# Daleth Agent

An example Omnigent agent that demonstrates **architectural isolation** for external AI agent tools via the Model Context Protocol (MCP). Instead of generating direct runtime library dependencies that could break the core codebase, tools run as independent MCP server processes.

Wired tools (using official MCP servers):

| Tool | MCP Server | Description |
|---|---|---|
| `context7` | `@upstash/context7-mcp` | Up-to-date documentation, migration guides, and official code examples for libraries and frameworks. |
| `playwright` | `@playwright/mcp` | Browser automation, web page navigation, accessibility snapshots, interaction, and E2E verification. |

## Prerequisites

- **Node.js** (v20+) and **`npx`** on `PATH` — both official MCP servers are published as npm packages and launched dynamically via `npx -y ...@latest`.

## Run

```bash
omnigent run examples/daleth_agent
```

## Architecture & Isolation

By encapsulating external tools as stdio-based MCP servers:
1. **Zero Core Dependency Bloat:** The core Omnigent repository and Python environment remain clean of 3rd-party automation library dependencies.
2. **Crash Isolation:** If a tool CLI changes its API or crashes, the MCP subprocess returns a clean error to the agent without bringing down the main orchestrator or session.
3. **Pluggable Architecture:** Tools can be added, updated, or removed simply by modifying the tool block in `config.yaml`.
