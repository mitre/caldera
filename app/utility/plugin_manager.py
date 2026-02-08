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
    
    CORE_PLUGINS = ['stockpile', 'sandcat', 'manx', 'magma']
    
    def __init__(self, services, plugins_dir: str = 'plugins', allow_build=False):
        self.services = services
        self.plugins_dir = Path(plugins_dir)
        self.loaded_plugins: Dict[str, object] = {}
        self.enabled_plugins: Dict[str, object] = {}
        self.available_plugins: List[str] = []
        self.allow_build = allow_build 

        self._discover_plugins()
    
    async def initialize(self):
        """Initialize required infrastructure plugins."""
        if "magma" in self.available_plugins:
            await self.enable_plugin("magma")

    def _discover_plugins(self):
        """Discover available plugins without loading them."""
        if not self.plugins_dir.exists():
            return
        
        for plugin_path in self.plugins_dir.iterdir():
            if plugin_path.is_dir() and (plugin_path / '__init__.py').exists():
                if plugin_path.name not in self.available_plugins:
                    self.available_plugins.append(plugin_path.name)

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

    async def enable_plugin(self, plugin_name: str, build_gui=False) -> bool:
        if plugin_name in self.enabled_plugins:
            return False

        module = self.load_plugin(plugin_name)
        if not module:
            return False
        
        await self._install_requirements_if_needed(plugin_name)
        
        restart_required = False
        if build_gui:
            restart_required = await self._build_plugin_gui_if_needed(plugin_name)

        try:
            hook = importlib.import_module(f'plugins.{plugin_name}.hook')
        except ModuleNotFoundError:
            print(f"[PluginManager] Hook not found for {plugin_name}, skipping.")
            return restart_required

        self.enabled_plugins[plugin_name] = module

        return restart_required

    async def _build_plugin_gui_if_needed(self, plugin_name):
        gui_path = f"plugins/{plugin_name}/gui"

        if not os.path.isdir(gui_path):
            return False

        if not glob.glob(f"{gui_path}/**/*.vue", recursive=True):
            return False

        print(f"[plugin_manager] Building GUI for {plugin_name}")

        await asyncio.to_thread(
            subprocess.run,
            ["node", "prebundle.js"],
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

    def load_core_plugins(self):
        """Load only core plugins needed for basic operation."""
        for plugin in self.CORE_PLUGINS:
            if plugin in self.available_plugins:
                self.load_plugin(plugin)
    
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

        await asyncio.to_thread(
            subprocess.run,
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
            check=True
        )
