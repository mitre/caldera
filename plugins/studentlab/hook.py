# plugins/studentlab/hook.py
from aiohttp import web
from app.service.auth_svc import check_authorization  # to guard GUI/REST if desired

name = "studentlab"
description = "Hardcoded student -> abilities mapping, plus simple endpoints"
address = None  # we add a GUI later; for now pure API

async def enable(services):
    app = services.get("app_svc").application
    handler = StudentLabAPI(services)
    # Start an operation for a student with their assigned ability list
    app.router.add_route("POST", "/plugin/studentlab/start-op", handler.start_op)

class StudentLabAPI:
    def __init__(self, services):
        self.services = services
        self.data_svc = services.get("data_svc")
        self.rest_svc = services.get("rest_svc")

    async def _ensure_adversary_for_student(self, username, ability_ids):
        """
        Create (persist) an adversary profile tied to this student if not present.
        Returns the adversary_id.
        """
        # Find existing by name tag, else persist
        existing = await self.data_svc.locate("adversaries", {"name": f"student-{username}"})
        if existing:
            return existing[0].adversary_id

        # Persist a new adversary using the RestServiceInterface
        # (writes YAML into data/adversaries so it survives restarts)
        adv_dict = {
            "name": f"student-{username}",
            "description": f"Abilities assigned to {username}",
            "atomic_ordering": ability_ids,  # list of ability UUID strings
            # you may generate a uuid4() yourself and add "adversary_id": "<uuid>",
            # but Caldera can also assign one if omitted.
        }
        adv_id = await self.rest_svc.persist_adversary("red", adv_dict)
        return adv_id

    async def start_op(self, request):
        """
        POST /plugin/studentlab/start-op
        JSON body: { "username": "alice", "group": "students", "planner": "atomic" }
        """
        body = await request.json()
        username = body.get("username")
        group = body.get("group", "students")    # agent group to target
        planner = body.get("planner", "atomic")  # atomic | batch | buckets ...

        # --- Hardcoded student -> ability mapping (fill your real UUIDs) ---
        from .student_assign import STUDENT_ABILITIES
        if username not in STUDENT_ABILITIES:
            return web.json_response({"error": "unknown student"}, status=400)

        ability_ids = STUDENT_ABILITIES[username]["abilities"]
        adversary_id = await self._ensure_adversary_for_student(username, ability_ids)

        # Create an operation that uses the student's adversary
        op_data = {
            "name": f"lab-{username}",
            "adversary_id": adversary_id,
            "group": group,
            "planner": {"name": planner},
        }
        op = await self.rest_svc.create_operation("red", op_data)
        return web.json_response({"ok": True, "operation_id": op.id, "adversary_id": adversary_id})
