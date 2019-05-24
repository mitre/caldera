import jwt
import random
import string
from datetime import datetime
from aiohttp import web
from aiohttp_session import get_session


async def authenticated_login(auth_svc, *args):
    async def deco(*args):
        auth_handle = auth_svc
        default_login = auth_handle.redirect_landing
        try:
            session = await get_session(args[0])
            if 'app_token' not in session or 'ref_key' not in session:
                return web.HTTPFound(default_login)
            webauth_data = await auth_handle.data_svc.dao.get('webauth', dict(ref_insert=session['ref_key']))
            token_data = jwt.decode(session['app_token'], webauth_data[0]['passkey'], algorithm='HS256')
        except (jwt.InvalidSignatureError, IndexError):
            return web.HTTPFound(default_login, reason='Token Key Invalid - Please log in again.')
        except jwt.DecodeError:
            # Flawed decryption - occasionally happens, force re-auth
            token_data = []
        except KeyError:
            return web.HTTPFound(default_login)
        if 'issued' not in token_data or (datetime.now().timestamp() - webauth_data[0]['issued'] > 28800):  # 8 hrs
            return web.HTTPFound(default_login, reason='Outdated Token - Please log in again.')
        return False
    return await deco(*args)


async def login_session(auth_svc, session, user):
    key = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(256))
    ref_key = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(16))
    issue_date = datetime.now().timestamp()
    token_data = jwt.encode(dict(user=user, issued=issue_date), key, algorithm='HS256')
    await auth_svc.data_svc.dao.create('webauth', dict(ref_insert=ref_key, passkey=key, issued=issue_date))
    session['app_token'] = token_data.decode()
    session['ref_key'] = ref_key


async def logout_session(auth_svc, session):
    webauth_data = await auth_svc.data_svc.dao.get('webauth', dict(ref_insert=session['ref_key']))
    try:
        token_data = jwt.decode(session['app_token'], webauth_data[0]['passkey'], algorithm='HS256')
        await auth_svc.data_svc.dao.update('webauth', 'issued', token_data['issued'], dict(issued=0))
    except jwt.DecodeError:
        pass
    session['ref_key'] = ''
    session['app_token'] = ''


async def reset_password(auth_svc, submission, session):
    webauth_data = await auth_svc.data_svc.dao.get('webauth', dict(ref_insert=session['ref_key']))
    token_data = jwt.decode(session['app_token'], webauth_data[0]['passkey'], algorithm='HS256')
    if not await auth_svc.login(token_data.get('user'), submission.get('old')):
        return web.json_response('INVALID PASSWORD')
    s1, k1 = await auth_svc.generate(submission.get('new'))
    await auth_svc.data_svc.dao.update('users', 'username', token_data.get('user'), dict(password=k1, salt=s1))
    return web.json_response('PASSWORD CHANGED SUCCESSFULLY')

