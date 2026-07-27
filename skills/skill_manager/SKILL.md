---
name: skill-manager
description: AI agent skill for discovering, installing, removing, and wiring Omnigent skills and MCP tools dynamically using the `omnigent skill` CLI. Use when the user wants to search for skills, install tools into an agent YAML, or manage MCP integrations.
---

# Omnigent Skill Manager

You are equipped with the **Omnigent Skill Manager** skill. Your role is to help the user discover, install, configure, and remove tools and skills dynamically without introducing direct dependency bloat into the core repository.

## When to use this skill
Use this skill whenever the user asks to:
- Search for available tools, MCP servers, or extensions (e.g., "search for browser automation skills", "what MCPs are available for testing").
- Install or wire a tool into an agent's configuration file (e.g., "install playwright into daleth_agent").
- Check what tools an agent is currently using or list the global skills catalog.
- Remove a tool from an agent or global registry.

## CLI Commands Reference

You manage skills by running terminal commands using the `omnigent skill` CLI:

### 1. Searching for Skills
To search the skills catalog by keywords (in names, descriptions, or tags):
```bash
omnigent skill search "<keyword>" --json
```
*Always use `--json` when parsing search results programmatically.*

### 2. Listing Available or Installed Skills
To list all available skills in the catalog:
```bash
omnigent skill list --json
```

To list tools currently wired into a specific agent configuration:
```bash
omnigent skill list --agent /path/to/agent/config.yaml --json
```

### 3. Installing / Wiring Skills
To wire an MCP server or skill into a specific agent configuration file (`config.yaml`):
```bash
omnigent skill install <skill_name> --agent /path/to/agent/config.yaml
```
*This command automatically updates the `tools` section of the agent's YAML file while preserving its structure.*

To install a skill globally (into `~/.omnigent/installed_skills.json`):
```bash
omnigent skill install <skill_name> --global
```

### 4. Removing Skills
To remove a tool from an agent configuration:
```bash
omnigent skill remove <skill_name> --agent /path/to/agent/config.yaml
```

To remove a globally installed skill:
```bash
omnigent skill remove <skill_name> --global
```

## Best Practices & Guidelines

1. **Verify Before Installing:** Before wiring a tool into an agent, run `omnigent skill search <skill_name> --json` to confirm the exact skill name and check its description and prerequisites.
2. **Check Agent Config Existence:** Ensure the target `config.yaml` exists before attempting installation.
3. **Handle Errors Gracefully:** If an installation fails (e.g., skill not found or syntax error in YAML), explain the error clearly to the user and suggest running `omnigent skill list` to see valid options.
4. **Architectural Isolation:** Explain to the user that installing MCP tools via `omnigent skill install` creates isolated subprocess tool boundaries, protecting their main codebase from dependency conflicts.
