import json
import asyncio
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[1] / 'data' / 'rbac.json'

class RbacStore:
    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = Path(path)
        self._lock = asyncio.Lock()
        self._data = {"roles": {}, "users": {}, "groups": {}}

    async def load(self):
        async with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.exists():
                self._data = json.loads(self.path.read_text(encoding='utf-8'))
            else:
                self._write()

    def _write(self):
        self.path.write_text(json.dumps(self._data, indent=2), encoding='utf-8')

    async def save(self):
        async with self._lock:
            self._write()

    # --- role ops ---
    async def list_roles(self):
        return self._data["roles"]

    async def upsert_role(self, name: str, allowed_abilities: list[str]):
        self._data["roles"][name] = {"allowed_abilities": sorted(set(allowed_abilities))}
        await self.save()

    # --- user ops ---
    async def list_users(self):
        return self._data["users"]

    async def upsert_user(self, username: str, group: str, roles: list[str], allowed_abilities: list[str] = None):
        self._data["users"][username] = {
            "group": group,
            "roles": sorted(set(roles)),
            "allowed_abilities": sorted(set(allowed_abilities or []))
        }
        await self.save()

    # --- group ops ---
    async def list_groups(self):
        return self._data["groups"]

    async def upsert_group(self, name: str, members: list[str], roles: list[str]):
        self._data["groups"][name] = {
            "members": sorted(set(members)),
            "roles": sorted(set(roles))
        }
        await self.save()

    # --- resolution ---
    async def resolve_allowed_abilities_for_user(self, username: str):
        d = self._data
        user = d["users"].get(username)
        if not user:
            return []
        # start with per-user overrides
        allowed = set(user.get("allowed_abilities", []))
        # add role abilities
        for r in user.get("roles", []):
            allowed.update(d["roles"].get(r, {}).get("allowed_abilities", []))
        # add abilities via plugin “groups”
        for g in d["groups"].values():
            if username in g.get("members", []):
                for r in g.get("roles", []):
                    allowed.update(d["roles"].get(r, {}).get("allowed_abilities", []))
        return sorted(allowed)
