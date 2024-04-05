from plugins.oidc.app.oidc_svc import OidcService

name = 'oidc'
description = 'A plugin that provides OpenID authentication for CALDERA'
address = None

async def enable(services):
    app = services.get('app_svc').application
    oidc_svc = OidcService()
    app.router.add_route('*', '/oidc', oidc_svc.oidc)
