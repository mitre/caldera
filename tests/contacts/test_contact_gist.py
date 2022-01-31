from app.contacts.contact_gist import Contact
from app.utility.base_world import BaseWorld


class TestContactGist:

    async def test_retrieve_config(self, app_svc):
        BaseWorld.apply_config(name='main', config={'app.contact.gist': 'arandomkeythatisusedtoconnecttogithubapi',
                                                    'plugins': ['sandcat', 'stockpile'],
                                                    'crypt_salt': 'BLAH',
                                                    'api_key': 'ADMIN123',
                                                    'encryption_key': 'ADMIN123',
                                                    'exfil_dir': '/tmp'})
        gist_c2 = Contact(app_svc.get_services())
        await gist_c2.start()
        assert gist_c2.retrieve_config() == 'arandomkeythatisusedtoconnecttogithubapi'
