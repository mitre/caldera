import os
from .engine.objects import SiteUser
from .engine.database import subjectify
from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import binascii
import base64
from .util import tz_utcnow


_backend = default_backend()
auth_key = None

# age is valid for one day
max_age = 60*60*24*1


class NotAuthorized(Exception):
    pass


class Token(object):
    def __init__(self, session_blob):
        self._blob = session_blob

        if self._blob is None:
            raise NotAuthorized
        try:
            s = URLSafeTimedSerializer(auth_key)
            self.session_info = s.loads(self._blob, max_age=max_age)
        except (BadSignature, SignatureExpired, UnicodeDecodeError, binascii.Error):
            raise NotAuthorized

    def require_group(self, g):
        if g not in self.session_info['groups']:
            raise NotAuthorized()

    def in_group(self, g):
        return g in self.session_info['groups']


# _verify the glob against the kdf key with the given salt
def _verify(glob, key, salt):
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000, backend=_backend)
    try:
        kdf.verify(glob, key)
        return True
    except InvalidKey:
        return False


# creates a hash and salt from the given glob
def _create_hash(glob):
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000, backend=_backend)
    return salt, kdf.derive(glob)


# registers a new user with the password and is a member of the given groups
def register_user(username, groups, email=None, password=None):
    if not password:
        password = base64.b64encode(os.urandom(64)).decode("ascii")
    salt, key = _create_hash(password.encode())
    return SiteUser(username=username, password=key, salt=salt, groups=groups, email=email).save()


# returns a session identifier for a generic user that is a member of the given groups and has the given attributes
def login_generic(groups, attrs) -> str:
    # does not handle any sessions a user is already logged into
    serializer = URLSafeTimedSerializer(auth_key)
    temp = attrs.copy()
    temp.update({'groups': groups})
    return serializer.dumps(subjectify(temp))


def login_user(username, password) -> str:
    """
    returns a session blob for a valid user or None for an invalid user

    Args:
        user:
        password:

    Returns:
        a session blob for a valid user or None for an invalid user
    """
    try:
        siteuser = SiteUser.objects.get(username=username)
    except SiteUser.DoesNotExist:
        return None

    if not _verify(password.encode(), siteuser.password, siteuser.salt):
        return None

    siteuser.update(last_login=tz_utcnow())

    # does not handle any sessions a user is already logged into
    serializer = URLSafeTimedSerializer(auth_key)
    return serializer.dumps({'_id': str(siteuser.id), 'username': siteuser.username, 'groups': siteuser.groups})


def username_exists(username: str):
    """Checks if the username exists

    Args:
        user: the user

    Returns:
        True if they exist else False
    """
    try:
        SiteUser.objects.get(username=username)
        return True
    except SiteUser.DoesNotExist:
        return False


def user_change_password(user: SiteUser, password):
    """Changes the users password

    Args:
        user: the user
        password: the password

    Returns:
        Nothing
    """
    salt, key = _create_hash(password.encode())
    user.update(password=key, salt=salt)
