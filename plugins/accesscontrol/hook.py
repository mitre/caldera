from app.utility.base_world import BaseWorld

name = 'accesscontrol'
description = 'Custom Plugin for Role-Based Access Control'
address = '/plugin/accesscontrol'
access = BaseWorld.Access.APP

async def enable(services):
    app_svc  = services.get('app_svc')
    data_svc = services.get('data_svc')
    auth_svc = services.get('auth_svc')

    from .app.service.accesscontrol_svc import AccessControlService
    services['accesscontrol_svc'] = AccessControlService(data_svc=data_svc, auth_svc=auth_svc)

    from .app.api.accesscontrol_api import add_routes
    await add_routes(app_svc.application, services)

    from .app.api.accesscontrol_api import add_routes, add_gui_routes
    await add_routes(app_svc.application, services)
    add_gui_routes(app_svc.application)

async def disable(services):
    return