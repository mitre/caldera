class Handler:

    TAGS = dict(
        process=lambda m: process_handler(m)
    )

    def __init__(self, tag):
        self.func = self.TAGS[tag]

    def handle(self, message):
        self.func(message)


def process_handler(message):
    print('Received: %s' % message)
