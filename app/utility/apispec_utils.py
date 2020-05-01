import apispec
import marshmallow
from apispec.ext.marshmallow import OpenAPIConverter, resolver,  resolve_schema_instance, \
    make_schema_key
from apispec import BasePlugin, yaml_utils


class CalderaApispecPlugin(BasePlugin):
    """APISpec plugin for aiohttp"""

    def __init__(self):
        self.converter = None

    def init_spec(self, spec: apispec.APISpec):
        schemas = [name for name in marshmallow.schema.class_registry._registry if
                   ('app.objects' in name and 'secondclass' not in name and 'Fields' not in name)]
        schema_names = [resolver(schema) for schema in schemas]
        self.converter = OpenAPIConverter(spec.openapi_version, resolver, spec)
        for schema in schemas:
            self.converter.resolve_nested_schema(schema)
        schema_mapping = {name.lower(): '#/components/schemas/%s' % name for name in schema_names}
        spec.components.schema('CalderaObjects',
                               component=dict(type='object',
                                              discriminator=dict(propertyName='index', mapping=schema_mapping)),
                               marshmallow=False)

    def schema_helper(self, name, _, schema=None, marshmallow=True, **kwargs):
        if schema is None:
            return None

        if not marshmallow:
            return schema

        schema_instance = resolve_schema_instance(schema)
        #
        schema_key = make_schema_key(schema_instance)
        # self.warn_if_schema_already_in_spec(schema_key)
        self.converter.refs[schema_key] = name

        json_schema = self.converter.schema2jsonschema(schema_instance)

        return json_schema

    @staticmethod
    def _get_methods_for_view(route):
        if route.method == '*':
            raise NotImplementedError('Cannot infer appropriate methods from aiohttp routes added with "*".')
        else:
            return [route.method.lower()]

    def path_helper(self, operations, *, view, handler, **kwargs):
        """Path helper that allows passing a aiohttp ReosourceRoute object."""
        handler_docstring = getattr(handler, 'orig_docstring', handler)
        operations.update(yaml_utils.load_operations_from_docstring(handler_docstring))
        return view.resource.canonical
