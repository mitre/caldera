import asyncio
from datetime import datetime, timezone
from functools import wraps
import traceback
import inspect
import logging

import ujson as json_module
import hashlib
import yaml
from aiohttp import web
import aiohttp
import mongoengine
import os

from .engine.objects import Operation, Network, Domain, Log, ObservedHost, TechniqueMapping, Job, Rat, Host, \
    ObservedRat, Adversary, CodedStep, ActiveConnection, Agent, AttackTechnique, AttackTactic, SiteUser, Setting, \
    Opcodes, Artifactlist, ObservedFile, AttackList, JobException, ObservedSchtask, ObservedProcess, AttackGroup
from . import authentication as auth
from .engine.database import native_types
from . import ddp
from . import attack
from . import util
from . import interface
from . import extern


log = logging.getLogger(__name__)

routes = []


def api(uri, methods, objects=None, get=None, auth_group=None, headers=None):
    """This is a decorator for web api endpoints

    Args:
        uri: The URI for the API, can contain keywords denoted by '{}' which indicate
        objects: a list of tuples
        methods: the list of HTTP methods this API accepts
        auth_group: the group that the token must be in for access to this API
        headers: A list of headers to return with the Response
    """
    if objects is None:
        objects = {}
    if get is None:
        get = {}
    if auth_group is None:
        auth_group = []
    if headers is None:
        headers = {}

    def decorator(f):
        @wraps(f)
        async def decorated(req, token, url_match):
            kwargs = {}
            # Map id to object
            for name, _class in objects.items():
                if name in url_match:
                    # If this fails and the request type is 'GET',
                    # then an exception should be returned
                    try:
                        kwargs[name] = _class.objects.with_id(url_match[name])
                        if kwargs[name] is None:
                            return web.HTTPBadRequest()
                    except (mongoengine.errors.ValidationError, ):
                        # The client has sent an invalid id in the URL
                        return web.HTTPBadRequest()

            # Now set the default get parameters
            # For cases where we see args like ?arg1=value1&arg2&...
            # arg2 is set to ''
            # but change it to True instead
            trueified = {k: True if v == '' else v for k, v in req.GET.items()}

            for k, v in get.items():
                kwargs[k] = trueified.get(k, v)

            sig = inspect.signature(f)

            if 'token' in sig.parameters:
                kwargs['token'] = token

            # Finally format the output as json (or jsonfm)
            results = await f(req, **kwargs)
            if isinstance(results, web.StreamResponse):
                return results
            else:
                json = json_module.dumps(native_types(results), sort_keys=True, indent=4)
                return web.Response(text=json, content_type='application/json', headers=headers)

        async def entrypoint(req):
            host = None
            try:
                # ensure this member is authorized
                token = auth.Token(req.cookies.get('AUTH'))
                l = [g for g in auth_group if token.in_group(g)]
                if len(l) == 0:
                    raise auth.NotAuthorized()

                # active connections
                peername = req.transport.get_extra_info('peername')
                if peername is not None:
                    host_ip, port = peername
                    if req.host:
                        local_ip = req.host.split(":")[0]
                        if local_ip == "localhost":
                            local_ip = "127.0.0.1"
                    else:
                        local_ip = "127.0.0.1"
                    token_host = None
                    if token.in_group('agent'):
                        agent = Agent.objects.with_id(token.session_info['_id'])
                        if agent is None:
                            raise auth.NotAuthorized
                        agent.modify(**{'alive': True})
                        token_host = agent.host
                    host = ActiveConnection.objects(ip=host_ip, host=token_host, local_ip=local_ip).first()
                    if host is None:
                        host = ActiveConnection(ip=host_ip, host=token_host, local_ip=local_ip, connections=0).save()
                    host.update(inc__connections=1)

                resp = await decorated(req, token, req.match_info)
                return resp
            except auth.NotAuthorized:
                return web.HTTPForbidden()
            except Exception:
                traceback.print_exc()
                results = {'error': 'exception in ' + f.__name__}
                output = json_module.dumps(results, sort_keys=True, indent=4)
                return web.HTTPInternalServerError(text=output, content_type='application/json')
            finally:
                if host:
                    host.update(dec__connections=1)

        for method in methods:
            routes.append((method, uri, entrypoint))
        return decorated
    return decorator


