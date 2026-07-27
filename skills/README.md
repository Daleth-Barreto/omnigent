# Omnigent AI Skills

This directory contains AI-native agent skills — structured Markdown instructions and assets that teach AI agents (such as Claude Code, Copilot, or Omnigent agents) how to perform specialized tasks or workflows.

## What is an Agent Skill?

Unlike traditional code libraries, an Agent Skill is a package of procedural knowledge and prompts defined in a `SKILL.md` file with YAML frontmatter (`name` and `description`). When an AI agent detects that a user request matches a skill's description, it loads the skill's instructions into its context window and executes the documented workflow.

## Available Skills

| Skill | Directory | Description |
|---|---|---|
| `skill-manager` | `skills/skill_manager/` | Manages, searches, installs, and wires Omnigent skills and MCP tools dynamically using the `omnigent skill` CLI. |
