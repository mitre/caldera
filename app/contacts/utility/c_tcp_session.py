from app.utility.base_object import BaseObject


class TCPSession(BaseObject):

    @property
    def unique(self):
        return self.hash('%s' % self.paw)

    def __init__(self, id, paw, reader, writer):
        super().__init__()
        self.id = id
        self.paw = paw
        self._reader = reader
        self._writer = writer

    def store(self, ram):
        existing = self.retrieve(ram['sessions'], self.unique)
        if not existing:
            ram['sessions'].append(self)
            return self.retrieve(ram['sessions'], self.unique)
        return existing

    def write_bytes(self, input):
        """Wrapper for self._writer.write"""

        return self._writer.write(input)

    def read_bytes(self, buffer):
        """Wrapper for self._reader.read"""

        return self._reader.read(buffer)