def websocket(uri, auth_group=None):
    if auth_group is None:
        auth_group = []

    def decorator(f):
        @wraps(f)
        async def entrypoint(req):
            try:
                # ensure this member is authorized
                token = auth.Token(req.cookies.get('AUTH'))
                l = [g for g in auth_group if token.in_group(g)]
                if len(l) == 0:
                    raise auth.NotAuthorized()
                return await f(req)
            except auth.NotAuthorized:
                return web.HTTPForbidden()
            except Exception:
                traceback.print_exc()
                results = {'error': 'exception in ' + f.__name__}
                output = json_module.dumps(results, sort_keys=True, indent=4)
                return web.HTTPInternalServerError(text=output, content_type='application/json')

        routes.append(('GET', uri, entrypoint))
        return entrypoint
    return decorator


# Example usage:
# GET  /api/jobs
# POST /api/jobs     { 'action': 'install_service', 'host': 'mm198673-pc', ... }
@api('/api/jobs', methods=['GET', 'POST'], get={'status': None, 'wait': False}, auth_group=['human', 'agent'])
async def query_jobs(request, token, status, wait):
    if request.method == 'GET':
        query = {}
        if status:
            query['status'] = status

        if token.in_group('agent'):
            agent = Agent.objects.with_id(token.session_info['_id'])
            if not agent:
                raise auth.NotAuthorized()
            # are there any jobs for this agent?
            query.update({'agent': agent.id})
            jobs = list(Job.objects(**query))
            if not len(jobs) and wait is not False:
                # Now wait for jobs to be created
                try:
                    jobs = [(await Job.wait_next(query))]
                except asyncio.CancelledError:
                    return

        else:
            jobs = list(Job.objects(**query))
            if not len(jobs) and wait is not False:
                jobs = [(await Job.wait_next(query))]

        return jobs
    elif request.method == 'POST':
        # only humans are allowed to create new jobs
        token.require_group('human')
        json = await request.json()
        return Job(**json).save().id


# Example usage:
# GET  /api/jobs/<job>
# POST /api/jobs/<job>     { 'action': 'install_service', 'host': 'mm198673-pc', ... }
@api('/api/jobs/{job}', methods=['GET', 'PUT', 'DELETE'], objects={'job': Job}, auth_group=['human', 'agent'])
async def query_job(request, token, job):
    if request.method == 'GET':
        if token.in_group('agent'):
            # can only get jobs that are not completed and are for them
            if job['status'] in ("created", "pending") and str(job.agent.id) == token.session_info['_id']:
                return job
            else:
                raise auth.NotAuthorized()
        else:
            return job
    elif request.method == 'PUT':
        if token.in_group('agent'):
            # can only put jobs that are not completed and are for them
            if job.status in ("created", "pending") and str(job.agent.id) == token.session_info['_id']:
                json = await request.json()
                # whitelist legal fields
                if 'result' in json['action']:
                    job['action']['result'] = json['action']['result']
                if 'error' in json['action']:
                    job['action']['error'] = json['action']['error']
                if 'exception' in json['action']:
                    job['action']['exception'] = json['action']['exception']
                job['status'] = json.get('status', job.status)

                if job['status'] == "failed" and 'error' in job['action'] and job['action']['error'] == "no client":
                    # Force update the clients list
                    interface.get_clients(job.agent.host)
                    # find the rat
                    try:
                        iv_name = job['action']["rats"]["args"][0]
                        iv = Rat.objects(agent=job.agent, name=iv_name)
                        iv.modify(**{'active': False})
                    except KeyError:
                        log.warning("Could not find rat to remove for failed job")
                return job.save()
            else:
                raise auth.NotAuthorized()

        else:  # human
            # Update the job
            json = await request.json()
            if json['create_time']:
                json['create_time'] = datetime.strptime(json['create_time'], "%Y-%m-%dT%H:%M:%S.%f")
            return job.save()

    elif request.method == 'DELETE':
        token.require_group('human')
        return job.delete()


