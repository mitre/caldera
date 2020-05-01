import apispec
import marshmallow
from apispec.ext.marshmallow import resolver, MarshmallowPlugin
from apispec import yaml_utils


class CalderaApispecPlugin(MarshmallowPlugin):
    """APISpec plugin for Caldera."""

    def init_spec(self, spec: apispec.APISpec):
        super().init_spec(spec)

        # Automatically add all first class object schemas and create a polymorphic 'discriminator' schema
        # that references them. REF: https://swagger.io/docs/specification/data-models/inheritance-and-polymorphism/
        schemas = [name for name in marshmallow.schema.class_registry._registry if
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
        spec.components.schema('CoreRequest',
                               component=dict(type='object',
                                              discriminator=dict(propertyName='index'),
                                              oneOf=[
                                                  {'$ref': '#/components/schemas/CoreOperationRequest'},
                                                  {'$ref': '#/components/schemas/CoreAgentRequest'},
                                              ]))

    @staticmethod
    def _get_methods_for_view(route):
        if route.method == '*':
            raise NotImplementedError('Cannot infer appropriate methods from aiohttp routes added with "*".')
        else:
            return [route.method.lower()]

    def path_helper(self, operations, *, aiohttp_resource, handler, **kwargs):
        """Path helper that allows passing a aiohttp ReosourceRoute object."""
        handler_docstring = getattr(handler, 'orig_docstring', handler)
        operations.update(yaml_utils.load_operations_from_docstring(handler_docstring))
        return aiohttp_resource.resource.canonical
