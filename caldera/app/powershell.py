import zlib
import base64

ZLIB_HEADER = b'\x78\x9c'
ZLIB_CHKSUM_LEN = 4

remote_endl = '\r\n'
remote_encoding = 'ascii'

PS_COMMAND = "powershell -command -"


def powershell_compress(data, do_base64=False):
    # deflatestream
    # .net is deflatestream which uses zlib under rfc 1950 (no header)
    # python zlib compress is rfc 1951 (specifies a 2B header)
    # deflatestream will also ignore trailing checksums
    # level = 6  # python zlib.compress default
    # level = 8  # may be default for .net deflatestream
    data = zlib.compress(data)[len(ZLIB_HEADER):-1 * ZLIB_CHKSUM_LEN]
    if do_base64:
        data = base64.b64encode(data)  # .decode('ascii')
    return data


def powershell_compress_script(data):
    # do we need to be concerned for boms here?
    # encoded needs to be ascii bc inflatestream expects output to be ascii
    encoded = data.lstrip().rstrip().encode('ascii')

    b64ed_compressed = powershell_compress(encoded, do_base64=True)

    return b64ed_compressed


def ps_lined(script, encode=True):
    d = remote_endl
    script = [e + d for e in script.split(d)]
    if encode:
        script = [e.encode(remote_encoding) for e in script]
    # PS requires an extra endl at the end of scripts
    script += [remote_endl]
    return script


def ps_append(b64_script, final_cmd, max_line=8190, var_name='ps1'):
    # Max max cmd line 8190
    # Max createprocess 32767
    initial_cmd = '$%s = ' % var_name
    middle_cmd = '$%s += ' % var_name
    new_script = ''
    i = 0
    while i < len(b64_script):
        prefix = middle_cmd
        if i == 0:
            prefix = initial_cmd
        b64_len = max_line - len(prefix) - 2  # for the quotes
        if b64_len > (len(b64_script) - i):
            b64_len = len(b64_script) - i
        new_script += ("%s'%s';%s" %
                       (prefix,
                        b64_script[i:(i + b64_len)].decode(remote_encoding),
                        remote_endl))
        i += b64_len
    new_script += final_cmd
    return ps_lined(new_script, encode=False)


def ps_compressed(script, var_name='expr'):
    b64_script = powershell_compress_script(script)
    # PS needs a script to that can uncompress and exec this string
    # https://github.com/mattifestation/PowerSploit/
    #   ScriptModification/Out-EncodedCommand.ps1
    # sal sets alias 'a' to represent 'New-Object'
    # iex is Invoke-Expression
    tmp_var_name = 'ps1'
    final_cmd = ("sal a New-Object;" +
                 "$%s=(a IO.StreamReader(" % var_name +
                 "(a IO.Compression.DeflateStream(" +
                 "[IO.MemoryStream][Convert]::FromBase64String($%s)," % tmp_var_name +  # noqa
                 "[IO.Compression.CompressionMode]::Decompress))," +
                 "[Text.Encoding]::ASCII)).ReadToEnd();" +
                 "iex $%s" % var_name)
    # Now the script can be invoked again via command line (incl with args)
    return ps_append(b64_script, final_cmd, var_name=tmp_var_name)
