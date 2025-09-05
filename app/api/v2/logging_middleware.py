import json
from pathlib import Path
from aiohttp import web
from aiohttp_security import api as aiosec_api

ROOT_DIR = Path(__file__).resolve().parents[3]
ALLOWED_JSON_PATH = ROOT_DIR / "plugins" / "rbac" / "state" / "allowed.json"

_ALLOWED_CACHE = {"ids": set(), "mtime": None}



def _load_allowed_from_json(path: Path) -> set:
    try:
        data = json.loads(path.read_text() or "{}")
        # Prefer new format: per-user mapping
        if isinstance(data.get("users"), dict):
            return set(map(str, (data["users"].get("student") or [])))
        # Legacy keys
        if "allowed_student_abilities" in data:
            return set(map(str, data.get("allowed_student_abilities", [])))
        if "allowed_abilities" in data:
            return set(map(str, data.get("allowed_abilities", [])))
        return set()
    except FileNotFoundError:
        return set()
    except Exception as e:
        print(f"[RBAC] read error {path}: {e}")
        return set()

def _get_allowed_cached() -> set:
    try:
        mtime = ALLOWED_JSON_PATH.stat().st_mtime
    except FileNotFoundError:
        if _ALLOWED_CACHE["mtime"] is not None:
            _ALLOWED_CACHE["ids"], _ALLOWED_CACHE["mtime"] = set(), None
        return _ALLOWED_CACHE["ids"]
    if _ALLOWED_CACHE["mtime"] != mtime:
        _ALLOWED_CACHE["ids"] = _load_allowed_from_json(ALLOWED_JSON_PATH)
        _ALLOWED_CACHE["mtime"] = mtime
    return _ALLOWED_CACHE["ids"]

def _load_plugin_blocks_from_json(path: Path) -> dict:
    """Return mapping username -> set(blocked plugin names) from JSON file."""
    try:
        data = json.loads(path.read_text() or "{}")
        out = {}
        if isinstance(data.get("plugin_blocks"), dict):
            for u, names in data["plugin_blocks"].items():
                out[str(u)] = set(map(str, names or []))
        return out
    except Exception:
        return {}


def _get_allowed_for_user(request, username: str) -> set:
    """Resolve allowed abilities for the given username using RBAC plugin state.

    Order of precedence:
    1) Live per-user map published by RBAC plugin: request.app['rbac_allowed_map'][username]
    2) Legacy single set in app for back-compat: request.app['rbac_allowed'] (only for 'student')
    3) JSON file on disk: plugins/rbac/state/allowed.json (users[username] or legacy keys)
    """
    # 1) Live per-user map
    try:
        live_map = request.app.get("rbac_allowed_map")
        if isinstance(live_map, dict):
            s = live_map.get(username)
            if isinstance(s, set):
                return s
            if s:
                return set(s)
    except Exception:
        pass

    # 2) Legacy single set (student only)
    if username == "student":
        try:
            live = request.app.get("rbac_allowed")
            if isinstance(live, set):
                return live
            if live:
                return set(live)
        except Exception:
            pass

    # 3) JSON fallback
    try:
        data = json.loads(ALLOWED_JSON_PATH.read_text() or "{}")
        if isinstance(data.get("users"), dict):
            ids = data["users"].get(username)
            if ids:
                return set(map(str, ids))
        if username == "student":
            if "allowed_student_abilities" in data:
                return set(map(str, data.get("allowed_student_abilities", [])))
            if "allowed_abilities" in data:
                return set(map(str, data.get("allowed_abilities", [])))
    except Exception:
        pass
    return set()


def _get_blocked_plugins_for_user(request, username: str) -> set:
    """Resolve blocked plugin names for the given username."""
    try:
        m = request.app.get("rbac_plugin_blocks")
        if isinstance(m, dict):
            s = m.get(username)
            if isinstance(s, set):
                return s
            if s:
                return set(s)
    except Exception:
        pass
    # fallback to JSON
    return _load_plugin_blocks_from_json(ALLOWED_JSON_PATH).get(username, set())

