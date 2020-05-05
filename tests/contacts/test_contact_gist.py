from app.contacts.contact_gist import Gist
from app.utility.base_world import BaseWorld


class TestContactGist:

    def test_retrieve_config(self, loop, app_svc):
        BaseWorld.apply_config(name='main', config={'app.contact.gist': 'arandomkeythatisusedtoconnecttogithubapi',
                                                    'plugins': ['sandcat', 'stockpile'],
                                                    'crypt_salt': 'BLAH',
                                                    'api_key': 'ADMIN123',
                                                    'encryption_key': 'ADMIN123',
                                                    'exfil_dir': '/tmp'})
        internal_app_svc = app_svc(loop)
        gist_c2 = Gist(internal_app_svc.get_services())
        loop.run_until_complete(gist_c2.start())
        assert gist_c2.retrieve_config() == 'arandomkeythatisusedtoconnecttogithubapi'
