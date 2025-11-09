import json
from typing import Tuple, Dict, Any

import aiohttp_apispec
from aiohttp import web

from app.api.v2.handlers.base_object_api import BaseObjectApi
from app.api.v2.managers.adversary_api_manager import AdversaryApiManager
from app.api.v2.schemas.base_schemas import BaseGetAllQuerySchema, BaseGetOneQuerySchema
from app.objects.c_adversary import Adversary, AdversarySchema


class AdversaryApi(BaseObjectApi):
    """HTTP API for CRUD operations on adversaries."""

    def __init__(self, services: Dict[str, Any]) -> None:
        """Initialize routes and supporting managers."""
        super().__init__(
            description="adversary",
            obj_class=Adversary,
            schema=AdversarySchema,
            ram_key="adversaries",
            id_property="adversary_id",
            auth_svc=services["auth_svc"],
        )
        self._api_manager = AdversaryApiManager(
            data_svc=services["data_svc"], file_svc=services["file_svc"]
        )

    def add_routes(self, app: web.Application) -> None:
        """Register adversary routes on the application router."""
        router = app.router
        adversaries_by_id_path = "/adversaries/{adversary_id}"
        router.add_get("/adversaries", self.get_adversaries)
        router.add_get(adversaries_by_id_path, self.get_adversary_by_id)
        router.add_post("/adversaries", self.create_adversary)
        router.add_patch(adversaries_by_id_path, self.update_adversary)
        router.add_put(adversaries_by_id_path, self.create_or_update_adversary)
        router.add_delete(adversaries_by_id_path, self.delete_adversary)

    @aiohttp_apispec.docs(
        tags=["adversaries"],
        summary="Retrieve all adversaries",
        description=(
            "Returns a list of all available adversaries in the system, including plugin, name, "
            "description, and atomic ordering. Supply fields from `AdversarySchema` to the include/exclude "
            "fields of `BaseGetAllQuerySchema` in the request to filter the result."
        ),
    )
    @aiohttp_apispec.querystring_schema(BaseGetAllQuerySchema)
    @aiohttp_apispec.response_schema(
        AdversarySchema(many=True, partial=True),
        description="List of adversaries in `AdversarySchema` format.",
    )
    async def get_adversaries(self, request: web.Request) -> web.Response:
        """List adversaries with optional include/exclude filtering."""
        adversaries = await self.get_all_objects(request)
        self.log.debug("[get_adversaries] count=%s", len(adversaries))
        return web.json_response(adversaries)

    @aiohttp_apispec.docs(
        tags=["adversaries"],
        summary="Retrieve adversary by ID",
        description=(
            "Retrieve one adversary by ID. Use fields from the `AdversarySchema` in the request "
            "to filter the retrieved adversary."
        ),
        parameters=[
            {
                "in": "path",
                "name": "adversary_id",
                "schema": {"type": "string"},
                "required": "true",
                "description": "UUID of the adversary to retrieve",
            }
        ],
    )
    @aiohttp_apispec.querystring_schema(BaseGetOneQuerySchema)
    @aiohttp_apispec.response_schema(
        AdversarySchema(partial=True),
        description="Single adversary in `AdversarySchema` format.",
    )
    async def get_adversary_by_id(self, request: web.Request) -> web.Response:
        """Fetch a specific adversary by its ID."""
        adversary = await self.get_object(request)
        self.log.debug("[get_adversary_by_id] id=%s", request.match_info.get("adversary_id"))
        return web.json_response(adversary)

    @aiohttp_apispec.docs(
        tags=["adversaries"],
        summary="Create a new adversary",
        description="Create a new adversary using the format provided in the `AdversarySchema`.",
    )
    @aiohttp_apispec.request_schema(AdversarySchema)
    @aiohttp_apispec.response_schema(
        AdversarySchema, description="The created adversary in `AdversarySchema` format."
    )
    async def create_adversary(self, request: web.Request) -> web.Response:
        """Create a new adversary and verify it post-creation."""
        adversary = await self.create_on_disk_object(request)
        self.log.debug("[create_adversary] created=%s", getattr(adversary, "adversary_id", None))
        adversary = await self._api_manager.verify_adversary(adversary)
        self.log.debug("[create_adversary] verified id=%s", getattr(adversary, "adversary_id", None))
        return web.json_response(adversary.display)

    @aiohttp_apispec.docs(
        tags=["adversaries"],
        summary="Update an adversary",
        description="Update an adversary using fields from the `AdversarySchema` in the request body.",
        parameters=[
            {
                "in": "path",
                "name": "adversary_id",
                "schema": {"type": "string"},
                "required": "true",
                "description": "UUID of the adversary to be updated",
            }
        ],
    )
    @aiohttp_apispec.request_schema(AdversarySchema(partial=True, exclude=["adversary_id"]))
    @aiohttp_apispec.response_schema(
        AdversarySchema, description="The updated adversary in `AdversarySchema` format."
    )
    async def update_adversary(self, request: web.Request) -> web.Response:
        """Update an existing adversary and re-verify."""
        adversary = await self.update_on_disk_object(request)
        if adversary is None:
            self.log.debug("[update_adversary] not found id=%s", request.match_info.get("adversary_id"))
            raise web.HTTPNotFound(reason="Adversary not found. Try creating it instead.")

        try:
            adversary = await self._api_manager.verify_adversary(adversary)
        except Exception as exc:
            self.log.exception("[update_adversary] verification failed: %s", exc)
            raise web.HTTPInternalServerError(reason="Adversary verification failed")

        self.log.debug("[update_adversary] updated id=%s", getattr(adversary, "adversary_id", None))
        return web.json_response(adversary.display)

    @aiohttp_apispec.docs(
        tags=["adversaries"],
        summary="Deletes an adversary.",
        description="Deletes an existing adversary.",
        parameters=[
            {
                "in": "path",
                "name": "adversary_id",
                "schema": {"type": "string"},
                "required": "true",
                "description": "UUID of the adversary to delete",
            }
        ],
    )
    @aiohttp_apispec.response_schema(
        AdversarySchema(partial=True), code=204, description="HTTP 204 Status Code (No Content)"
    )
    async def delete_adversary(self, request: web.Request) -> web.Response:
        """Delete an adversary by ID."""
        await self.delete_on_disk_object(request)
        self.log.debug("[delete_adversary] deleted id=%s", request.match_info.get("adversary_id"))
        return web.HTTPNoContent()

    @aiohttp_apispec.docs(
        tags=["adversaries"],
        summary="Create or update an adversary",
        description=(
            "Attempt to update an adversary using fields from the `AdversarySchema`. If the "
            "adversary does not exist, a new one is created."
        ),
        parameters=[
            {
                "in": "path",
                "name": "adversary_id",
                "schema": {"type": "string"},
                "required": "true",
                "description": "UUID of the adversary to create or update",
            }
        ],
    )
    @aiohttp_apispec.request_schema(AdversarySchema(partial=True))
    @aiohttp_apispec.response_schema(
        AdversarySchema,
        description="A single adversary, either newly created or updated, in `AdversarySchema` format.",
    )
    async def create_or_update_adversary(self, request: web.Request) -> web.Response:
        """Create a new adversary or update an existing one, then verify and return JSON."""
        try:
            # Let the base class handle payload parsing, access, ID setting, and validation
            obj = await self.create_on_disk_object(request)

            # Post-creation/update verification step (e.g., metadata backfill)
            obj = await self._api_manager.verify_adversary(obj)

            self.log.debug(
                "[create_or_update_adversary] final display=%s", getattr(obj, "display", {})
            )
            self.log.debug(
                "[create_or_update_adversary] metadata=%s", getattr(obj, "metadata", {})
            )
            return web.json_response(obj.display)

        except web.HTTPException:
            # Preserve existing behavior for known HTTP exceptions
            raise

        except Exception as exc:
            self.log.exception("[create_or_update_adversary] unexpected error: %s", exc)
            raise web.HTTPInternalServerError(
                reason="Internal error during adversary create-or-update"
            )

    async def _parse_common_data_from_request(
        self, request: web.Request
    ) -> Tuple[Dict[str, Any], Dict[str, Any], str, Dict[str, Any], Dict[str, Any]]:
        """
        Parse request body and common elements for ID, access, query, and search dicts.

        Returns:
            data: Parsed JSON body (with 'id' stripped and path id injected as adversary_id if present)
            access: Access dict for the requesting user
            obj_id: ID pulled from the path parameters
            query: Query dict targeting the specified object
            search: `query` + `access` merged for manager layer
        """
        # Prefer request.json() but keep a safe fallback for non-JSON bodies
        data: Dict[str, Any] = {}
        try:
            if request.can_read_body:
                data = await request.json()
        except Exception:
            raw_body = await request.read()
            if raw_body:
                try:
                    data = json.loads(raw_body)
                except Exception:
                    data = {}

        data.pop("id", None)  # ensure we don't accidentally trust body 'id'

        obj_id = request.match_info.get(self.id_property, "") or ""
        if obj_id:
            data[self.id_property] = obj_id

        access = await self.get_request_permissions(request)
        query = {self.id_property: obj_id}
        search = {**query, **access}

        self.log.debug(
            "[_parse_common_data_from_request] id=%s, has_body=%s",
            obj_id,
            bool(data),
        )
        return data, access, obj_id, query, search
