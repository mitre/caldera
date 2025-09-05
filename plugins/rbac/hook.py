"Edited"

from aiohttp import web
from aiohttp_jinja2 import template
from app.service.auth_svc import check_authorization
from pathlib import Path
import json
from aiohttp_security import authorized_userid

name = "RBAC"
description = "Role Based Access Control"
address = "/plugin/rbac/gui"

async def _forbid_student(request):
    try:
        u = await authorized_userid(request)
    except Exception:
        u = None
    if u == 'student':
        raise web.HTTPForbidden(text="RBAC plugin is not available for your role.")

async def enable(services):
    app = services.get("app_svc").application
    r = Rbac(services)

    # GUI
    app.router.add_route("GET",  "/plugin/rbac/gui", r.gui)

    # Users + Allowed-IDs API (per-user)
    app.router.add_route("GET",    "/api/rbac/users", r.get_users)            # list known users
    app.router.add_route("GET",    "/api/rbac/allowed", r.get_allowed)        # ?username=alice
    app.router.add_route("PUT",    "/api/rbac/allowed", r.put_allowed)        # body: {username, ability_ids}
    app.router.add_route("POST",   "/api/rbac/allowed", r.post_allowed)       # body: {username, ability_ids}
    app.router.add_route("DELETE", "/api/rbac/allowed/{id}", r.delete_allowed)# ?username=alice

    # Minimal state + persistence
    plugin_root = Path(__file__).resolve().parent
    state_file = plugin_root / "state" / "allowed.json"
    state_file.parent.mkdir(exist_ok=True)

    app["rbac_state_file"] = str(state_file)
    # Initialize mapping: username -> set(ability_id)
    app["rbac_allowed_map"] = {}
    if state_file.exists():
        try:
            data = json.loads(state_file.read_text() or "{}")
            # New format
            users_map = data.get("users")
            if isinstance(users_map, dict):
                app["rbac_allowed_map"] = {u: set(map(str, ids or [])) for u, ids in users_map.items()}
            else:
                # Back-compat: old single list for student
                old = set(map(str, data.get("allowed_student_abilities", [])))
                app["rbac_allowed_map"] = {"student": old}
        except Exception:
            app["rbac_allowed_map"] = {}
    else:
        state_file.write_text(json.dumps({"users": {}}, indent=2))


class Rbac:
    def __init__(self, services):
        self.app = services.get("app_svc").application
        self.auth_svc = services.get("auth_svc")
        self.data_svc = services.get("data_svc")

    # ---------- helpers ----------
    def _allowed_map(self) -> dict:
        return self.app.setdefault("rbac_allowed_map", {})

    def _allowed_for(self, username: str) -> set:
        m = self._allowed_map()
        if username not in m:
            m[username] = set()
        return m[username]

    def _state_file(self) -> Path:
        return Path(self.app["rbac_state_file"])

    def _persist(self):
        payload = {"users": {u: sorted(list(ids)) for u, ids in self._allowed_map().items()}}
        tmp = self._state_file().with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2))
        tmp.replace(self._state_file())

    # ---------- GUI ----------
    @check_authorization
    @template("rbac.html")
    async def gui(self, request):
        await _forbid_student(request)
        abilities = await self.data_svc.locate("abilities", match={})
        # Normalize to simple {id,name}
        options = []
        for a in abilities:
            aid = getattr(a, "ability_id", None) or (a.get("ability_id") if isinstance(a, dict) else None)
            nm  = getattr(a, "name", None)       or (a.get("name")       if isinstance(a, dict) else None)
            if aid:
                options.append({"id": str(aid), "name": (nm or str(aid))})
        options.sort(key=lambda x: x["name"].lower())

        return {
            "ability_count": len(options),
            "ability_options": options,
            # initial render doesn't pre-select; client will fetch per-user
            "allowed_ids": set(),
        }

    # ---------- APIs ----------
    @check_authorization
    async def get_users(self, request):
        await _forbid_student(request)
        # prefer auth_svc user list
        users = sorted(list(self.auth_svc.user_map.keys()))
        return web.json_response({"users": users})

    @check_authorization
    async def get_allowed(self, request):
        await _forbid_student(request)
        username = request.rel_url.query.get("username")
        if not username:
            raise web.HTTPBadRequest(text="username is required")
        return web.json_response({"username": username, "allowed": sorted(self._allowed_for(username))})

    @check_authorization
    async def put_allowed(self, request):
        await _forbid_student(request)
        data = await request.json()
        username = (data.get("username") or "").strip()
        if not username:
            raise web.HTTPBadRequest(text="username is required")
        ids = set(map(str, data.get("ability_ids", [])))
        s = self._allowed_for(username)
        s.clear()
        s.update(ids)
        self._persist()
        return web.json_response({"ok": True, "username": username, "allowed": sorted(self._allowed_for(username))})

    @check_authorization
    async def post_allowed(self, request):
        await _forbid_student(request)
        data = await request.json()
        username = (data.get("username") or "").strip()
        if not username:
            raise web.HTTPBadRequest(text="username is required")
        ids = set(map(str, data.get("ability_ids", [])))
        self._allowed_for(username).update(ids)
        self._persist()
        return web.json_response({"ok": True, "username": username, "allowed": sorted(self._allowed_for(username))})

    @check_authorization
    async def delete_allowed(self, request):
        await _forbid_student(request)
        ability_id = request.match_info.get("id", "")
        username = request.rel_url.query.get("username", "").strip()
        if not username:
            raise web.HTTPBadRequest(text="username is required")
        self._allowed_for(username).discard(str(ability_id))
        self._persist()
        return web.json_response({"ok": True, "username": username, "allowed": sorted(self._allowed_for(username))})
