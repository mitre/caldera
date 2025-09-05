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

    # Allowed-IDs API
    app.router.add_route("GET",    "/api/rbac/allowed", r.get_allowed)
    app.router.add_route("PUT",    "/api/rbac/allowed", r.put_allowed)        # replace all
    app.router.add_route("POST",   "/api/rbac/allowed", r.post_allowed)       # add/merge
    app.router.add_route("DELETE", "/api/rbac/allowed/{id}", r.delete_allowed)# remove one

    # Minimal state + persistence
    plugin_root = Path(__file__).resolve().parent
    state_file = plugin_root / "state" / "allowed.json"
    state_file.parent.mkdir(exist_ok=True)

    app["rbac_state_file"] = str(state_file)
    if state_file.exists():
        try:
            data = json.loads(state_file.read_text() or "{}")
            app["rbac_allowed"] = set(map(str, data.get("allowed_student_abilities", [])))
        except Exception:
            app["rbac_allowed"] = set()
    else:
        app["rbac_allowed"] = set()
        state_file.write_text(json.dumps({"allowed_student_abilities": []}, indent=2))


class Rbac:
    def __init__(self, services):
        self.app = services.get("app_svc").application
        self.auth_svc = services.get("auth_svc")
        self.data_svc = services.get("data_svc")

    # ---------- helpers ----------
    def _allowed(self) -> set:
        return self.app.setdefault("rbac_allowed", set())

    def _state_file(self) -> Path:
        return Path(self.app["rbac_state_file"])

    def _persist(self):
        payload = {"allowed_student_abilities": sorted(self._allowed())}
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
            "allowed_ids": set(self._allowed()),
        }

    # ---------- APIs ----------
    @check_authorization
    async def get_allowed(self, request):
        await _forbid_student(request)
        return web.json_response({"allowed": sorted(self._allowed())})

    @check_authorization
    async def put_allowed(self, request):
        await _forbid_student(request)
        data = await request.json()
        ids = set(map(str, data.get("ability_ids", [])))
        self._allowed().clear()
        self._allowed().update(ids)
        self._persist()
        return web.json_response({"ok": True, "allowed": sorted(self._allowed())})

    @check_authorization
    async def post_allowed(self, request):
        await _forbid_student(request)
        data = await request.json()
        ids = set(map(str, data.get("ability_ids", [])))
        self._allowed().update(ids)
        self._persist()
        return web.json_response({"ok": True, "allowed": sorted(self._allowed())})

    @check_authorization
    async def delete_allowed(self, request):
        await _forbid_student(request)
        ability_id = request.match_info.get("id", "")
        self._allowed().discard(str(ability_id))
        self._persist()
        return web.json_response({"ok": True, "allowed": sorted(self._allowed())})
