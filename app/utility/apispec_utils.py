import json
from collections import defaultdict

import apispec
import marshmallow as ma
import yaml
from apispec.ext.marshmallow import resolver, MarshmallowPlugin
from apispec import yaml_utils

from app.utility.base_world import BaseWorld


def recursive_default_dict():
    return defaultdict(recursive_default_dict)


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
                    operations[method]["responses"]["200"]["content"]["application/json"]["schema"] = api_info.response_schema
                if api_info.request_schema:
                    operations[method]["requestBody"]["content"]["application/json"]["schema"] = api_info.request_schema
                operations[method]["summary"] = api_info.summary
                operations[method]["description"] = api_info.description

            self.apispec.path(summary=api_info.summary,
                              description=api_info.description,
                              path=route.resource.canonical,
                              operations=operations)


class RequestSchema(ma.Schema):
    index = ma.fields.String(required=True)


class RequestOperationReport(RequestSchema):
    op_id = ma.fields.String()
    display_results = ma.fields.Bool()


class CalderaApispecPlugin(MarshmallowPlugin):
    """APISpec plugin for Caldera."""

    def init_spec(self, spec: apispec.APISpec):
        super().init_spec(spec)

        # Automatically add all first class object schemas and create a polymorphic 'discriminator' schema
        # that references them. REF: https://swagger.io/docs/specification/data-models/inheritance-and-polymorphism/
        schemas = [name for name in ma.schema.class_registry._registry if
                   ('app.objects' in name and 'secondclass' not in name and 'Fields' not in name)]
        schema_names = [resolver(schema) for schema in schemas]
        # self.converter = OpenAPIConverter(spec.openapi_version, resolver, spec)
        for schema in schemas:
            self.converter.resolve_nested_schema(schema)
        schema_mapping = {name.lower(): '#/components/schemas/%s' % name for name in schema_names}
        spec.components.schema('CalderaObjects',
                               component=dict(type='object',
                                              discriminator=dict(propertyName='index', mapping=schema_mapping)))
        spec.components.schema('CoreOperationRequest', component=dict(type='object', required=['index', 'op_id'],
                               properties=(dict(op_id=dict(type='string'),
                                                index=dict(type='string')))))
        spec.components.schema('CoreAgentRequest', component=dict(type='object', required=['index'],
                               properties=(dict(id=dict(type='string'),
                                                index=dict(type='string')))))
        request_mapping = dict(operation='#/components/schemas/CoreOperationRequest',
                               agent='#/components/schemas/CoreAgentRequest',
                               )
        spec.components.schema('CoreRequest',
                               component=dict(type='object',
                                              discriminator=dict(propertyName='index', mapping=request_mapping)))

    @staticmethod
    def _get_methods_for_view(route):
        if route.method == '*':
            raise NotImplementedError('Cannot infer appropriate methods from aiohttp routes added with "*".')
        else:
            return [route.method.lower()]

    def path_helper(self, operations, *, aiohttp_resource, handler, **kwargs):
        """Path helper that allows passing a aiohttp ReosourceRoute object."""
        handler_docstring = getattr(handler, 'orig_docstring', handler.__doc__)
        operations.update(yaml_utils.load_operations_from_docstring(handler_docstring))
        return aiohttp_resource.resource.canonical
