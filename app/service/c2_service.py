from app.utility.base_service import BaseService
import multiprocessing as mp


class C2Service(BaseService):

    def __init__(self):
        self.log = self.add_service('c2_svc', self)
        self.c2_channels = []
        self.running = False
        mp.set_start_method('spawn')
        self.q = mp.Queue()

    def start_channel(self, c2_channel):
        if c2_channel.c2_type == 'active':
            if not self.running:
                self._start_active_channel_process()
            self.q.put(c2_channel)
        elif c2_channel.c2_type == 'passive':
            # TODO: not yet implemented
            pass

    """ PRIVATE """

    def _start_active_channel_process(self):
        p = mp.Process(target=self._handle_c2_channels, args=(self.q,))
        p.start()
        self.running = True

    @staticmethod
    def _handle_c2_channels(queue):
        while True:
            c2 = queue.get()
            c2.handle_beacon()
            queue.put(c2)
