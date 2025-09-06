from aiohttp import web
import logging
from aiohttp_jinja2 import template
from app.service.auth_svc import check_authorization
from pathlib import Path
import json
from aiohttp_security import authorized_userid

name = "RBAC"
description = "Role Based Access Control"
address = "/plugin/rbac/gui"

async def _ensure_plugin_access(request, plugin_name: str = 'rbac'):
    """Dynamically forbid access to a plugin based on per-user block list."""
    try:
        u = await authorized_userid(request)
    except Exception:
        u = None
    # admins bypass
    if u and u.lower() in {'admin', 'red', 'blue'}:
        return
    # consult RBAC plugin block map
    app = request.app
    blocks = app.get('rbac_plugin_blocks', {}) or {}
    user_blocks = set(blocks.get(u, []) if u else [])
    if plugin_name in user_blocks:
        raise web.HTTPForbidden(text=f"Plugin '{plugin_name}' is not available for your role.")

async def enable(services):
    app = services.get("app_svc").application
    r = Rbac(services)

    # GUI
    app.router.add_route("GET",  "/plugin/rbac/gui", r.gui)

    # Users + Allowed-IDs API (per-user)
    app.router.add_route("GET",    "/api/rbac/users", r.get_users)            # list known users
    app.router.add_route("GET",    "/api/rbac/users/list", r.get_users_detailed) # list with groups
    app.router.add_route("POST",   "/api/rbac/users/register", r.register_user) # create auth user
    app.router.add_route("PUT",    "/api/rbac/users/group", r.update_user_group) # change group
    app.router.add_route("DELETE", "/api/rbac/users/{username}", r.delete_user)  # delete auth user
    app.router.add_route("GET",    "/api/rbac/allowed", r.get_allowed)        # ?username=alice
    app.router.add_route("PUT",    "/api/rbac/allowed", r.put_allowed)        # body: {username, ability_ids}
    app.router.add_route("POST",   "/api/rbac/allowed", r.post_allowed)       # body: {username, ability_ids}
    app.router.add_route("DELETE", "/api/rbac/allowed/{id}", r.delete_allowed)# ?username=alice

    # Plugin access (per-user block list)
    app.router.add_route("GET",  "/api/rbac/plugins", r.get_all_plugins)
    app.router.add_route("GET",  "/api/rbac/whoami", r.whoami)
    app.router.add_route("GET",  "/api/rbac/blocked", r.get_blocked_plugins)     # ?username=alice
    app.router.add_route("PUT",  "/api/rbac/blocked", r.put_blocked_plugins)     # body: {username, plugin_names}
    app.router.add_route("POST", "/api/rbac/blocked", r.post_blocked_plugins)    # body: {username, plugin_names}
    app.router.add_route("DELETE", "/api/rbac/blocked/{plugin}", r.del_blocked_plugin) # ?username=alice

    # Role/Group management APIs
    app.router.add_route("GET",  "/api/rbac/groups", r.get_groups)
    app.router.add_route("POST", "/api/rbac/groups", r.upsert_group)
    app.router.add_route("DELETE", "/api/rbac/groups/{name}", r.delete_group)

    # Minimal state + persistence
    plugin_root = Path(__file__).resolve().parent
    state_file = plugin_root / "state" / "allowed.json"
    state_file.parent.mkdir(exist_ok=True)

    app["rbac_state_file"] = str(state_file)
    # Initialize mapping: username -> set(ability_id)
    app["rbac_allowed_map"] = {}
    # Initialize mapping: username -> set(blocked_plugin_names)
    app["rbac_plugin_blocks"] = {}
    # Initialize mapping: group_name -> {members:[], color:'red'|'blue'}
    app["rbac_groups"] = {}
    if state_file.exists():
        try:
            data = json.loads(state_file.read_text() or "{}")
            # New format
            users_map = data.get("users")
            if isinstance(users_map, dict):
                app["rbac_allowed_map"] = {u: set(map(str, ids or [])) for u, ids in users_map.items()}
            else:
                # Back-compat: support legacy root keys
                # 1) allowed_student_abilities → student only
                old_student = set(map(str, data.get("allowed_student_abilities", [])))
                # 2) allowed_abilities (generic) → treat as student fallback
                old_generic = set(map(str, data.get("allowed_abilities", [])))
                merged = old_student or old_generic
                app["rbac_allowed_map"] = {"student": merged} if merged else {}
            # Plugin blocks in new format
            blocks_map = data.get("plugin_blocks")
            if isinstance(blocks_map, dict):
                app["rbac_plugin_blocks"] = {u: set(map(str, names or [])) for u, names in blocks_map.items()}
            # Groups map
            groups_map = data.get("groups")
            if isinstance(groups_map, dict):
                norm = {}
                for gname, g in groups_map.items():
                    if isinstance(g, dict):
                        members = set(map(str, (g.get("members") or [])))
                        color = (g.get("color") or "red").lower()
                        norm[str(gname)] = {"members": members, "color": color if color in {"red","blue"} else "red"}
                app["rbac_groups"] = norm
        except Exception:
            app["rbac_allowed_map"] = {}
            app["rbac_plugin_blocks"] = {}
            app["rbac_groups"] = {}
    else:
        state_file.write_text(json.dumps({"users": {}}, indent=2))

    # Attach RBAC UI filtering middleware at the FRONT so it takes precedence on the main app
    app.middlewares.insert(0, RbacUiMiddleware(services, app).handle)
    # Also attach to sub-apps (e.g., /api/v2) so it applies there as well
    for sub in getattr(app, '_subapps', []):
        try:
            sub.middlewares.insert(0, RbacUiMiddleware(services, app).handle)
        except Exception:
            pass


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
        payload = {
            "users": {u: sorted(list(ids)) for u, ids in self._allowed_map().items()},
            "plugin_blocks": {u: sorted(list(names)) for u, names in self.app.get('rbac_plugin_blocks', {}).items()},
            "groups": {g: {"members": sorted(list(v.get("members", []))), "color": v.get("color", "red")}
                       for g, v in self.app.get('rbac_groups', {}).items()},
        }
        tmp = self._state_file().with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2))
        tmp.replace(self._state_file())
        # Best-effort sync to testing plugin's RBAC store so Magma UI reflects changes
        try:
            testing_path = Path(__file__).resolve().parents[1] / 'testing' / 'data' / 'rbac.json'
            testing_path.parent.mkdir(parents=True, exist_ok=True)
            if testing_path.exists():
                tdata = json.loads(testing_path.read_text(encoding='utf-8') or '{}')
            else:
                tdata = {"roles": {}, "users": {}, "groups": {}}
            tdata.setdefault('roles', {})
            tdata.setdefault('users', {})
            tdata.setdefault('groups', {})
            # merge/update users' allowed_abilities from our per-user map
            for u, ids in self._allowed_map().items():
                user = tdata['users'].get(u, {"group": "red", "roles": [], "allowed_abilities": []})
                user['allowed_abilities'] = sorted(list(set(ids)))
                # ensure minimal keys exist
                user.setdefault('group', 'red')
                user.setdefault('roles', [])
                tdata['users'][u] = user
            testing_tmp = testing_path.with_suffix('.json.tmp')
            testing_tmp.write_text(json.dumps(tdata, indent=2), encoding='utf-8')
            testing_tmp.replace(testing_path)
        except Exception:
            # Non-fatal: if testing plugin not present, ignore
            pass

    # ---------- GUI ----------
    @check_authorization
    @template("rbac.html")
    async def gui(self, request):
        await _ensure_plugin_access(request, 'rbac')
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
        await _ensure_plugin_access(request, 'rbac')
        # Gather users from auth service and from stored RBAC state
        from_auth = set(self.auth_svc.user_map.keys())
        from_state = set(self._allowed_map().keys())
        users = sorted(list(from_auth.union(from_state)))
        return web.json_response({"users": users})

    @check_authorization
    async def get_users_detailed(self, request):
        await _ensure_plugin_access(request, 'rbac')
        users = []
        # from auth service (authoritative)
        for uname, u in self.auth_svc.user_map.items():
            try:
                grp = (u.permissions[0] if u.permissions else '').lower() or 'red'
            except Exception:
                grp = 'red'
            users.append({"username": uname, "group": grp})
        # include any users present only in RBAC state
        for uname in self._allowed_map().keys():
            if not any(x['username'] == uname for x in users):
                users.append({"username": uname, "group": 'red'})
        users.sort(key=lambda x: x['username'].lower())
        return web.json_response({"users": users})

    @check_authorization
    async def register_user(self, request):
        await _ensure_plugin_access(request, 'rbac')
        body = await request.json()
        username = (body.get('username') or '').strip()
        password = (body.get('password') or '').strip()
        group = (body.get('group') or '').strip().lower() or 'red'
        groups = set(map(str, (body.get('groups') or [])))
        if not username or not password:
            raise web.HTTPBadRequest(text='username and password are required')
        if group not in {'red','blue'}:
            raise web.HTTPBadRequest(text='group must be red or blue')
        if username in self.auth_svc.user_map:
            return web.json_response({"ok": False, "error": "user already exists"}, status=409)
        await self.auth_svc.create_user(username, password, group)
        # ensure user appears in our maps
        self._allowed_for(username)  # creates empty set if absent
        # Optionally add to groups
        if groups:
            gm = self._groups_map()
            for gname in groups:
                if gname not in gm:
                    gm[gname] = {"members": set(), "color": group}
                gm[gname].setdefault("members", set()).add(username)
        self._persist()
        return web.json_response({"ok": True, "username": username, "group": group, "groups": sorted(list(groups))})

    @check_authorization
    async def update_user_group(self, request):
        await _ensure_plugin_access(request, 'rbac')
        body = await request.json()
        username = (body.get('username') or '').strip()
        group = (body.get('group') or '').strip().lower()
        if not username or group not in {'red','blue'}:
            raise web.HTTPBadRequest(text='username and valid group (red/blue) are required')
        u = self.auth_svc.user_map.get(username)
        if not u:
            raise web.HTTPNotFound(text='user not found')
        # rebuild the namedtuple preserving password and setting new group
        new_u = self.auth_svc.User(username, u.password, (group, 'app'))
        self.auth_svc.user_map[username] = new_u
        return web.json_response({"ok": True, "username": username, "group": group})

    @check_authorization
    async def delete_user(self, request):
        await _ensure_plugin_access(request, 'rbac')
        username = (request.match_info.get('username') or '').strip()
        if not username:
            raise web.HTTPBadRequest(text='username required')
        # protect core accounts
        if username.lower() in {'red', 'blue', 'admin'}:
            return web.json_response({"ok": False, "error": "cannot delete core user"}, status=400)
        # remove from auth map
        self.auth_svc.user_map.pop(username, None)
        # remove from RBAC maps
        self._allowed_map().pop(username, None)
        self.app.get('rbac_plugin_blocks', {}).pop(username, None)
        # remove from groups memberships
        for g in self._groups_map().values():
            if 'members' in g and isinstance(g['members'], set):
                g['members'].discard(username)
        self._persist()
        return web.json_response({"ok": True, "username": username})

    @check_authorization
    async def get_allowed(self, request):
        await _ensure_plugin_access(request, 'rbac')
        username = request.rel_url.query.get("username")
        if not username:
            raise web.HTTPBadRequest(text="username is required")
        return web.json_response({"username": username, "allowed": sorted(self._allowed_for(username))})

    @check_authorization
    async def put_allowed(self, request):
        await _ensure_plugin_access(request, 'rbac')
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
        await _ensure_plugin_access(request, 'rbac')
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
        await _ensure_plugin_access(request, 'rbac')
        ability_id = request.match_info.get("id", "")
        username = request.rel_url.query.get("username", "").strip()
        if not username:
            raise web.HTTPBadRequest(text="username is required")
        self._allowed_for(username).discard(str(ability_id))
        self._persist()
        return web.json_response({"ok": True, "username": username, "allowed": sorted(self._allowed_for(username))})

    # ---------- Plugin access APIs ----------
    @check_authorization
    async def get_all_plugins(self, request):
        await _ensure_plugin_access(request, 'rbac')
        # list plugin directory names
        plugins_root = Path(__file__).resolve().parents[1]
        names = []
        for p in plugins_root.iterdir():
            if p.is_dir() and not p.name.startswith('.'):
                names.append(p.name)
        names.sort()
        return web.json_response({"plugins": names})

    @check_authorization
    async def whoami(self, request):
        try:
            u = await authorized_userid(request)
        except Exception:
            u = None
        return web.json_response({"username": u})

    # ---------- Groups (Roles) ----------
    def _groups_map(self) -> dict:
        return self.app.setdefault('rbac_groups', {})

    @check_authorization
    async def get_groups(self, request):
        await _ensure_plugin_access(request, 'rbac')
        # return { name: { members: [...], color: 'red'|'blue' } }
        g = self._groups_map()
        # convert sets to lists for JSON
        out = {name: {"members": sorted(list(v.get("members", []))), "color": v.get("color", "red")}
               for name, v in g.items()}
        return web.json_response({"groups": out})

    @check_authorization
    async def upsert_group(self, request):
        await _ensure_plugin_access(request, 'rbac')
        body = await request.json()
        name = (body.get('name') or '').strip()
        color = (body.get('color') or 'red').strip().lower()
        members = set(map(str, (body.get('members') or [])))
        if not name:
            raise web.HTTPBadRequest(text='name is required')
        if color not in {'red','blue'}:
            raise web.HTTPBadRequest(text='color must be red or blue')
        m = self._groups_map()
        m[name] = {"members": members, "color": color}
        # apply color to auth_svc groups for member users, if they exist
        for uname in members:
            u = self.auth_svc.user_map.get(uname)
            if u:
                self.auth_svc.user_map[uname] = self.auth_svc.User(uname, u.password, (color, 'app'))
        self._persist()
        return web.json_response({"ok": True, "group": name, "color": color, "members": sorted(list(members))})

    @check_authorization
    async def delete_group(self, request):
        await _ensure_plugin_access(request, 'rbac')
        name = request.match_info.get('name', '').strip()
        if not name:
            raise web.HTTPBadRequest(text='name required')
        self._groups_map().pop(name, None)
        self._persist()
        return web.json_response({"ok": True})

    def _plugin_blocks(self) -> dict:
        return self.app.setdefault('rbac_plugin_blocks', {})

    def _blocked_for(self, username: str) -> set:
        m = self._plugin_blocks()
        if username not in m:
            m[username] = set()
        return m[username]

    @check_authorization
    async def get_blocked_plugins(self, request):
        await _ensure_plugin_access(request, 'rbac')
        username = request.rel_url.query.get('username', '').strip()
        if not username:
            raise web.HTTPBadRequest(text='username is required')
        return web.json_response({"username": username, "blocked": sorted(self._blocked_for(username))})

    @check_authorization
    async def put_blocked_plugins(self, request):
        await _ensure_plugin_access(request, 'rbac')
        data = await request.json()
        username = (data.get('username') or '').strip()
        if not username:
            raise web.HTTPBadRequest(text='username is required')
        names = set(map(str, data.get('plugin_names', []) or []))
        s = self._blocked_for(username)
        s.clear(); s.update(names)
        self._persist()
        return web.json_response({"ok": True, "username": username, "blocked": sorted(self._blocked_for(username))})

    @check_authorization
    async def post_blocked_plugins(self, request):
        await _ensure_plugin_access(request, 'rbac')
        data = await request.json()
        username = (data.get('username') or '').strip()
        if not username:
            raise web.HTTPBadRequest(text='username is required')
        names = set(map(str, data.get('plugin_names', []) or []))
        self._blocked_for(username).update(names)
        self._persist()
        return web.json_response({"ok": True, "username": username, "blocked": sorted(self._blocked_for(username))})

    @check_authorization
    async def del_blocked_plugin(self, request):
        await _ensure_plugin_access(request, 'rbac')
        username = request.rel_url.query.get('username', '').strip()
        if not username:
            raise web.HTTPBadRequest(text='username is required')
        plugin = request.match_info.get('plugin', '')
        self._blocked_for(username).discard(plugin)
        self._persist()
        return web.json_response({"ok": True, "username": username, "blocked": sorted(self._blocked_for(username))})


