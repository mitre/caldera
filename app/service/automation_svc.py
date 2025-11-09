import logging
import uuid

import marshmallow as ma
import yaml
from aiohttp import web
from aiohttp_jinja2 import template

from app.objects.secondclass.c_fact import FactSchema


class AbilitySchema(ma.Schema):
    ability_id = ma.fields.String(required=True)
    facts = ma.fields.List(ma.fields.Nested(FactSchema))

    @ma.pre_load
    def fix_id(self, ability, **_):
        if "id" in ability:
            ability["ability_id"] = ability.pop("id")
        return ability


class AutomatedOperationSchema(ma.Schema):
    class Meta:
        unknown = ma.EXCLUDE

    operation_id = ma.fields.String(required=True)
    name = ma.fields.String()
    description = ma.fields.String()
    version = ma.fields.Integer()
    operation_facts = ma.fields.List(ma.fields.Nested(FactSchema))
    atomic_ordering = ma.fields.List(ma.fields.Nested(AbilitySchema))

    @ma.pre_load
    def fix_id(self, operation, **_):
        if "id" in operation:
            operation["operation_id"] = operation.pop("id")
        else:
            operation["operation_id"] = str(uuid.uuid4())
        return operation


class AutomationService:
    def __init__(self, services, name, description):
        self.name = name
        self.description = description
        self.services = services

        self.log = logging.getLogger("automation_svc")

    @template("automation.html")
    async def splash(self, request):
        return dict(name=self.name, description=self.description)

    async def _read_yaml(self, request):
        file_size_limit = 1.28e8  # 128 MB (SI)

        reader = await request.multipart()
        field = await reader.next()
        assert field.name == "file"

        content = bytes()
        size = 0
        while True:
            chunk = await field.read_chunk()
            if not chunk:
                break

            size += len(chunk)
            if size > file_size_limit:
                break

            content += chunk

        yaml_content = yaml.safe_load(content)

        # Make a round-trip to schema to validate content
        res = AutomatedOperationSchema().load(yaml_content)
        return AutomatedOperationSchema().dump(res)

    async def handle_import(self, request):
        try:
            data = await self._read_yaml(request)
        except yaml.YAMLError:
            return web.json_response({"error": "Invalid YAML format"}, status=422)
        except ma.ValidationError as err:
            self.log.warning(f"YAML validation failed: {err.messages}")
            return web.json_response(
                {"error": "YAML validation failed", "messages": err.messages},
                status=422,
            )
        except Exception:
            return web.json_response({"error": "An error occurred"}, status=500)
        return web.json_response(data)
