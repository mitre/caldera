import argparse
import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from subprocess import Popen


def spawn_proxy_service(proxy, conf_path):
    if proxy == 'haproxy':
        proxy_args = [proxy, '-V', '-f', conf_path]
    elif proxy == 'nginx':
        proxy_args = [proxy, '-V', '-c', conf_path]
    else:
        print('Invalid or unsupported proxy selected.')
        return
    try:
        return Popen(proxy_args)
    except FileNotFoundError:
        print('%s is could not be started because the path does not exist.' % proxy)


def render_proxy_config(cfg):
    env = Environment(
        loader=FileSystemLoader(searchpath='conf')
    )
    template = env.get_template(cfg['proxy_template'])
    rendered = '%s-%s-rendered.conf' % (cfg['proxy_name'], datetime.now().strftime('%Y%H%M%S'))
    with open(os.path.abspath(os.path.join('conf', rendered)), 'w') as f:
        f.write(template.render(cert_path=cfg['cert_path'],
                                http_port=cfg['http_port'],
                                https_port=cfg['https_port'],
                                caldera_ip=cfg['caldera_ip'],
                                caldera_port=cfg['caldera_port']))
    print("%s config rendered at %s" % (cfg['proxy_name'], rendered))
    return os.path.join('conf', rendered)


if __name__ == '__main__':
    parser = argparse.ArgumentParser('Deploy a reverse proxy/TLS termination server')
    parser.add_argument('-P', '--proxyfile', required=False, default='haproxy', help='Specify a proxy to use [haproxy, '
                                                                                     'nginx, etc] (default: haproxy)')
    parser.add_argument('-C', '--cert_path', required=True, default='', help='Absolute path to server certificate (cert'
                                                                             ' & key)')
    parser.add_argument('-U', '--http_port', required=True, default=80, help='Provide a port on which to run http'
                                                                             ' (default: 80)')
    parser.add_argument('-S', '--https_port', required=True, default=443, help='Provide a port on which to run https'
                                                                               ' (default: 443)')
    parser.add_argument('-CI', '--caldera_ip', required=True, default='localhost', help='IP address of the caldera'
                                                                                        ' server (default: localhost')
    parser.add_argument('-CP', '--caldera_port', required=True, default=8888, help='Port on which the caldera server is'
                                                                                   'serving http (default: 8888)')
    parser.add_argument('-L', '--launch_proxy', required=False, default=False, help='Set True/False to launch the proxy'
                                                                                    ' (default:false)')
    args = parser.parse_args()
    proxy_cfg = dict(proxy_path=os.path.abspath('conf'),
                     proxy_name=args.proxyfile,
                     proxy_template='%s-template.conf' % args.proxyfile,
                     cert_path=os.path.abspath(args.cert_path),
                     http_port=args.http_port,
                     https_port=args.https_port,
                     caldera_ip=args.caldera_ip,
                     caldera_port=args.caldera_port)
    proxy_conf = render_proxy_config(proxy_cfg)
    if args.launch_proxy:
        try:
            proxy_svr = spawn_proxy_service(args.proxyfile, proxy_conf)
            print("%s started with PID %s" % (args.proxyfile, proxy_svr.pid))
        except KeyboardInterrupt:
            pass
