import logging
import traceback

from aiohttp import web
from aiohttp_jinja2 import template


class RestApi:

    def __init__(self, services):
        self.data_svc = services.get('data_svc')
        self.app_svc = services.get('app_svc')
        self.reporting_svc = services.get('reporting_svc')
        self.auth_svc = services.get('auth_svc')
        self.plugin_svc = services.get('plugin_svc')
        self.contact_svc = services.get('contact_svc')
        self.file_svc = services.get('file_svc')
        self.rest_svc = services.get('rest_svc')

    async def enable(self):
        self.app_svc.application.router.add_static('/gui', 'static/', append_version=True)
        self.app_svc.application.router.add_route('*', '/', self.landing)
        self.app_svc.application.router.add_route('*', '/enter', self.validate_login)
        self.app_svc.application.router.add_route('*', '/logout', self.logout)
        self.app_svc.application.router.add_route('GET', '/login', self.login)
        self.app_svc.application.router.add_route('PUT', '/plugin/chain/potential-links', self.add_potential_link)
        self.app_svc.application.router.add_route('POST', '/plugin/chain/potential-links', self.find_potential_links)
        self.app_svc.application.router.add_route('*', '/plugin/chain/full', self.rest_full)
        self.app_svc.application.router.add_route('*', '/plugin/chain/rest', self.rest_api)
        self.app_svc.application.router.add_route('POST', '/plugin/chain/payload', self.upload_payload)
        self.app_svc.application.router.add_route('PUT', '/plugin/chain/operation/state', self.rest_state_control)
        self.app_svc.application.router.add_route('PUT', '/plugin/chain/operation/{operation_id}',
                                                  self.rest_update_operation)

    @template('login.html', status=401)
    async def login(self, request):
        return dict()

    @template('login.html')
    async def logout(self, request):
        await self.auth_svc.logout_user(request)

    async def validate_login(self, request):
        return await self.auth_svc.login_user(request)

    @template('chain.html')
    async def landing(self, request):
        try:
            await self.auth_svc.check_permissions(request)
            abilities = await self.data_svc.locate('abilities')
            tactics = set([a.tactic.lower() for a in abilities])
            payloads = await self.rest_svc.list_payloads()
            hosts = [h.display for h in await self.data_svc.locate('agents')]
            groups = list(set(([h['group'] for h in hosts])))
            adversaries = [a.display for a in await self.data_svc.locate('adversaries')]
            operations = [o.display for o in await self.data_svc.locate('operations')]
            sources = [s.display for s in await self.data_svc.locate('sources')]
            planners = [p.display for p in await self.data_svc.locate('planners')]
            obfuscators = [o.display for o in await self.data_svc.locate('obfuscators')]
            plugins = [p.display for p in await self.data_svc.locate('plugins', match=dict(enabled=True))]
            contacts = [c.display for c in self.contact_svc.contacts]
            return dict(exploits=[a.display for a in abilities], groups=groups, adversaries=adversaries, agents=hosts,
                        operations=operations, tactics=tactics, sources=sources, planners=planners, payloads=payloads,
                        plugins=plugins, obfuscators=obfuscators, contacts=contacts)
        except web.HTTPFound as e:
            raise e
        except Exception as e:
            logging.error('[!] landing: %s' % e)

    async def upload_payload(self, request):
        return await self.file_svc.save_multipart_file_upload(request, 'data/payloads/')

    async def find_potential_links(self, request):
        await self.auth_svc.check_permissions(request)
        data = dict(await request.json())
        links = await self.rest_svc.get_potential_links(**data)
        return web.json_response(dict(links=[l.display for l in links]))

    async def add_potential_link(self, request):
        await self.auth_svc.check_permissions(request)
        data = dict(await request.json())
        await self.rest_svc.apply_potential_link(data)
        return web.json_response(dict())

    async def rest_full(self, request):
        try:
            base = await self.rest_core(request)
            base[0]['abilities'] = [a.display for a in await self.data_svc.locate('abilities')]
            return web.json_response(base)
        except Exception:
            pass

    async def rest_api(self, request):
        try:
            base = await self.rest_core(request)
            return web.json_response(base)
        except Exception:
            pass

    async def rest_core(self, request):
        """
        This function is under construction until all objects have been converted from SQL tables
        :param request:
        :return:
        """
        try:
            await self.auth_svc.check_permissions(request)
            data = dict(await request.json())
            index = data.pop('index')
            options = dict(
                DELETE=dict(
                    agent=lambda d: self.rest_svc.delete_agent(d),
                    operation=lambda d: self.rest_svc.delete_operation(d)
                ),
                PUT=dict(
                    adversary=lambda d: self.rest_svc.persist_adversary(d),
                    ability=lambda d: self.rest_svc.persist_ability(d),
                    source=lambda d: self.rest_svc.persist_source(d),
                    planner=lambda d: self.rest_svc.update_planner(d),
                    agent=lambda d: self.rest_svc.update_agent_data(d),
                    chain=lambda d: self.rest_svc.update_chain_data(d),
                    operation=lambda d: self.rest_svc.create_operation(d),
                    schedule=lambda d: self.rest_svc.create_schedule(d),
                ),
                POST=dict(
                    ability=lambda d: self.rest_svc.display_objects('abilities', d),
                    adversary=lambda d: self.rest_svc.display_objects('adversaries', d),
                    planners=lambda d: self.rest_svc.display_objects('planners', d),
                    agent=lambda d: self.rest_svc.display_objects('agents', d),
                    operation=lambda d: self.rest_svc.display_objects('operations', d),
                    source=lambda d: self.rest_svc.display_objects('sources', d),
                    operation_report=lambda d: self.rest_svc.display_operation_report(d),
                    result=lambda d: self.rest_svc.display_result(d),
                )
            )
            output = await options[request.method][index](data)
            return output
        except Exception:
            traceback.print_exc()

    async def rest_update_operation(self, request):
        i = request.match_info['operation_id']
        data = await request.json()
        operation = await self.data_svc.locate('operations', match=dict(id=int(i)))
        operation[0].autonomous = data.get('autonomous')
        return web.Response()

    async def rest_state_control(self, request):
        body = await request.json()
        state = body.get('state')

        async def _validate_request():
            try:
                op = await self.data_svc.locate('operations', dict(id=body['name']))
                if not len(op):
                    raise web.HTTPNotFound
                elif op[0].state == op[0].states['FINISHED']:
                    raise web.HTTPBadRequest(body='This operation has already finished.')
                elif state not in op[0].states.values():
                    raise web.HTTPBadRequest(body='state must be one of {}'.format(op[0].states.values()))
            except Exception as e:
                print(e)

        await _validate_request()
        operation = await self.data_svc.locate('operations', match=dict(id=body['name']))
        operation[0].state = body.get('state')
        return web.Response()
