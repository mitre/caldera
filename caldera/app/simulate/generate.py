class GenerateError(Exception):
    pass


def generate_circular(world):
    users = world.get_objects_by_type('OPUser')

    domain_users = [x for x in users if x.domain is not None]
    hosts = world.get_objects_by_type('OPHost')

    if len(domain_users) < len(hosts):
        raise GenerateError('Not enough users to produce a circular network')

    for i in range(0, len(hosts)):
        # assign the i - 1 admin
        hosts[i - 1]['admins'] = [domain_users[i]]

        # cache the i - 1 creds on the i host
        hosts[i]['cached_creds'] = [domain_users[i]['cred']]