# Example usage:
# POST /api/clients
@api('/api/clients', methods=['POST'], auth_group=['agent'])
async def query_clients(request, token):
    json = await request.json()
    # pid, elevated, executable_path
    agen = Agent.objects.with_id(token.session_info['_id'])

    # Get the list of known rats
    complete_names = {iv.name: iv for iv in Rat.objects(host=agen.host)}
    # Filter list for living rats
    known_names = {}
    for name, element in complete_names.items():
        if element.active:
            known_names[name] = element
    # All of the currently running rats, as returned by the job
    active = {x['pid']: x for x in json}

    # Enumerate the active rats, and delete dead ones
    for name, iv in known_names.items():
        if name not in active:
            iv.modify(**{'active': False})
        else:
            a = active.pop(name)
            iv.update(**{'elevated': a['elevated'],
                         'executable': a['executable_path']})

    # Any new rats need to be added
    for name in active:
        Rat(**{'agent': agen,
                     'host': agen.host,
                     'name': name,
                     'elevated': active[name]['elevated'],
                     'executable': active[name]['executable_path'],
                     'username': active[name]['username'].lower(),
                     'active': True}).save()
    return None


# Example usage:
# GET  /api/networks
# POST /api/networks     { domain: 'mitre.org' }
@api('/api/networks', methods=['GET', 'POST'], auth_group=['human'])
async def query_networks(request):
    if request.method == 'GET':
        return Network.objects
    elif request.method == 'POST':
        json = await request.json()
        network = Network(**json).save()
        return network.id


@api('/api/networks/{network}', methods=['GET', 'DELETE'], objects={'network': Network}, auth_group=['human'])
async def query_network(request, network):
    if request.method == 'GET':
        return network
    elif request.method == 'DELETE':
        network.delete()


@api('/api/heartbeat', methods=['GET'], auth_group=['agent'])
async def agent_check_in(request, token):
    agen = Agent.objects.with_id(token.session_info['_id'])
    agen.modify(**{'check_in': datetime.now(timezone.utc), 'alive': True})
    return True


@api('/api/hosts', methods=['GET'], auth_group=['human'])
async def query_hosts(request):
    return Host.objects


@api('/api/domains', methods=['GET'], auth_group=['human'])
async def query_domains(request):
    return Domain.objects


@api('/api/domains/{domain}', methods=['GET'], objects={'domain': Domain}, auth_group=['human'])
async def query_domain(request, domain):
    return domain


@api('/api/domains/{domain}/hosts', methods=['GET'], objects={'domain': Domain}, auth_group=['human'])
async def query_domainhosts(request, domain):
    return Host.objects(domain=domain)


@api('/api/networks/{network}/hosts', methods=['GET'], objects={'network': Network}, auth_group=['human'])
async def query_networkhosts(request, network):
    return network.hosts


@api('/api/networks/{network}/hosts/{host}', methods=['GET', 'PUT', 'DELETE'],
     objects={'network': Network, 'host': Host}, auth_group=['human'])
async def query_networkhosthosts(request, network, host):
    if request.method == 'GET':
        return host
    elif request.method == 'PUT':
        network.modify(push__hosts=host)
    elif request.method == 'DELETE':
        network.modify(pull__hosts=host)


@api('/api/hosts/{host}/commands', methods=['GET', 'POST'], objects={'host': Host}, auth_group=['human'])
async def query_commands(request, host):
    if request.method == 'GET':
        if 'hostname' in request.GET:
            hosts = Host.objects(hostname=request.GET['hostname'])
            return [x.host_command_result() for x in Job.objects(host__in=hosts)]
        else:
            return [x.host_command_result() for x in Job.objects(host=host)]
    elif request.method == 'POST':
        json = await request.json()
        return interface.agent_shell_command(host, json['command_line']).id


@api('/api/hosts/{host}/commands/{job}', methods=['GET'], get={'wait': False},
     objects={'host': Host, 'job': Job}, auth_group=['human'])
async def query_command(request, wait, host, job):
    # start waiting for the job before reloading to avoid missing the update
    if wait is not False:
        try:
            await job.wait_till_completed()
        except JobException as e:
            log.warning(e.args)

    return job.host_command_result()


