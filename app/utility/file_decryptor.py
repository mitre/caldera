import os
import yaml
import base64
import argparse

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

description = """
This script is for the purpose of decrypting encrypted files that are exfilled by caldera
default output files are created in the same dir as input file and postpended with '_decrypted'

examples:
python file_decryptor.py filename
    - uses only the defaults and will use the current caldera config if ran from the app/utility dir
python file_decryptor.py -c default.yml filename
    - you can specify a specific config to pass in as well
python file_decryptor.py -k ADMIN123 -s WORDSMOREWORDS filename
    - you can also forgo a config and directly pass in the key and salt values
python filedescriptor.py -b64 ../../data/results/554667-212609
    - enables b64 decoding of the stored value as well (useful for results files)
"""
FILE_ENCRYPTION_FLAG = '%encrypted%'


def get_encryptor(salt, key):
    generated_key = PBKDF2HMAC(algorithm=hashes.SHA256(),
                               length=32,
                               salt=bytes(salt, 'utf-8'),
                               iterations=2 ** 20,
                               backend=default_backend())
    return Fernet(base64.urlsafe_b64encode(generated_key.derive(bytes(key, 'utf-8'))))


def read(filename, encryptor):
    with open(filename, 'rb') as f:
        buf = f.read()
    if buf.startswith(bytes(FILE_ENCRYPTION_FLAG, encoding='utf-8')):
        buf = encryptor.decrypt(buf[len(FILE_ENCRYPTION_FLAG):])
    return buf


def decrypt(filename, configuration, output_file=None, b64decode=False):
    encryptor = get_encryptor(configuration['crypt_salt'], configuration['encryption_key'])
    if not output_file:
        output_file = filename + '_decrypted'
    with open(output_file, 'wb') as f:
        if b64decode:
            f.write(base64.b64decode(read(filename, encryptor)))
        else:
            f.write(read(filename, encryptor))
    print(f'file decrypted and written to {output_file}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-k', '--key')
    parser.add_argument('-s', '--salt')
    parser.add_argument('-c', '--config', default='../../conf/default.yml')
    parser.add_argument('-b64', action='store_true', help='b64 decode data after decryption')
    parser.add_argument('input')
    parser.add_argument('output', nargs='?')

    args = parser.parse_args()
    config = {}
    if args.key and args.salt:
        config = dict(crypt_salt=args.salt, encryption_key=args.key)
    elif args.config and os.path.exists(args.config):
        with open(args.config, encoding='utf-8') as conf:
            config = list(yaml.load_all(conf, Loader=yaml.FullLoader))[0]
    else:
        print('please pass in a path to the caldera config file or a crypt salt and api key for decryption')

    decrypt(args.input, config, output_file=args.output, b64decode=args.b64)
