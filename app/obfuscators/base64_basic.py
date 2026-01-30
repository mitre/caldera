from base64 import b64encode

from app.utility.base_obfuscator import BaseObfuscator


class Obfuscation(BaseObfuscator):

    @property
    def supported_platforms(self):
        return dict(
            windows=['psh'],
            darwin=['sh'],
            linux=['sh']
        )

    """ EXECUTORS """

    def psh(self, link):
        recoded = b64encode(self.decode_bytes(link.command).encode('UTF-16LE'))
        return 'powershell -Enc %s' % recoded.decode('utf-8')

    @staticmethod
    def sh(link):
        return 'eval "$(echo %s | base64 --decode)"' % str(link.command.encode(), 'utf-8')