@api('/api/rats', methods=['GET'], auth_group=['human'])
async def query_ivs(request):
    query = {k: v for k, v in request.GET.items() if k == 'hostname'}
    return Rat.objects(**query)


@api('/api/rats/{rat}', methods=['GET'], objects={'rat': Rat}, auth_group=['human'])
async def query_iv(rat):
    return rat


@api('/api/rats/{rat}/commands', methods=['GET', 'POST'],
     objects={'rat': Rat}, auth_group=['human'])
async def query_ivcommands(request, rat):
    if request.method == 'GET':
        return [x.rat_command_result() for x in Job.objects(agent=rat.agent)]
    elif request.method == 'POST':
        json = await request.json()
        return Job.create_rat_command(rat, json["function"], **json["parameters"]).id


@api('/api/rats/{rat}/commands/{job}', methods=['GET'],
     get={'wait': False}, objects={'rat': Rat, 'job': Job}, auth_group=['human'])
async def query_ivcommand(request, wait, rat, job):
    # start waiting for the job before reloading to avoid missing the update
    if wait is not False:
        try:
            await job.wait_till_completed()
        except JobException as e:
            log.warning(e.args)
    return job.rat_result()


@api('/api/operations', methods=['GET'], auth_group=['human'])
async def query_operations(request):
    return Operation.objects


@api('/api/opcodes', methods=['GET'], auth_group=['human'])
async def get_opcodes(request):
    return Opcodes.arguments


@api('/api/networks/{network}/operations', methods=['GET', 'POST'], objects={'network': Network}, auth_group=['human'])
async def query_operations(request, network):
    if request.method == 'GET':
        return list(Operation.objects(network=network))
    elif request.method == 'POST':
        json = await request.json()
        if json['start_type'] == 'existing' and 'start_rat' not in json:
            return None
        json['network'] = network
        json['status'] = 'start'
        json['status_state'] = ''
        json['log'] = Log().save()
        # Get the adversary
        adversary = Adversary.objects.with_id(json['adversary'])
        json['steps'] = [x.name for x in adversary.steps]
        operation = Operation(**json).save()
        return operation.id


@api('/api/networks/{network}/operations/{operation}', methods=['GET', 'PUT', 'DELETE', 'PATCH'], get={'wait': False},
     objects={'network': Network, 'operation': Operation}, auth_group=['human'])
async def query_operation(request, network, operation, wait):
    if request.method == 'GET':
        if wait:
            wait = json_module.loads(wait)
            wait["id"] = operation.id
            log.info("Wait: {}".format(wait))
            # TODO fix race condition here
            new = list(Operation.objects(**wait))
            if len(new) == 0:
                del wait["id"]
                new = [await operation.wait(wait)]
            return new[0]
        return operation
    elif request.method == 'PUT':
        json = await request.json()
        json['network_id'] = network.id
        json['hosts'] = network.hosts
        return operation.update(**json)
    elif request.method == 'DELETE':
        if operation.status == "complete":
            return operation.delete()
        else:
            return "Cannot delete an operation that is not complete"
    elif request.method == 'PATCH':
        json = await request.json()
        operation.update(__raw__={'$set': json})


@api('/api/agents', methods=['GET'], auth_group=['human'])
async def query_agents(request):
    return Agent.objects


@api('/api/logs', methods=['GET'], auth_group=['human'])
async def query_logs(request):
    return Log.objects


@api('/api/logs/{log}', methods=['GET'], objects={'log': Log}, auth_group=['human'])
async def query_log(request, log):
    return log


@api('/api/agents/{agent}', methods=['GET'], objects={'agent': Agent}, auth_group=['human'])
async def query_agent(request, agent):
    return agent


@api('/api/adversaries', methods=['GET', 'POST'], auth_group=['human'])
async def query_adversaries(request):
    if request.method == 'GET':
        return Adversary.objects
    elif request.method == 'POST':
        json = await request.json()
        json['artifactlists'] = [Artifactlist.objects.with_id(x) for x in json['artifactlists']]
        json['steps'] = [CodedStep.objects.with_id(x) for x in json['steps']]
        return Adversary(**json).save().id


