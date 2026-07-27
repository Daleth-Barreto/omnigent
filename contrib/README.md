# Omnigent Contrib & Isolated Extension Packages

This directory contains optional, third-party, and community-driven integrations and tool wrappers for Omnigent.

## Architectural Principle: Process & Package Isolation

All extensions in `contrib/` follow a strict isolation pattern:
1. **Independent Packages:** Each subdirectory is a standalone Python package with its own `pyproject.toml` and virtual environment. None of these packages are added to Omnigent's core runtime dependencies.
2. **Subprocess MCP Execution:** When an AI agent utilizes an extension from `contrib/`, Omnigent spawns the extension as an independent Model Context Protocol (MCP) server process (e.g., via stdio).
3. **Fault Tolerance:** If a third-party CLI or service breakingly changes its API, crashes, or suffers dependency conflicts, the failure is isolated to that specific MCP process and reported cleanly to the agent as a tool error—never crashing the core Omnigent orchestrator or session.

## Available Extensions

| Package | Type | Description |
|---|---|---|
| `mcp-testsprite` | MCP Server | Stdio MCP wrapper around the [TestSprite CLI](https://github.com/testsprite/testsprite-cli) for automated E2E testing in cloud environments. |
