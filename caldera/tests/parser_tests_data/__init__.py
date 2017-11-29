import pathlib

parser_tests_data_dir = pathlib.Path(__file__).parent


def get_data(filename: str) -> str:
    res = None
    # Line-ending contortions are below to avoid interference from git settings
    with open(str(parser_tests_data_dir / filename), 'r', newline=None) as f:
        res = f.read().replace('\n', '\r\n')
    return res


dirlist_collect = get_data("dirlist_collect.output")
mimi_logonpasswords3 = get_data("mimi_logonpasswords3.output")
mimi_logonpasswords4 = get_data("mimi_logonpasswords4.output")
mimi_pth1 = get_data("mimi_pth1.output")
mimi_pth2 = get_data("mimi_pth2.output")
mimi_pth3 = get_data("mimi_pth3.output")
nbtstat = get_data("nbtstat.output")
powerview_GetDomainComputer = get_data("powerview_GetDomainComputer.output")
powerview_GetNetLocalGroupMember = get_data("powerview_GetNetLocalGroupMember.output")
reg_query = get_data("reg_query.output")
service_file_permissions = get_data("service_file_permissions.output")
service_paths = get_data("service_paths.output")
service_permissions = get_data("service_permissions.output")
systeminfo_local = get_data("systeminfo_local.output")
tasklist_csv_verbose = get_data("tasklist_csv_verbose.output")
tasklist_modules_csv = get_data("tasklist_modules_csv.output")
tasklist_service_csv = get_data("tasklist_service_csv.output")
tasklist_system_csv_verbose = get_data("tasklist_system_csv_verbose.output")
timestomp = get_data("timestomp.output")
wmic_create = get_data("wmic_create.output")


