import msgpack

from app.objects.base_object import BaseObject


class Result(BaseObject):

    @property
    def unique(self):
        return True

    def display(self):
        return self.clean(dict(link_id=self.link_id, output=self.output, parsed=self.parsed))

    def __init__(self, link_id, output=None, parsed=False):
        self.link_id = link_id
        self.output = output
        self.parsed = parsed

    def store(self, ram):
        if self.output:
            with open('data/results/%s' % int(float(self.link_id)), 'wb') as out:
                out.write(msgpack.packb(self.output, use_bin_type=True))
