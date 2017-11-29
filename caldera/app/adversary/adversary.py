# word_lists containing adversary used words pulled from threat intelligence reports.
# Using generic python lists for now

import random
from collections import defaultdict
from ..engine.objects import Adversary


class AdversaryProfile(object):
    def __init__(self, adversary: Adversary):
        self._default_artifact_list = {'executables': ["commander.exe"],
                                       'dlls': ["commander.dll"],
                                       'services': ["caldera"],
                                       'schtasks': ["caldera4eva"],
                                       'file_paths': ["\\"]}
        self._default_exfil_method = {'method': 'rawtcp',
                                      'address': '127.0.0.1',
                                      'port': '8889'}

        # populate the adversary artifactlists if needed
        if len(adversary.artifactlists):
            self._artifact_list = defaultdict(set)
            for artifact_list in adversary.artifactlists:
                for k in self._default_artifact_list:
                    self._artifact_list[k] |= set(getattr(artifact_list, k))
        else:
            self._artifact_list = self._default_artifact_list

        for k, v in self._artifact_list.items():
            self._artifact_list[k] = list(v)

        # populate the adversary exfil method if needed
        if adversary.exfil_method != "":
            self._exfil_method = {'method': adversary.exfil_method,
                                  'address': adversary.exfil_address,
                                  'port':  adversary.exfil_port}
        else:
            self._exfil_method = self._default_exfil_method

    def get_executable_word(self):
        return random.choice(self._artifact_list['executables'])

    def get_dll_word(self):
        return random.choice(self._artifact_list['dlls'])

    def get_service_word(self):
        return random.choice(self._artifact_list['services'])

    def get_scheduled_task_word(self):
        return random.choice(self._artifact_list['schtasks'])

    def get_file_path_word(self):
        return random.choice(self._artifact_list['file_paths'])

    def get_exfil_method(self):
        return self._exfil_method['method']

    def get_exfil_address(self):
        return self._exfil_method['address']

    def get_exfil_port(self):
        return self._exfil_method['port']
