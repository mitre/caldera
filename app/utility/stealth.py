from base64 import b64encode
from random import randint, choice


def obfuscate_ps1(code):
    ran1 = 'P4j'
    ran2 = 'X5x'
    ran3 = '5x4'

    avblah = b64encode(code.encode('utf_16_le'))
    avsux = randint(4000, 5000)
    avnotftw = [avblah[i: i + avsux] for i in range(0, len(avblah), avsux)]
    haha_av = ''
    counter = 0
    for non_signature in avnotftw:
        non_signature = (non_signature.rstrip())
        if counter > 0:
            haha_av = haha_av + '+'
            haha_av = haha_av + "'"
        surprise_surprise = non_signature.decode('ascii') + "'"
        haha_av = haha_av + surprise_surprise
        haha_av = haha_av.replace("==", "'+'==")
        counter = 1
    mangle_quotes = (choice(["''"]))
    return '''powershell /w 1 /C "s{0}v {1} -;s{0}v {2} e{0}c;s{0}v {3} ((g{0}v {4}).value.toString()+(g{0}v {5}).value.toString());powershell (g{0}v {6}).value.toString() (\''''.format(
        mangle_quotes, ran1, ran2, ran3, ran1, ran2, ran3) + haha_av + ")" + '"'


def obfuscate_bash(code):
    return code
