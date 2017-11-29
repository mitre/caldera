import os
from datetime import datetime, timezone
import subprocess
import yaml
import requests
import array
from typing import Dict, List


class CaseException(Exception):
    pass


def tz_utcnow():
    return datetime.now(timezone.utc)


def git_commit_hash() -> str:
    """
    Checks the current directory for a git commit

    Returns:
        The commit id or "" if none could be found

    """
    try:
        return subprocess.check_output(["git", "show", "-s", "--quiet", "--format=%H"]).decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def nested_cmp(state, *filters):
    """
    Performs a comparison between the 'state' object and a set of filters
    Args:
        state: the state either a dictionary or a string
        *filters: one or more filters. If state is a dictionary, filters is treated like a list of dictionaries where
        each field is compared to the state. If state is not a dictionary, state is checked to see if it is in filters.

    Returns: True if the state matches the filters, otherwise False

    """
    if len(filters) == 0:
        return True
    if not isinstance(state, dict):
        return state in filters
    for f in filters:
        for k, v in f.items():
            if k not in state:
                break
            elif isinstance(v, tuple):
                if not nested_cmp(state[k], *v):
                    break
            elif isinstance(v, dict):
                if not nested_cmp(state[k], v):
                    break
            elif v != state[k]:
                break
        else:
            return True
    return False


def build_cagent_conf(hostname, port, ssl_cert):
    prepend_spaces = '\n'.join(['  ' + x for x in ssl_cert.splitlines()])
    t = r"""url_root: https://{}:{}
verify_hostname: false
cert: |
{}
logging_level: debug"""
    return t.format(hostname, port, prepend_spaces)


def relative_path(dunder_file, relative_path):
    directory = os.path.dirname(dunder_file)
    return os.path.join(directory, relative_path)


def load_connection_data(mode):
    """
    Retrieves proxy and cert settings
    Args:
        mode: specific proxy/cert combination to use
    Returns:
        cert: path to configured cert
        proxies: dictionary containing proxy data

    """
    conf_file_path = '../conf/settings.yaml'
    abs_conf_file_path = relative_path(__file__, conf_file_path)
    with open(abs_conf_file_path, 'r') as f:
        settings = yaml.load(f.read())
    if mode not in settings['proxy']:
        mode = 'default'
    try:
        proxies = {}
        proxies['http'] = settings['proxy'][mode]['http']
        proxies['https'] = settings['proxy'][mode]['https']
        if proxies['https'] == '' and proxies['http'] == '':
            proxies = None
    except KeyError:
        proxies = None
    try:
        cert = settings['proxy'][mode]['cert']
        if cert == '':
            cert = True
    except KeyError:
        cert = True
    return cert, proxies


def grab_site(site: str, params, mode: str, stream: bool):
    """
    Contacts a website for content
    Args:
        site: the site to visit
        params: requests parameters to use
        mode: specific proxy/cert combination to use
        stream: treat the connection as a data stream
    Returns:
        requests object containing the website's response
    """
    cert, proxies = load_connection_data(mode)
    return requests.get(site, params=params, proxies=proxies, verify=cert, stream=stream)


def encrypt_file(file: str) -> array:
    """
    Encrypts a file for transfer to the Caldera Agents and Rats
    Args:
        file: The file contents to encrypt
    Returns:
        arr: The encrypted file contents
    """
    key = [0x32, 0x45, 0x32, 0xca]
    arr = array.array('B', file.encode())

    for i, val in enumerate(arr):
        cur_key = key[i % len(key)]
        arr[i] = val ^ cur_key

    return arr


def decrypt_file(enc_file: str) -> str:
    """
    Decrypts a transfer-ready file
    Args:
        enc_file: The file contents to decry[t
    Returns:
        The unencrypted file contents
    """
    key = [0x32, 0x45, 0x32, 0xca]
    arr = array.array('B', enc_file)

    for i, val in enumerate(arr):
        cur_key = key[i % len(key)]
        arr[i] = val ^ cur_key
    return ''.join(map(chr,arr))


def list_files() -> array:
    """
    Recursively lists files starting in the Caldera files folder
    Args:
        None
    Returns:
        filelist: jsTree ready dictionary containing mapping of the files folder and its contents
    """
    filelist = []
    directory = os.path.dirname(os.path.realpath(__file__))
    directory = os.path.join(directory, '..', 'files')
    cycle = []
    dirlist = []
    for (current_loc, dirc, filenames) in os.walk(directory):
        cycle.extend(filenames)
        dirlist.extend(dirc)
        for filename in cycle:
            filelist.append({"id": os.path.join(current_loc[current_loc.find('files'):][6:], filename),
                                 "parent" : get_parent(current_loc), "text" : filename, "icon" : "glyphicon"
                                 " glyphicon-file"})
        for entry in dirc:
            filelist.append({"id" : "[-d-]" + entry, "parent" : get_parent(current_loc), "text" : "["
                             "Directory] " + entry, "icon" : "glyphicon glyphicon-folder-open"})
        cycle = []
    return filelist


def get_parent(file_path: str):
    """
    Support function for list_files - identifies the parent folder of a given file path
    Args:
        file_path: the file path to process
    Returns:
        jsTree ready parent folder string
    """
    fragments = file_path.split(os.path.sep)
    if fragments[-1] == 'files':
        return '#'
    return "[-d-]" + fragments[-1]


def get_path(file_name: str):
    """
    Calculates the direct path to a given file, while remaining resistant to directory traversal
    Args:
        file_name: the file to identify the direct path of
    Returns:
        filepath |[None]: the direct path to the file requested, or none if it is outside the files directory
    """
    start_path = os.path.abspath(os.path.join(os.path.realpath(__file__), '..', '..', 'files'))
    target_path = os.path.relpath(os.path.join(start_path, file_name), start_path)
    file_path = os.path.abspath(os.path.join(start_path, target_path))
    if os.path.commonprefix([file_path,start_path]).startswith(start_path):
            return file_path
    return None


def unique_list_of_dicts(dict_list: List[Dict]):
    return list(map(dict, set(tuple(sorted(x.items())) for x in dict_list)))
