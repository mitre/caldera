import os
from aiohttp import web

class AccessControlService:
    def __init__(self, data_svc, auth_svc):
        self.data_svc = data_svc
        self.auth_svc = auth_svc
        self.users = {}  # username -> {allowed_abilities: set()}

    def create_user(self, username):
        username = username.strip()
        if not username:
            raise ValueError("Username required")
        self.users[username] = {"allowed_abilities": set()}
        return self.users[username]

    def assign_ability_to_user(self, username, ability):
        user = self.users.get(username)
        if not user:
            raise ValueError("User not found")
        user["allowed_abilities"].add(ability)
        return user

    def get_user_abilities(self, username):
        user = self.users.get(username)
        if not user:
            raise ValueError("User not found")
        return list(user["allowed_abilities"])

def add_gui_routes(app):
    gui_path = os.path.join(os.path.dirname(__file__), '../../gui/build')
    app.router.add_static('/plugin/accesscontrol/gui/', gui_path, show_index=True)
    app.router.add_get('/plugin/accesscontrol/', index)

async def index(request):
    gui_path = os.path.join(os.path.dirname(__file__), '../../gui/build/index.html')
    return web.FileResponse(gui_path)
