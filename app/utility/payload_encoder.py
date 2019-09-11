"""
This module contains helper functions for encoding and decoding payload files.

If AV is running on the CALDERA server host, then it may sometimes flag, quarantine, or delete
CALDERA payloads. To help prevent this, encoded payloads can be used to prevent AV
from breaking CALDERA server-side. The convention expected by the CALDERA server is that
encoded payloads will be XOR'ed with the DEFAULT_KEY contained in the payload_encoder.py
module.

Additionally, payload_encoder.py can be used from the command-line to add a new encoded payload.

```
python /path/to/payload_encoder.py /path/to/plain-text-file /path/to/encoded-file.xored
```

NOTE: In order for CALDERA to detect the availability of an encoded payload, the payload file's
name must end in the `.xored` extension.
"""

import array
import argparse
import pathlib

DEFAULT_KEY = [0x32, 0x45, 0x32, 0xca]


def xor_bytes(in_bytes, key=None):
    if not key:
        key = DEFAULT_KEY

    arr = array.array('B', in_bytes)
    for i, val in enumerate(arr):
        cur_key = key[i % len(key)]
        arr[i] = val ^ cur_key

    return bytes(arr)


def xor_file(input_file, output_file=None, key=None):
    with open(input_file, 'rb') as encoded_stream:
        buf = encoded_stream.read()

    buf = xor_bytes(buf, key=key)

    if output_file:
        with open(output_file, 'wb') as decoded_stream:
            decoded_stream.write(bytes(buf))

    return buf


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-key', default=DEFAULT_KEY)
    parser.add_argument('input')
    parser.add_argument('output')

    args = parser.parse_args()

    xor_file(args.input, output_file=args.output, key=args.key)
