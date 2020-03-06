import copy
from collections import defaultdict


DEFAULT_RESPONSES = {
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


def swagger(summary='', description='', parameters=None, responses=None, requestBody=None, tags=None):
    """
    Decorator that can be used document an aiohttp request handler.

    :param summary:
    :param description:
    :param responses:
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
    openapi_dict = dict(
        openapi='3.0.0',
        info=dict(title='CALDERA API',
                  description='API Docs for the Caldera Automated Adversary Emulation Tool',
                  version='0.6.4'),
        servers=[dict(url='http://localhost:8888', description='locally running service')],
        paths=defaultdict(dict)
    )
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
        path_info['responses'] = copy.deepcopy(DEFAULT_RESPONSES)
    for tag in _get_tags_for_route(route):
        if tag not in path_info['tags']:
            path_info['tags'].append(tag)

    return path_info