@api('/api/adversaries/{adversary}', methods=['GET', 'PUT', 'DELETE'], objects={'adversary': Adversary}, auth_group=['human'])
async def query_adversary(request, adversary):
    if request.method == 'GET':
        return adversary
    elif request.method == 'PUT':
        if (adversary.protected):
            new_adv = {}
            new_adv['name'] = adversary['name']
            new_adv['steps'] = adversary['steps']
            new_adv['exfil_method'] = adversary['exfil_method']
            new_adv['exfil_port'] = adversary['exfil_port']
            new_adv['exfil_address'] = adversary['exfil_address']
            new_adv['artifactlists'] = adversary['artifactlists']
            adversary = Adversary(**new_adv).save()
        # Update the adversary
        json = await request.json()
        json['artifactlists'] = [Artifactlist.objects.with_id(x) for x in json['artifactlists']]
        json['steps'] = [CodedStep.objects.with_id(x) for x in json['steps']]
        adversary.update(**json)
        return adversary.id
    elif request.method == 'DELETE':
        if not adversary.protected:
            return adversary.delete()


@api('/api/step', methods=['GET'], auth_group=['human'])
async def query_step(request):
    return CodedStep.objects


@api('/api/site_user', methods=['GET', 'POST'], auth_group=['admin'])
async def query_siteusers(request):
    if request.method == 'GET':
        return SiteUser.objects.only('username', 'groups', 'email', 'last_login')
    elif request.method == 'POST':
        json = await request.json()
        username = json['username']
        email = json.get('email', '')
        password = json.get('password', None)

        groups = ['human']
        if json.get('admin', False):
            groups.append('admin')

        return auth.register_user(username, groups, password=password, email=email).id


@api('/api/site_user/{user}', methods=['GET', 'DELETE'], objects={'user': SiteUser}, auth_group=['admin'])
async def query_siteuser(request, token, user):
    if request.method == 'GET':
        return user.only('username', 'groups', 'email', 'last_login')
    elif request.method == 'DELETE':
        if token.session_info['_id'] != str(user.id):
            return user.delete()


@api('/api/site_user/{user}/admin', methods=['PUT', 'DELETE'], objects={'user': SiteUser}, auth_group=['admin'])
async def query_siteuser_admin(request, token, user):
    if request.method == 'PUT':
        user.modify(push__groups='admin')
    elif request.method == 'DELETE':
        if SiteUser.objects(groups='admin').count() > 1 and token.session_info['_id'] != str(user.id):
            user.modify(pull__groups='admin')


@api('/api/site_user/{user}/password', methods=['POST'], objects={'user': SiteUser}, auth_group=['admin', 'human'])
async def query_siteuser_password(request, token, user):
    json = await request.json()
    if 'password' in json:
        if token.in_group('admin') or token.session_info['_id'] == str(user.id):
            auth.user_change_password(user, json['password'])


@api('/api/site_user/{user}/email', methods=['POST'], objects={'user': SiteUser}, auth_group=['admin'])
async def query_siteuser_email(request, user):
    json = await request.json()
    if 'email' in json:
        user.update(email=json['email'])


@api('/api/save_file', methods=['POST'], auth_group=['admin'])
async def save_file(request):
    json = await request.json()
    if 'edited' in json and 'file' in json:
        file_path = util.get_path(json['file'])
        if json['file'].startswith("[-d-]") or file_path is None:
            return
        core = util.encrypt_file(json['edited'])
        with open(file_path, 'wb') as handle:
            core.tofile(handle)


@api('/api/list_file', methods=['GET'], auth_group=['admin'])
async def list_files(request):
    return util.list_files()


@api('/api/load_file', methods=['POST'], auth_group=['admin'])
async def load_file(request):
    json = await request.json()
    if 'file' in json:
        file_path = util.get_path(json['file'])
        if json['file'].startswith("[-d-]") or json['file'] == '' or file_path is None:
            return
        if file_path.startswith('[m]'):
            return file_path
        with open(file_path, 'rb') as handle:
            data = handle.read()
        return util.decrypt_file(data)


@api('/api/load_psexec', methods=['GET'], auth_group=['admin'])
async def load_psexec(request):
    extern.load_psexec()
    Setting.objects.first().update(last_psexec_update=util.tz_utcnow())


