"""FastMCP server wrapping the TestSprite CLI for automated software testing."""

from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path
from typing import List, Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP("testsprite")


async def _run_subprocess(cmd: list[str], cwd: Path, timeout: int) -> tuple[int, str, str]:
    """Run a subprocess asynchronously and return (returncode, stdout, stderr)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=float(timeout)
        )
        return (
            proc.returncode if proc.returncode is not None else -1,
            stdout_bytes.decode("utf-8", errors="replace"),
            stderr_bytes.decode("utf-8", errors="replace"),
        )
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except OSError:
            pass
        return (-1, "", f"Execution timed out after {timeout} seconds.")
    except Exception as exc:
        return (-1, "", f"Failed to execute command {cmd[0]}: {exc}")


@mcp.tool()
async def testsprite_check(cwd: str = ".") -> str:
    """
    Verifica la disponibilidad de la CLI de TestSprite e inspecciona la configuración de testing en el directorio del proyecto.

    :param cwd: Directorio del proyecto a evaluar (por defecto el directorio actual).
    :returns: Resumen del estado de TestSprite en el proyecto (binarios disponibles, archivos de configuración detectados).
    """
    target_dir = Path(cwd).resolve()
    if not target_dir.exists() or not target_dir.is_dir():
        return f"Error: El directorio especificado no existe o no es válido: {cwd}"

    npx_path = shutil.which("npx")
    testsprite_path = shutil.which("testsprite")

    status_lines = [f"=== TestSprite Status Report for: {target_dir} ==="]
    if testsprite_path:
        status_lines.append(f"[OK] CLI directa encontrada en: {testsprite_path}")
        code, out, err = await _run_subprocess([testsprite_path, "--version"], target_dir, 10)
        ver = out.strip() or err.strip()
        status_lines.append(f"     Versión: {ver}")
    elif npx_path:
        status_lines.append(f"[OK] npx encontrado en: {npx_path} (se usará @testsprite/testsprite-cli vía npx)")
    else:
        status_lines.append("[ERROR] No se encontró 'testsprite' ni 'npx' en PATH. Instale Node.js/npx para utilizar este tool.")

    config_files = ["testsprite.config.json", "testsprite.config.js", "package.json", "pytest.ini", "pyproject.toml"]
    found_configs = [f for f in config_files if (target_dir / f).exists()]
    if found_configs:
        status_lines.append(f"[INFO] Archivos de configuración/proyecto detectados: {', '.join(found_configs)}")
    else:
        status_lines.append("[INFO] No se encontraron archivos de configuración de testing estándar en la raíz.")

    return "\n".join(status_lines)


@mcp.tool()
async def testsprite_run(
    cwd: str = ".",
    command: str = "test",
    args: Optional[List[str]] = None,
    timeout_seconds: int = 300,
) -> str:
    """
    Ejecuta un comando de la CLI de TestSprite (ej. 'test', 'generate', 'status') en el directorio del proyecto para crear o verificar pruebas.

    :param cwd: Directorio raíz donde se ejecutará TestSprite.
    :param command: Subcomando de TestSprite a ejecutar ('test', 'generate', etc.). Por defecto 'test'.
    :param args: Argumentos o flags adicionales opcionales para la CLI (ej. ["--verbose", "--tag", "smoke"]).
    :param timeout_seconds: Tiempo máximo en segundos antes de cancelar la ejecución.
    :returns: Salida combinada (stdout/stderr) del subproceso junto con su código de salida y estado.
    """
    target_dir = Path(cwd).resolve()
    if not target_dir.exists() or not target_dir.is_dir():
        return f"Error: El directorio especificado no existe: {cwd}"

    testsprite_bin = shutil.which("testsprite")
    npx_bin = shutil.which("npx")

    if testsprite_bin:
        cmd_list = [testsprite_bin, command]
    elif npx_bin:
        cmd_list = [npx_bin, "-y", "@testsprite/testsprite-cli@latest", command]
    else:
        return "Error: No se encontró la CLI de TestSprite ni npx en el PATH del sistema."

    if args:
        cmd_list.extend(args)

    logger.info("Running TestSprite command: %s in %s", " ".join(cmd_list), target_dir)
    code, stdout, stderr = await _run_subprocess(cmd_list, target_dir, timeout_seconds)

    out_lines = [
        f"=== TestSprite Execution: {' '.join(cmd_list)} ===",
        f"Directorio de ejecución: {target_dir}",
        f"Código de salida (return code): {code}",
        "--- STDOUT ---",
        stdout.strip() if stdout.strip() else "(vacío)",
        "--- STDERR ---",
        stderr.strip() if stderr.strip() else "(vacío)",
        "=========================================",
    ]
    return "\n".join(out_lines)


def main() -> None:
    mcp.run()