class RbacUiMiddleware:
    """
    Read-filter for Caldera v2 list endpoints based on RBAC plugin per-user assignments.
    Only affects read endpoints to reflect in the Magma UI; admins are not filtered.
    """
    def __init__(self, services, app):
        self.services = services
        self.app = app
        self.data_svc = services.get('data_svc')

    async def _username(self, request):
        try:
            return await authorized_userid(request)
        except Exception:
            return None

    def _allowed(self, username: str) -> set:
        try:
            m = self.app.get("rbac_allowed_map", {}) or {}
            s = set(m.get(username, set()))
            if s:
                return s
            # Back-compat: if no per-user entry, fall back to student mapping
            # to support legacy files using allowed_abilities/allowed_student_abilities
            return set(m.get('student', set()))
        except Exception:
            return set()

    def _is_admin(self, username: str) -> bool:
        if not username:
            return False
        uname = username.lower()
        if uname in {"admin", "red"}:  # simple built-in bypass
            return True
        # allow config-based groups if available
        try:
            user = self.services.get('auth_svc').user_map.get(username)
            if user and any(p.lower() == 'admin' for p in (user.permissions or [])):
                return True
        except Exception:
            pass
        return False

    @web.middleware
    async def handle(self, request, handler):
        method = request.method.upper()
        path = request.rel_url.path
        # Dynamic plugin blocking on all /plugin/<name> and /plugins/<name> routes
        if path.startswith('/plugin/') or path.startswith('/plugins/'):
            username = await self._username(request)
            if username and not self._is_admin(username):
                parts = path.split('/')
                if len(parts) > 2:
                    plugin_name = parts[2]
                    blocks = self.app.get('rbac_plugin_blocks', {}) or {}
                    if plugin_name in set(blocks.get(username, set())):
                        # Return HTML or JSON depending on path
                        if request.path.startswith('/plugin/') or request.path.startswith('/plugins/'):
                            return web.Response(text=f"Plugin '{plugin_name}' is not available for your role.", status=403, content_type='text/html')
                        return web.json_response({"error": "Forbidden for your role"}, status=403)

        if method != 'GET' or not path.startswith('/api/v2/'):
            return await handler(request)

        username = await self._username(request)
        # If not logged in or admin, do not filter
        if not username or self._is_admin(username):
            return await handler(request)

        allowed = self._allowed(username)
        logging.info(f"[RBAC] filter user=%s path=%s allowed=%d", username, path, len(allowed))
        try:
            if path.startswith('/api/v2/abilities'):
                abilities = await self.data_svc.locate('abilities')
                filtered = [
                    a.display for a in abilities
                    if (a.display.get('ability_id') or a.display.get('id')) in allowed
                ]
                logging.info("[RBAC] abilities filtered=%d", len(filtered))
                return web.json_response({'total': len(filtered), 'abilities': filtered})

            if path.startswith('/api/v2/adversaries'):
                adversaries = await self.data_svc.locate('adversaries')

                def adv_ability_ids(disp):
                    ids = []
                    if disp.get('atomic_ordering'):
                        ids += disp['atomic_ordering']
                    if disp.get('phases'):
                        for chunk in (disp['phases'] or {}).values():
                            ids += chunk or []
                    return [x for x in ids if x]

                filtered = [
                    adv.display for adv in adversaries
                    if set(adv_ability_ids(adv.display)).issubset(allowed)
                ]
                logging.info("[RBAC] adversaries filtered=%d", len(filtered))
                return web.json_response({'total': len(filtered), 'adversaries': filtered})
        except Exception:
            # On any exception, fall back to default behavior
            pass

        return await handler(request)
