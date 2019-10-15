
def mimikatz(blob, **kwargs):
    matched_facts = []
    list_lines = blob.split('\n')
    for i, line in enumerate(list_lines):
        if 'Username' in line and '(null)' not in line:
            value = line.split(':')[1].strip()
            if value[-1] is not '$':
                username_fact = dict(fact='host.user.name', value=value)
                if 'Password' in list_lines[i + 2] and '(null)' not in list_lines[i + 2]:
                    password_fact = dict(fact='host.user.password', value=list_lines[i + 2].split(':')[1].strip())
                    matched_facts.append(password_fact)
                    matched_facts.append(username_fact)
    return matched_facts