@web.middleware
async def log_all_requests(request, handler):
    """Dynamic RBAC enforcement in v2 API layer.

    - Blocks plugin GUIs based on per-user blocklist (from RBAC plugin state).
    - Filters abilities/adversaries lists based on per-user allowed ability IDs.
    - Admin-like users (admin, red) bypass enforcement.
    """
    user = None
    try:
        try:
            user = await aiosec_api.authorized_userid(request)
        except Exception:
            user = None

        path = request.path

        # Admin bypass
        is_admin = user and user.lower() in {"admin", "red"}

        # Dynamic plugin GUI blocking (also logs for debugging)
        if (path.startswith('/plugin/') or path.startswith('/plugins/')):
            if not user:
                # not logged-in: let auth middleware redirect
                return await handler(request)
            if not is_admin:
                parts = path.split('/')
                plugin_name = parts[2] if len(parts) > 2 else ''
                blocked = _get_blocked_plugins_for_user(request, user)
                if plugin_name:
                    print(f"[RBAC] user={user} path={path} plugin={plugin_name} blocked_list={sorted(blocked)}")
                if plugin_name and plugin_name in blocked:
                    return web.Response(text=f"Plugin '{plugin_name}' is not available for your role.", status=403, content_type='text/html')
            parts = path.split('/')
            plugin_name = parts[2] if len(parts) > 2 else ''
            blocked = _get_blocked_plugins_for_user(request, user)
            if plugin_name and plugin_name in blocked:
                if path.startswith('/plugin/') or path.startswith('/plugins/'):
                    return web.Response(text=f"Plugin '{plugin_name}' is not available for your role.", status=403, content_type='text/html')
                return web.json_response({"error": "Forbidden for your role"}, status=403)

        # Let downstream handlers run and generate their response
        resp = await handler(request)

        # Apply read filters for non-admin users
        if not is_admin and user:
            if path.startswith('/api/v2/abilities'):
                try:
                    body_text = resp.text or (resp.body.decode('utf-8', 'ignore') if getattr(resp, 'body', None) else '')
                    if body_text:
                        data = json.loads(body_text)
                        allowed = _get_allowed_for_user(request, user)

                        if isinstance(data, dict) and 'abilities' in data:
                            items = [a for a in (data.get('abilities') or []) if isinstance(a, dict) and (a.get('ability_id') or a.get('id')) in allowed]
                            return web.json_response({'total': len(items), 'abilities': items}, status=200)

                        if isinstance(data, list):
                            limited = [a for a in data if isinstance(a, dict) and (a.get('ability_id') or a.get('id')) in allowed]
                            return web.json_response(limited, status=200)
                except Exception:
                    return web.json_response({'total': 0, 'abilities': []}, status=200)

            if path.startswith('/api/v2/adversaries'):
                try:
                    body_text = resp.text or (resp.body.decode('utf-8', 'ignore') if getattr(resp, 'body', None) else '')
                    if body_text:
                        data = json.loads(body_text)
                        allowed = _get_allowed_for_user(request, user)

                        def adv_ability_ids(disp):
                            ids = []
                            if isinstance(disp, dict):
                                if disp.get('atomic_ordering'): ids += disp['atomic_ordering']
                                if disp.get('phases'):
                                    for chunk in (disp['phases'] or {}).values():
                                        ids += chunk or []
                            return [x for x in ids if x]

                        if isinstance(data, dict) and 'adversaries' in data:
                            items = [adv for adv in (data.get('adversaries') or []) if set(adv_ability_ids(adv)).issubset(allowed)]
                            return web.json_response({'total': len(items), 'adversaries': items}, status=200)
                except Exception:
                    return web.json_response({'total': 0, 'adversaries': []}, status=200)

        return resp

    except web.HTTPException:
        raise
    except Exception as e:
        print(f"[LOGGER ERR] {request.method} {request.path}: {e}")
        raise
