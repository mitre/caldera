class Keyword(object):
    def __init__(self, obj=None):
        self.obj = obj


class KeywordVar(object):
    def __init__(self, obj):
        self.obj = obj


class MetaName(type):
    @property
    def coded_name(cls):
        return "{0}: {1}".format(cls.display_name, cls.attack_string(cls.attack_mapping))


class Step(object, metaclass=MetaName):
    display_name = "default"
    summary = ""

    preconditions = []
    postconditions = []
    hints = []
    not_equal = []
    value = 1
    deterministic = False
    preproperties = []
    postproperties = []
    significant_parameters = []
    attack_mapping = []
    cddl = ''


    @staticmethod
    def description(*args):
        raise NotImplementedError()

    @staticmethod
    async def action(operation, *args):
        raise NotImplementedError()

    @staticmethod
    async def cleanup():
        return

    @staticmethod
    def attack_string(mapping: list) -> str:
        """This function converts an attack mapping set to a string for label purposes.
        """
        final = ""
        slip = False
        for i in range(0,len(mapping)):
            if not slip:
                k = mapping[i]
                if (i < (len(mapping) - 1)):
                    if (mapping[i][1].startswith(mapping[i+1][1])):
                        #combine techniques if same tactic
                        k = (" & ".join((mapping[i][0],mapping[i+1][0])), k[1])
                        slip = True
                temp = ", ".join(k)
                final = final + temp + " | "
            else:
                slip = False
        return "[" + final[:-3] + "]"


class OPUser(Keyword):
    pass


class OPHost(Keyword):
    pass


class OPDomain(Keyword):
    pass


class OPFile(Keyword):
    pass


class OPCredential(Keyword):
    pass


class OPShare(Keyword):
    pass


class OPSchtask(Keyword):
    pass


class OPTimeDelta(Keyword):
    pass


class OPRat(Keyword):
    pass


class OPPersistence(Keyword):
    pass


class OPService(Keyword):
    pass


class OPRegKey(Keyword):
    pass


class OPProcess(Keyword):
    pass


class OPOSVersion(Keyword):
    pass


class OPVar(KeywordVar):
    pass
