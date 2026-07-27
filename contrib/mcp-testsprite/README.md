# TestSprite MCP Server (`mcp-testsprite`)

An isolated Model Context Protocol (MCP) server wrapper around the [TestSprite CLI](https://www.testsprite.com/), enabling AI agents to trigger, inspect, and verify end-to-end software tests.

## Features

- **Architectural Isolation:** Runs as a standalone stdio MCP server. TestSprite CLI dependencies (`npm`, `@testsprite/testsprite-cli`) never contaminate the Omnigent Python environment.
- **Graceful Error Handling:** Translates CLI exit codes and subprocess errors into clear, structured tool outputs for LLMs.

## Exposed Tools

| Tool | Parameters | Description |
|---|---|---|
| `testsprite_check` | `cwd` | Verifies TestSprite CLI availability and inspects test configuration in the project directory. |
| `testsprite_run` | `cwd`, `command`, `args`, `timeout_seconds` | Executes a TestSprite CLI command (e.g., `test`, `generate`, `status`) and captures output. |

## Prerequisites

- Python 3.11+
- Node.js & `npx` on PATH (to invoke `@testsprite/testsprite-cli`).

## Usage in Agent YAML

```yaml
tools:
  testsprite:
    type: mcp
    command: python
    args:
      - -m
      - mcp_testsprite
    # Alternatively, if running via uv in a separate virtual environment:
    # command: uv
    # args: ["run", "--directory", "contrib/mcp-testsprite", "python", "-m", "mcp_testsprite"]
```