@api('/api/load_attack', methods=['GET'], auth_group=['admin'])
async def load_attack(request):
    attack.refresh_attack()
    Setting.objects.first().update(last_attack_update=util.tz_utcnow())


@api('/api/update_depth', methods=['POST'], auth_group=['admin'])
async def update_recursion_limit(request):
    json = await request.json()
    if 'new_value' in json:
        Setting.objects.first().modify(recursion_limit=json['new_value'])


@api('/api/group_mimic', methods=['GET'], auth_group=['admin', 'human'])
async def group_coverage(request):
    temp_list = []
    core = {}
    for step in CodedStep.objects:
        for mapping in step.mapping:
            temp_list.append(mapping.technique)
    groups = AttackGroup.objects
    for entry in groups:
        temp = {}
        breakdown = {}
        decision = []
        for tech in entry.techniques:
            temp[tech.name] = (tech in temp_list)
            decision.append(tech in temp_list)
        breakdown['techniques'] = temp
        if (False not in decision) and (len(decision) > 2):
            breakdown['conclusion'] = 'Can Fully Emulate'
        else:
            breakdown['conclusion'] = 'Can Not Fully Emulate'
        core[entry.name] = breakdown
    return core


@api('/api/steps/{step}/mapping', methods=['POST', 'DELETE'], objects={'step': CodedStep}, auth_group=['human'])
async def post_step_mapping(request, step):
    if request.method == 'POST':
        json = await request.json()
        if 'tactics' not in json or 'technique' not in json:
            return

        tactics = json['tactics']
        technique = json['technique']

        try:
            tech = AttackTechnique.objects.with_id(technique)
            for tactic in tactics:
                tac = AttackTactic.objects.with_id(tactic)
                step.modify(push__mapping=TechniqueMapping(technique=tech, tactic=tac))
        except (TypeError, mongoengine.errors.ValidationError):
            return
    elif request.method == 'DELETE':
        json = await request.json()
        if 'tactic' not in json or 'technique' not in json:
            return

        tactic = json['tactic']
        technique = json['technique']

        try:
            tech = AttackTechnique.objects.with_id(technique)
            tac = AttackTactic.objects.with_id(tactic)
            for mapping in step.mapping:
                if mapping.tactic == tac and mapping.technique == tech:
                    step.modify(pull__mapping=mapping)
        except (TypeError, mongoengine.errors.ValidationError):
            return


@api('/api/steps/{step}/mapping/load_defaults', methods=['GET'], objects={'step': CodedStep},
     auth_group=['human'])
async def get_step_mapping_defaults(request, step):
    step.update(mapping=step.default_mapping)


@api('/api/attack_download.json', methods=['GET'], auth_group=['human'], headers={'Content-Disposition': 'attachment'})
async def get_all_attack_stuff(request):
    try:
        techniques = []
        for technique in AttackTechnique.objects:
            this_technique = technique.to_dict()
            this_technique['tactics'] = [x.name for x in technique.tactics]
            del this_technique['_id']
            techniques.append(this_technique)

        tactics = [x.to_dict() for x in AttackTactic.objects]
        for tactic in tactics:
            del tactic["_id"]

        return {"techniques": techniques, "tactics": tactics}
    except (TypeError, mongoengine.errors.ValidationError):
        return


@api('/api/generated/{function}', methods=["POST"], auth_group=['admin'])
async def generated_dispatcher(request):
    dispatched_function = request.match_info['function']
    request_json = await request.json()

    job = getattr(interface, dispatched_function)(**request_json)
    try:
        await job.wait_till_completed()
        return job.action['result']
    except JobException:
        return job.action['error']


@api('/api/artifactlists', methods=['GET', 'POST'], auth_group=['human'])
async def get_artifactlists(request):
    if request.method == 'GET':
        return Artifactlist.objects
    elif request.method == 'POST':
        if request.content_type == "application/json":
            content = await request.json()
        elif request.content_type == "text/x-yaml":
            try:
                content = format_yaml(await request.text())
            except (yaml.scanner.ScannerError, yaml.parser.ParserError):
                return web.Response(status=400, text="The yaml was not properly formatted")
        else:
            return web.Response(status=400)
        try:
            return Artifactlist(**content).save().id
        except (mongoengine.errors.FieldDoesNotExist, mongoengine.errors.ValidationError) as e:
            return web.Response(status=400, text=str(e))


