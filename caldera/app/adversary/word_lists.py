# artifact_lists containing adversary used words pulled from threat intelligence reports.
# Using generic python lists for now

import random

executables = ["doc.exe", "test.exe", "install.exe", "vmware_manager.exe", "csrs.exe", "hpinst.exe"]
dlls = ["IePorxyv.dll", "msupd.dll", "ieupd.dll", "mgswizap.dll", "lsasrvi.dll", "iprpp.dll", "hello32.dll",
        "amdcache.dll"]
services = ["myservice"]
scheduled_tasks = ["mysc"]
file_paths = ["C:\\"]


def get_executable():
    return random.choice(executables)


def get_dll():
    return random.choice(dlls)


def get_service():
    return random.choice(services)


def get_scheduled_task():
    return random.choice(scheduled_tasks)


def get_file_path():
    return random.choice(file_paths)
