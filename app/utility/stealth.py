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
    hidden_ps1 = '''robinhood /C "s{0}v {1} -;s{0}v {2} e{0}c;s{0}v {3} ((g{0}v {4}).value.toString()+(g{0}v {5}).value.toString());robinhood (g{0}v {6}).value.toString() (\''''.format(
        mangle_quotes, ran1, ran2, ran3, ran1, ran2, ran3) + empty_string + ")" + '"'
    return hidden_ps1.replace('robinhood', 'powershell')


def obfuscate_bash(code):
    return 'eval "$(echo %s | base64 --decode)"' % str(b64encode(code.encode()), 'utf-8')
