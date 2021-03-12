from aiohttp import web


def make_app(services):
    from .security import authentication_required_middleware_factory

    app = web.Application(
        middlewares=[authentication_required_middleware_factory(services['auth_svc'])]
    )

    from .handlers.health_api import HealthApi
    HealthApi(services).add_routes(app)

    return app
