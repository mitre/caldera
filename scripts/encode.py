import sys
import array

usage = """USAGE: encode.py [-i <input_file>] [-o <output_file>] [-k <key>]
input_file - the file to be encoded. If ommitted uses stdin
output_file - the place to put the encoded file, may be the same as input_file. If omitted, stdout is used.
key - the key to use encode, (default = 0xca)

Caldera Encoder, encodes files to be served up by the server. Performs a bitwise xor with the given key.
If no output file is specified it will print the result to stdout. If no key is specified it will use the default key."""


if __name__ == "__main__":
    key = [0x32, 0x45, 0x32, 0xca]

    contents = None
    outfname = None
    for i in range(1, len(sys.argv)):
        arg = sys.argv[i]
        if arg in ('-h', '--help'):
            print(usage)
            exit()
        elif arg == '-i':
            i += 1
            with open(sys.argv[i], 'rb') as inf:
                contents = inf.read()
        elif arg == '-o':
            i += 1
            outfname = sys.argv[i]
        elif arg == '-k':
            i += 1
            full_key = sys.argv[i]
            key = [int(full_key[x:x + 2], 16) for x in range(0, len(full_key), 2)]

    if not contents:
        contents = b''
        buffer = b'feedbeef'
        # read stdin
        while buffer:
            buffer = sys.stdin.buffer.read(1024)
            contents += buffer

    # unsigned char array
    arr = array.array('B', contents)

    for i, val in enumerate(arr):
        cur_key = key[i % len(key)]
        arr[i] = val ^ cur_key

    outf = sys.stdout.buffer
    if outfname:
        outf = open(outfname, 'wb')

    arr.tofile(outf)

    if outf != sys.stdout.buffer:
        outf.close()
