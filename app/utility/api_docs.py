import copy
from collections import defaultdict


class Responses:
    DEFAULT_RESPONSE = {
        '200': {
            'description': 'successful operation'
        },
        '400': {
            'description': 'invalid request'
        },
        '500': {
            'description': 'internal server error'
        }
    }
    JSON_RESPONSE = copy.copy(DEFAULT_RESPONSE)
    JSON_RESPONSE['200']['content'] = 'application/json'


class Schemas:
    AGENT = dict(Agent=dict(type='object', description='Agent', properties=dict(
        paw=dict(type='string'), group=dict(type='string'),
        architecture=dict(type='string'), platform=dict(type='string'),
        server='string', location='string', pid='integer', ppid=dict(type='integer'),
        trusted=dict(type='boolean'), last_seen=dict(type='string'), sleep_min=dict(type='integer'),
        sleep_max=dict(type='integer'), executors=dict(type='integer'),
        privilege=dict(type='string'), display_name=dict(type='string'), exe_name=dict(type='string'),
        host=dict(type='string'), watchdog=dict(type='integer'), contact=dict(type='string'))))

    OPERATION = dict(Operation=dict(type='object', description='Operation', properties=dict(
        id=dict(type='string'), name=dict(type='string'), host_group=dict(type='array'),
        adversary=dict(type='object'), jitter=dict(type='integer'),
        source=dict(type='object'), planner=dict(type='string'),
        start=dict(type='string'), state=dict(type='string'), phase=dict(type='integer'),
        obfuscator=dict(type='object'), autonomous=dict(type='boolean'), finish=dict(type='string'),
        chain=dict(type='array'))))


class Requests:
    INDEX_FIELD_REQUEST = {'content': {
                 'application/json': {'schema': {
                     'type': 'object',
                     'additionalProperties': True,
                     'properties': {
                         'index': {
                             'description': 'The caldera object type (e.g. "agent", "link", "ability", etc).',
                             'required': True,
                             'type': 'string'},
                     }
                     }}}}

    DELETE_REQUEST_BODY = {'content': {
        'application/json': {'schema': {
            'allOf': [{
                'type': 'object',
                'additionalProperties': True,
                'properties': {
                    'index': {
                        'description': 'The caldera object type (e.g. "agent", "link", "ability", etc).',
                        'required': True,
                        'type': 'string'}}},
                {'oneOf': [
                    {'$ref': '#/components/schemas/Agent'},
                    {'$ref': '#/components/schemas/Operation'}
                ]}
            ]
        }}}}

    MULTIPART_REQUEST = {'content': {
                 'multipart/form-data': {
                     'schema': {
                         'type': 'object',
                         'properties': {
                             'filename': {
                                 'type': 'array',
                                 'items': {
                                     'type': 'string',
                                     'format': 'binary'
                                 }
                             }
                         }
                     }
                 }}}


def swagger(summary='', description='', parameters=None, responses=None, requestBody=None, tags=None):
    """
    Decorator that can be used document an aiohttp request handler.

    :param summary:
    :param description:
    :param responses:
    :param parameters
    :param requestBody
    :param tags
    :return:
    """

    def wrapper(func):
        func.openapi_path_info = dict(
            summary=summary,
            description=description,
            parameters=parameters if parameters else [],
            responses=responses if responses else dict(),
            requestBody=requestBody if requestBody else dict(),
            tags=tags if tags else []
        )
        return func

    return wrapper


def build_openapi_spec(app):
    """
    Creates the openapi HTTP API specification (e.g. swagger.json) from an aiohttp.Application object.
    :param app: The aiohttp application object to generate API documentation for.
    :return: A dictionary object ready for JSON serialization.
    """
    agent_model_tag = {'name': 'agent_model',
         'x-displayName': 'The Agent Model',
         'description': '<SchemaDefinition schemaRef="#/components/schemas/Agent"/>'
         }
    operation_model_tag = {'name': 'operation_model',
                       'x-displayName': 'The Operation Model',
                       'description': '<SchemaDefinition schemaRef="#/components/schemas/Operation"/>'
                       }
    openapi_dict = dict(
        openapi='3.0.0',
        info=dict(title='CALDERA API',
                  description='API Docs for the Caldera Automated Adversary Emulation Tool',
                  version='0.6.4'),
        servers=[dict(url='http://localhost:8888', description='locally running service')],
        paths=defaultdict(dict),
        components=dict(schemas=dict(**Schemas.AGENT, **Schemas.OPERATION)),
        tags=[agent_model_tag, operation_model_tag]
    )
    openapi_dict['x-tagGroups'] = [{'name': 'HTTP API', 'tags': ['core']},
                                   {'name': 'Models', 'tags': ['agent_model', 'operation_model']}]

    for route in app.router.routes():
        if hasattr(route.handler, 'openapi_path_info'):
            if route.method == '*':
                for method in ('get', 'put', 'post'):
                    openapi_dict['paths'][route.resource.canonical][method] = _get_path_info(route)
            else:
                openapi_dict['paths'][route.resource.canonical][route.method.lower()] = _get_path_info(route)

    return openapi_dict


def _get_tags_for_route(route):
    """ Tag a path based on whether its handler is in the core of caldera or a plugin."""
    mod_path = route.handler.__module__.split('.')
    if mod_path[0] == 'app':
        return ['core']
    elif mod_path[0] == 'plugins':
        return [mod_path[1]]
    else:
        return []


def _get_path_info(route):
    path_info = route.handler.openapi_path_info
    if 'responses' not in path_info:
        path_info['responses'] = copy.deepcopy(Responses.DEFAULT_RESPONSE)
    for tag in _get_tags_for_route(route):
        if tag not in path_info['tags']:
            path_info['tags'].append(tag)

    return path_info