@api('/api/artifactlists/{artifactlist}', methods=['GET', 'PUT', 'DELETE'], objects={'artifactlist': Artifactlist}, auth_group=['human'])
async def query_artifactlist(request, artifactlist):
    if request.method == 'GET':
        return artifactlist
    elif request.method == 'PUT':
        if request.content_type == "application/json":
            content = await request.json()
        elif request.content_type == "text/x-yaml":
            try:
                content = format_yaml(await request.text())
            except (yaml.scanner.ScannerError, yaml.parser.ParserError):
                return web.Response(status=400, text="The yaml was not properly formatted")
        else:
            return web.Response(status=400)
        try:
            artifactlist.update(**content)
            return artifactlist.id
        except (mongoengine.errors.FieldDoesNotExist, mongoengine.errors.ValidationError) as e:
            return web.Response(status=400, text=str(e))
    elif request.method == 'DELETE':
        return artifactlist.delete()


@api('/api/parse_artifactlist', methods=['POST'], auth_group=['human'])
async def get_parse_artifactlist(request):
    try:
        parsed = format_yaml(await request.text())
        Artifactlist(**parsed)
        return parsed
    except (yaml.scanner.ScannerError, yaml.parser.ParserError) as e:
        return web.Response(status=400, text="The yaml was not properly formatted: \n" + str(e.problem_mark) + '\n  ' + str(e.problem))
    except (mongoengine.errors.FieldDoesNotExist, mongoengine.errors.ValidationError) as e:
        return web.Response(status=400, text=str(e))


def format_yaml(yaml_content):
    parsed = yaml.load(yaml_content)
    cleaned = {}
    for k, v in parsed.items():
        if isinstance(v, list) and len(v) == 1 and v[0] is None:
            cleaned[k] = []
        else:
            cleaned[k] = v

    return cleaned


@api('/api/bsf/{log}', methods=['GET'], objects={'log': Log}, auth_group=['human'],
     headers={'Content-Disposition': 'attachment; filename=\"bsf.json\"'})
async def query_bsf(request, log):
    return log["event_stream"]


@websocket('/websocket', auth_group=["human"])
async def wb_operation(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    def write_websocket(data):
        if not ws.closed:
            ws.send_bytes(data)
        else:
            raise RuntimeError

    srv = ddp.DDPServer(write_websocket)
    srv.register_collection("operation", Operation)
    srv.register_collection("domain", Domain)
    srv.register_collection("host", Host)
    srv.register_collection("network", Network)
    srv.register_collection("rat", Rat)
    srv.register_collection("observed_rat", ObservedRat)
    srv.register_collection("observed_host", ObservedHost)
    srv.register_collection("observed_file", ObservedFile)
    srv.register_collection("observed_schtask", ObservedSchtask)
    srv.register_collection("job", Job)
    srv.register_collection("log", Log)
    srv.register_collection("adversary", Adversary)
    srv.register_collection("step", CodedStep)
    srv.register_collection("active_connection", ActiveConnection)
    srv.register_collection("agent", Agent)
    srv.register_collection("attack_technique", AttackTechnique)
    srv.register_collection("attack_tactic", AttackTactic)
    srv.register_collection("attack_list", AttackList)
    srv.register_collection("attack_group", AttackGroup)
    srv.register_collection("setting", Setting)
    srv.register_collection("artifactlist", Artifactlist)

    request.app['websockets'].append(ws)
    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT or msg.type == aiohttp.WSMsgType.BINARY:
                srv.parse_message(msg.data)
            elif msg.type == aiohttp.WSMsgType.ERROR:
                log.debug('ws connection closed with exception {}'.format(ws.exception()))
    finally:
        request.app['websockets'].remove(ws)

    log.debug('websocket connection closed')
    return ws


def init(app):
    # setup the generated endpoints
    for method, uri, func in routes:
        app.router.add_route(method, uri, func)
