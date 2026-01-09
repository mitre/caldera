# plugins/testing/app/rbac_mw.py
from aiohttp import web
from marshmallow import ValidationError

class RbacMiddleware:
    """
    RBAC read-filter + write-enforcement for Caldera v2 APIs.

    READ (UI lists):
      - GET /api/v2/abilities     → only abilities in user's allowed set (with 'total')
      - GET /api/v2/adversaries   → only adversaries whose abilities ⊆ allowed (with 'total')

    WRITE (execution):
      - POST /api/v2/operations
      - POST /api/v2/operations/{id}/potential-links
      Block if request implies abilities outside user's allowed set.
    """

    def __init__(self, services, store):
        self.services = services
        self.store = store
        self.auth_svc = services.get('auth_svc')
        self.data_svc = services.get('data_svc')

    @web.middleware
    async def handle(self, request, handler):
        method = request.method.upper()
        path = request.rel_url.path  # '/api/v2/abilities', '/api/v2/adversaries', etc.

        # -------------------------------
        # READ FILTERING (lists in the UI)
        # -------------------------------
        if method == 'GET' and path.startswith('/api/v2/abilities'):
            username = await self._get_username(request)
            if not username or self._is_admin(username):
                # Not logged in (auth will handle) or admin → show everything
                return await handler(request)

            allowed = set(await self.store.resolve_allowed_abilities_for_user(username))
            abilities = await self.data_svc.locate('abilities')

            filtered = [
                a.display for a in abilities
                if (a.display.get('ability_id') or a.display.get('id')) in allowed
            ]
            # IMPORTANT: include 'total' so the GUI renders the list
            return web.json_response({'total': len(filtered), 'abilities': filtered})

        if method == 'GET' and path.startswith('/api/v2/adversaries'):
            username = await self._get_username(request)
            if not username or self._is_admin(username):
                return await handler(request)

            allowed = set(await self.store.resolve_allowed_abilities_for_user(username))
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
            return web.json_response({'total': len(filtered), 'adversaries': filtered})

        # -------------------------------------------
        # WRITE ENFORCEMENT (actually scheduling work)
        # -------------------------------------------
        guard = (
            (method == 'POST' and path == '/api/v2/operations') or
            (method == 'POST' and path.endswith('/potential-links'))
        )
        if not guard:
            return await handler(request)

        username = await self._get_username(request)
        if not username or self._is_admin(username):
            # Not logged in (auth will handle) or admin bypass
            return await handler(request)

        try:
            ability_ids = await self._extract_ability_ids(request)
        except ValidationError as e:
            raise web.HTTPBadRequest(text=str(e))

        if not ability_ids:
            return await handler(request)

        allowed = set(await self.store.resolve_allowed_abilities_for_user(username))
        missing = sorted(set(ability_ids) - allowed)
        if missing:
            raise web.HTTPForbidden(text=f'RBAC: user {username} not allowed: {missing}')

        return await handler(request)

    # -----------------
    # helper functions
    # -----------------
    async def _get_username(self, request):
        """
        Pull identity from Caldera's session (set on login).
        """
        session = request.get('session') or getattr(request, 'session', None)
        if session and session.get('username'):
            return session['username']
        return None

    def _is_admin(self, username: str) -> bool:
        """
        Optional admin bypass to avoid hiding items from site admins.
        Tweak to match your environment (RBAC role/group or known usernames).
        """
        try:
            u = self.store.users.get(username, {})
            roles = set(u.get('roles', []))
            group = (u.get('group') or '').lower()
        except Exception:
            roles, group = set(), ''
        if 'admin' in roles or group == 'admin':
            return True
        if username.lower() in {'admin', 'red'}:
            return True
        return False

    async def _extract_ability_ids(self, request):
        """
        Return the ability IDs implicated by the request:
          - POST /api/v2/operations: expand adversary's abilities
          - POST .../potential-links: single 'ability_id' in body
        """
        method = request.method.upper()
        path = request.rel_url.path

        # POST /api/v2/operations → body contains adversary_id
        if method == 'POST' and path == '/api/v2/operations':
            body = await request.json()
            adv_id = body.get('adversary_id') or body.get('adversary', {}).get('adversary_id')
            if not adv_id:
                return []
            adversaries = await self.data_svc.locate('adversaries', match=dict(adversary_id=adv_id))
            if not adversaries:
                return []
            ids = []
            for adv in adversaries:
                disp = adv.display
                if disp.get('atomic_ordering'):
                    ids.extend(disp['atomic_ordering'])
                if disp.get('phases'):
                    for chunk in (disp['phases'] or {}).values():
                        ids.extend(chunk or [])
            return [a for a in ids if a]

        # POST /api/v2/operations/{id}/potential-links → body.ability_id
        if method == 'POST' and path.endswith('/potential-links'):
            body = await request.json()
            if 'ability_id' in body:
                return [body['ability_id']]
            return []

        return []
