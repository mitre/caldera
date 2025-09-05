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

def get_allowed_from_request(request) -> set:
    """Return allowed set for the student user.

    This middleware only applies to user == 'student' below, so it's safe
    to pull the 'student' entry from the RBAC plugin map if present.
    """
    # Prefer live per-user map published by RBAC plugin
    try:
        live_map = request.app.get("rbac_allowed_map")
        if isinstance(live_map, dict):
            s = live_map.get("student")
            if isinstance(s, set):
                return s
            if s:
                return set(s)
    except Exception:
        pass

    # Fallback to legacy single set if present
    try:
        live = request.app.get("rbac_allowed")
        if isinstance(live, set):
            return live
        if live:
            return set(live)
    except Exception:
        pass

    # Finally, read from JSON on disk (supports both new and legacy formats)
    return _get_allowed_cached()

@web.middleware
async def log_all_requests(request, handler):
    user = None

    
    try:
        try:
            user = await aiosec_api.authorized_userid(request)
        except Exception:
            user = None

        if user == 'student' and (
            request.path == '/plugin/rbac' or
            request.path.startswith('/plugin/rbac/') or
            request.path == '/api/rbac' or
            request.path.startswith('/api/rbac')
        ):
            print(f"[RBAC BLOCK] {request.method} {request.path} user={user}")
            if request.path.startswith('/plugin/'):
                return web.Response(
                    text="RBAC plugin is not available for your role.",
                    status=403,
                    content_type='text/html'
                )
            return web.json_response({"error": "Forbidden for your role"}, status=403)

        resp = await handler(request)

        if request.path.startswith("/api/v2/abilities") and user == "student":
            try:
                body_text = resp.text or (resp.body.decode("utf-8", "ignore") if getattr(resp, "body", None) else "")
                if body_text:
                    data = json.loads(body_text)
                    allowed = get_allowed_from_request(request)

                    if isinstance(data, list):
                        limited = [a for a in data if isinstance(a, dict) and a.get("ability_id") in allowed]
                        return web.json_response(limited, status=200)

                    if isinstance(data, dict):
                        aid = data.get("ability_id")
                        if aid and aid not in allowed:
                            return web.json_response({"error": "Forbidden for your role"}, status=403)
                        return web.json_response(data, status=200)
            except Exception:
                return web.json_response([], status=200)

        return resp

    except web.HTTPException:
        raise
    except Exception as e:
        print(f"[LOGGER ERR] {request.method} {request.path}: {e}")
        raise
