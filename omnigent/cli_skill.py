"""CLI command group for searching, installing, listing, and removing Omnigent skills and tools."""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from importlib import resources
from pathlib import Path
from typing import Any, Optional

import click
import yaml
from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)
console = Console()


def _load_registry(registry_source: Optional[str] = None) -> dict[str, Any]:
    """Load the skills registry JSON from a URL, local path, or fallback to built-in resources."""
    source = registry_source or os.environ.get("OMNIGENT_SKILLS_REGISTRY_URL") or os.environ.get("OMNIGENT_SKILLS_REGISTRY_PATH")
    
    if source:
        if source.startswith("http://") or source.startswith("https://"):
            try:
                with urllib.request.urlopen(source, timeout=10) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except Exception as exc:
                raise click.ClickException(f"Failed to load remote skills registry from {source}: {exc}")
        
        local_path = Path(source).resolve()
        if local_path.exists():
            try:
                return json.loads(local_path.read_text("utf-8"))
            except Exception as exc:
                raise click.ClickException(f"Failed to parse local skills registry {local_path}: {exc}")
        else:
            raise click.ClickException(f"Specified skills registry path does not exist: {local_path}")
            
    try:
        ref = resources.files("omnigent.resources").joinpath("skills_registry.json")
        return json.loads(ref.read_text(encoding="utf-8"))
    except Exception as exc:
        raise click.ClickException(f"Failed to load built-in skills registry: {exc}")


@click.group("skill")
def skill() -> None:
    """Manage, search, install, and remove Omnigent skills and MCP tools."""
    pass


@skill.command("search")
@click.argument("query", required=False, default="")
@click.option("--json", "as_json", is_flag=True, help="Output search results in JSON format.")
@click.option("--registry", "registry_source", help="Override path or URL for the skills registry.")
def search_skills(query: str, as_json: bool, registry_source: Optional[str]) -> None:
    """Search the skills registry for tools, packages, or agent skills."""
    registry = _load_registry(registry_source)
    skills = registry.get("skills", [])
    
    query_lower = query.lower() if query else ""
    results = []
    for entry in skills:
        name = entry.get("name", "").lower()
        desc = entry.get("description", "").lower()
        tags = [str(t).lower() for t in entry.get("tags", [])]
        
        if not query_lower or query_lower in name or query_lower in desc or any(query_lower in t for t in tags):
            results.append(entry)
            
    if as_json:
        click.echo(json.dumps(results, indent=2))
        return
        
    if not results:
        console.print(f"[yellow]No skills found matching query: '{query}'[/yellow]")
        return
        
    table = Table(title=f"Omnigent Skills Registry ({len(results)} matches)")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Description", style="white")
    table.add_column("Tags", style="green")
    
    for item in results:
        table.add_row(
            item.get("name", ""),
            item.get("type", ""),
            item.get("description", ""),
            ", ".join(item.get("tags", []))
        )
    console.print(table)


@skill.command("list")
@click.option("--agent", "-a", type=click.Path(exists=True, dir_okay=False, path_type=Path), help="List tools wired into an agent's config.yaml.")
@click.option("--json", "as_json", is_flag=True, help="Output in JSON format.")
@click.option("--registry", "registry_source", help="Override path or URL for the skills registry.")
def list_skills(agent: Optional[Path], as_json: bool, registry_source: Optional[str]) -> None:
    """List available skills in the registry or configured tools in an agent."""
    if agent:
        try:
            data = yaml.safe_load(agent.read_text("utf-8")) or {}
            tools = data.get("tools", {})
            results = [{"name": k, "config": v} for k, v in tools.items()]
            if as_json:
                click.echo(json.dumps(results, indent=2))
            else:
                table = Table(title=f"Wired Tools in {agent}")
                table.add_column("Tool Name", style="cyan", no_wrap=True)
                table.add_column("Type", style="magenta")
                table.add_column("Command / URL", style="white")
                for name, cfg in tools.items():
                    t_type = cfg.get("type", "unknown") if isinstance(cfg, dict) else "unknown"
                    cmd = cfg.get("command", "") or cfg.get("url", "") if isinstance(cfg, dict) else str(cfg)
                    table.add_row(name, t_type, str(cmd))
                console.print(table)
        except Exception as exc:
            raise click.ClickException(f"Failed to read agent config {agent}: {exc}")
        return

    registry = _load_registry(registry_source)
    skills = registry.get("skills", [])
    if as_json:
        click.echo(json.dumps(skills, indent=2))
        return
    table = Table(title="All Available Omnigent Skills & MCP Tools")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Package / Launcher", style="white")
    for item in skills:
        launcher = f"{item.get('launcher', '')} {' '.join(item.get('args', []))}".strip() or item.get("path", "")
        table.add_row(item.get("name", ""), item.get("type", ""), launcher)
    console.print(table)


