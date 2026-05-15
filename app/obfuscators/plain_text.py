from app.utility.base_obfuscator import BaseObfuscator


class Obfuscation(BaseObfuscator):

    def run(self, link, **kwargs):
        return self.decode_bytes(link.command)
