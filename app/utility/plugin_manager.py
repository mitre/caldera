"""Lazy plugin loading manager."""

import importlib
from typing import Dict, List, Optional
from pathlib import Path
import os, sys
import glob
import asyncio
import subprocess


class PluginManager:
    """Manage lazy loading of CALDERA plugins."""    
    def __init__(self, services, plugins_dir: str = 'plugins'):
        self.services = services
        self.plugins_dir = Path(plugins_dir)
        self.loaded_plugins: Dict[str, object] = {}
        self.enabled_plugins: Dict[str, object] = {}
        self.available_plugins: List[str] = []
        self._discover_plugins()
        self.build_state = {
            "status": "idle",   # idle | installing | building | restarting
            "plugin": None
        }
    
    async def initialize(self):
        """Initialize required infrastructure plugins."""
        if "magma" in self.available_plugins:
            await self.enable_plugin("magma")

    def _discover_plugins(self):
        """Discover available plugins without loading them."""
        if not self.plugins_dir.exists():
            return

        for plugin_path in self.plugins_dir.iterdir():
            if not plugin_path.is_dir():
                continue

            if not (plugin_path / "hook.py").exists():
                continue

            name = plugin_path.name

            if name not in self.available_plugins:
                self.available_plugins.append(name)

    def load_plugin(self, plugin_name: str) -> Optional[object]:
        if plugin_name in self.loaded_plugins:
            return self.loaded_plugins[plugin_name]

        if plugin_name not in self.available_plugins:
            print(f"[PluginManager] Plugin '{plugin_name}' not found, skipping.")
            return None

        try:
            module = importlib.import_module(f'plugins.{plugin_name}')
            
            self.loaded_plugins[plugin_name] = module
            return module

        except Exception as e:
            print(f"Error loading plugin {plugin_name}: {e}")
            return None

    async def enable_plugin(self, plugin_name: str, build_gui=False, install_deps=False) -> bool:
        restart_required = False
        if plugin_name in self.enabled_plugins:
            return False

        module = self.load_plugin(plugin_name)
        if not module:
            return False
        try:
            self.build_state = {
                "status": "installing",
                "plugin": plugin_name
            }
            # STEP 1 — install deps
            if install_deps:
                await self._install_requirements_if_needed(plugin_name)
            
            # STEP 2 — build GUI
            if build_gui:
                self.build_state = {
                    "status": "building",
                    "plugin": plugin_name
                }
                restart_required = await self._build_plugin_gui_if_needed(plugin_name)
            self.build_state = {
                "status": "restarting",
                "plugin": plugin_name
            }
            # STEP 3 — only now commit enable state
            try:
                importlib.import_module(f'plugins.{plugin_name}.hook')
            except ModuleNotFoundError as e:
                print(f"[PluginManager] Hook not found for {plugin_name}, skipping.")
                return restart_required
        except Exception as e:
            # NOTHING has been enabled yet — safe to abort
            print(f"[PluginManager] enable failed for {plugin_name}: {e}")
            raise

        # STEP 4 — commit enable state only after successful enable
        self.enabled_plugins[plugin_name] = module

        return restart_required

    async def _build_plugin_gui_if_needed(self, plugins):
        # allow string or list
        if isinstance(plugins, str):
            plugins = [plugins]

        plugins_to_build = []

        for plugin in plugins:
            gui_path = f"plugins/{plugin}/gui"

            if not os.path.isdir(gui_path):
                continue

            if not glob.glob(f"{gui_path}/**/*.vue", recursive=True):
                continue

            plugins_to_build.append(plugin)

        if not plugins_to_build:
            return False

        print(f"[plugin_manager] Building GUI for: {', '.join(plugins_to_build)}")

        await asyncio.to_thread(
            subprocess.run,
            ["node", "prebundle.js", *plugins_to_build],
            cwd="plugins/magma",
            check=True
        )

        await asyncio.to_thread(
            subprocess.run,
            ["npm", "install"],
            cwd="plugins/magma",
            check=True
        )

        await asyncio.to_thread(
            subprocess.run,
            ["npm", "run", "build"],
            cwd="plugins/magma",
            check=True
        )

        return True

    def unload_plugin(self, plugin_name: str):
        """Unload a plugin to free memory."""
        if plugin_name in self.loaded_plugins:
            del self.loaded_plugins[plugin_name]
    
    def get_loaded_plugins(self) -> List[str]:
        """Get list of currently loaded plugins."""
        return list(self.loaded_plugins.keys())
    
    async def _install_requirements_if_needed(self, plugin_name: str):
        req_file = self.plugins_dir / plugin_name / "requirements.txt"

        if not req_file.exists():
            return

        print(f"[plugin_manager] installing requirements for {plugin_name}")
        commands = [
            # preferred: current interpreter (venv)
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-input",
                "-r",
                str(req_file)
            ],
            # fallback: system python
            [
                "python3",
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-input",
                "-r",
                str(req_file)
            ]
        ]
        last_error = None

        for cmd in commands:
            try:
                await asyncio.to_thread(
                    subprocess.run,
                    cmd,
                    check=True
                )
                print(f"[plugin_manager] requirements installed using: {cmd[0]}")
                return
            except Exception as e:
                last_error = e
                print(f"[plugin_manager] pip install failed using {cmd[0]}")

        raise RuntimeError(
            f"Failed installing requirements for {plugin_name}"
        ) from last_error