@skill.command("install")
@click.argument("skill_name")
@click.option("--agent", "-a", type=click.Path(dir_okay=False, path_type=Path), help="Path to target agent's config.yaml.")
@click.option("--global", "-g", "is_global", is_flag=True, help="Record installation globally in ~/.omnigent/installed_skills.json.")
@click.option("--registry", "registry_source", help="Override path or URL for the skills registry.")
def install_skill(skill_name: str, agent: Optional[Path], is_global: bool, registry_source: Optional[str]) -> None:
    """Install or wire a skill/tool from the registry into an agent or global environment."""
    registry = _load_registry(registry_source)
    target_entry = next((s for s in registry.get("skills", []) if s.get("name", "").lower() == skill_name.lower()), None)
    if not target_entry:
        raise click.ClickException(f"Skill '{skill_name}' not found in registry. Run 'omnigent skill search' to view available skills.")

    s_type = target_entry.get("type", "mcp")
    
    if agent:
        if not agent.exists():
            raise click.ClickException(f"Target agent configuration file does not exist: {agent}")
        try:
            data = yaml.safe_load(agent.read_text("utf-8")) or {}
            if not isinstance(data, dict):
                data = {}
            if "tools" not in data or not isinstance(data["tools"], dict):
                data["tools"] = {}
                
            if s_type in ("mcp", "mcp-contrib"):
                tool_def = {
                    "type": "mcp",
                    "command": target_entry.get("launcher", "npx"),
                    "args": target_entry.get("args", []),
                }
                if "env" in target_entry:
                    tool_def["env"] = target_entry["env"]
                data["tools"][skill_name] = tool_def
            else:
                data["tools"][skill_name] = {"type": "skill", "path": target_entry.get("path", "")}
                
            agent.write_text(yaml.dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
            console.print(f"[green]Successfully wired '{skill_name}' ({s_type}) into {agent}[/green]")
        except Exception as exc:
            raise click.ClickException(f"Failed to update {agent}: {exc}")
    elif is_global or not agent:
        global_dir = Path.home() / ".omnigent"
        global_dir.mkdir(parents=True, exist_ok=True)
        global_file = global_dir / "installed_skills.json"
        
        installed = {}
        if global_file.exists():
            try:
                installed = json.loads(global_file.read_text("utf-8"))
            except Exception:
                installed = {}
        installed[skill_name] = target_entry
        global_file.write_text(json.dumps(installed, indent=2), encoding="utf-8")
        console.print(f"[green]Successfully installed '{skill_name}' to global registry manifest ({global_file})[/green]")
        console.print(f"[dim]Tip: To wire directly into an agent, use: omnigent skill install {skill_name} --agent /path/to/config.yaml[/dim]")


@skill.command("remove")
@click.argument("skill_name")
@click.option("--agent", "-a", type=click.Path(exists=True, dir_okay=False, path_type=Path), help="Path to target agent's config.yaml.")
@click.option("--global", "-g", "is_global", is_flag=True, help="Remove from ~/.omnigent/installed_skills.json.")
def remove_skill(skill_name: str, agent: Optional[Path], is_global: bool) -> None:
    """Remove a wired tool from an agent or from global installed skills."""
    removed = False
    if agent:
        try:
            data = yaml.safe_load(agent.read_text("utf-8")) or {}
            if isinstance(data, dict) and "tools" in data and isinstance(data["tools"], dict):
                if skill_name in data["tools"]:
                    del data["tools"][skill_name]
                    agent.write_text(yaml.dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
                    console.print(f"[green]Removed '{skill_name}' from {agent}[/green]")
                    removed = True
                else:
                    console.print(f"[yellow]Tool '{skill_name}' was not found in {agent}[/yellow]")
        except Exception as exc:
            raise click.ClickException(f"Failed to modify {agent}: {exc}")
            
    if is_global or not agent:
        global_file = Path.home() / ".omnigent" / "installed_skills.json"
        if global_file.exists():
            try:
                installed = json.loads(global_file.read_text("utf-8"))
                if skill_name in installed:
                    del installed[skill_name]
                    global_file.write_text(json.dumps(installed, indent=2), encoding="utf-8")
                    console.print(f"[green]Removed '{skill_name}' from global registry manifest[/green]")
                    removed = True
            except Exception as exc:
                raise click.ClickException(f"Failed to modify {global_file}: {exc}")
                
    if not removed and not agent:
        console.print(f"[yellow]Skill '{skill_name}' was not found in global installed manifest.[/yellow]")
