"""
clear_null_bytes
~~~~~~~~~~~~~~~~

Self explanatory; clears null bytes from files
"""
import argparse
import os
try:
    from StringIO import StringIO
except:  # python3
    from io import StringIO


def clear_descriptor_null_bytes(descriptor):
    descriptor_text = descriptor.read()
    stringio = StringIO()
    stringio.write(descriptor_text.replace("\x00", ""))
    stringio.seek(0)
    return stringio


def clear_null_bytes(input_file):
    with open(input_file, "rU") as old:
        return clear_descriptor_null_bytes(old)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", help="rel path to input file")
    args = parser.parse_args()
    stringio = clear_null_bytes(args.input_file)
    with open(new_file, "w") as new:
        new.write(stringio.read())


if __name__ == "__main__":
    main()
