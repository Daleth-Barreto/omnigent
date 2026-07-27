# Skill Manager (`skill-manager`)

An AI-native agent skill that empowers AI assistants to dynamically manage, discover, install, and wire tools and MCP servers into Omnigent agent configurations using the `omnigent skill` CLI.

## Purpose

When users want to extend an agent with new capabilities (e.g., adding Playwright for web scraping, Context7 for documentation, or TestSprite for testing), this skill guides the AI agent to execute the appropriate CLI commands (`omnigent skill search`, `install`, `list`, `remove`) rather than manually editing complex YAML files or installing direct Python dependencies.

## Structure

- `SKILL.md`: The core instruction set and CLI command reference loaded by AI agents when the skill triggers.
