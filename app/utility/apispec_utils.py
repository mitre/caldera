import json
from collections import defaultdict

import apispec
import marshmallow as ma
import yaml
from apispec.ext.marshmallow import MarshmallowPlugin

from app.utility.base_world import BaseWorld


def recursive_default_dict():
    """
    Factory for arbitrarily deeply nested dicts.
    """
    return defaultdict(recursive_default_dict)


class PolymorphicSchema:

    def __init__(self, name, discriminator, mapping):
        self.name = name
        self.discriminator = discriminator
        self.mapping = mapping

    def insert_into_apispec(self, spec_obj: apispec.APISpec):
        converter = self._get_marshmallow_converter(spec_obj)
        mapping = dict()
        for property_name, obj_def in self.mapping.items():
            if getattr(obj_def, 'display_schema', None):
                schema = obj_def.display_schema
            elif getattr(obj_def, 'schema', None):
                schema = obj_def.schema
            else:
                schema = obj_def
            for ref_path in converter.resolve_nested_schema(schema).values():
                mapping[property_name] = ref_path

        return dict(discriminator=dict(propertyName=self.discriminator, mapping=mapping))

    @staticmethod
    def _get_marshmallow_converter(spec: apispec.APISpec) -> MarshmallowPlugin.Converter:
        for plugin in spec.plugins:
            if isinstance(plugin, MarshmallowPlugin):
                return plugin.converter


class ApiInfo:

    def __init__(self):
        self.summary = None
        self.description = None
        self.methods = []
        self.request_schema = None
        self.response_schema = None


def apidocs(summary=None, description=None, methods=None):
    """
    Decorator for adding api info to paths.
    """
    def wrapper(func):
        if not hasattr(func, '__api_info__'):
            func.__api_info__ = ApiInfo()
        func.__api_info__.summary = summary
        func.__api_info__.description = description
        func.__api_info__.methods = methods
        return func
    return wrapper


def request_schema(schema):
    """
    Decorator for adding request body schemas.
    """
    def wrapper(func):
        if not hasattr(func, '__api_info__'):
            func.__api_info__ = ApiInfo()
        func.__api_info__.request_schema = schema
        return func
    return wrapper


def response_schema(schema):
    """
    Decorator for adding response body schemas.
    """
    def wrapper(func):
        if not hasattr(func, '__api_info__'):
            func.__api_info__ = ApiInfo()
        func.__api_info__.response_schema = schema
        return func
    return wrapper


class CalderaApiDocs(BaseWorld):
    def __init__(self, aiohttp_app):
        self.aiohttp_app = aiohttp_app
        self.apispec = apispec.APISpec(
            title='Caldera API',
            version=self.get_version(),
            openapi_version='3.0.2',
            plugins=[MarshmallowPlugin()],
        )

    @property
    def spec(self):
        return self.apispec.to_dict()

    @property
    def yaml_spec(self):
        # Contortions until we write a yaml representer to support recursive default dict
        return yaml.safe_dump(json.loads(self.json_spec), default_flow_style=False)

    @property
    def json_spec(self):
        return json.dumps(self.spec)

    def build_spec(self):
        for route in self.aiohttp_app.router.routes():
            if not hasattr(route.handler, '__api_info__'):
                continue

            api_info = route.handler.__api_info__  # type: ApiInfo
            operations = recursive_default_dict()
            for method in api_info.methods:
                method = method.lower()
                if api_info.response_schema:
                    operations[method]["responses"]["200"]["content"]["application/json"]["schema"] = self._schema_hook(api_info.response_schema)
                if api_info.request_schema:
                    operations[method]["requestBody"]["content"]["application/json"]["schema"] = self._schema_hook(api_info.request_schema)
                operations[method]["summary"] = api_info.summary
                operations[method]["description"] = api_info.description

            self.apispec.path(summary=api_info.summary,
                              description=api_info.description,
                              path=route.resource.canonical,
                              operations=operations)

    def _schema_hook(self, schema):
        if isinstance(schema, PolymorphicSchema):
            return schema.insert_into_apispec(self.apispec)
        else:
            return schema


class RequestSchema(ma.Schema):
    index = ma.fields.String(required=True)


class RequestOperationReport(RequestSchema):
    op_id = ma.fields.String()
    display_results = ma.fields.Bool()
