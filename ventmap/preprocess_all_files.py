"""
preprocess_all_files
~~~~~~~~~~~~~~~~~~~~

Preprocess all files in a given directory so they can be loaded in the future more quickly
"""
import argparse
from glob import glob
from io import open
import os

from ventmap.raw_utils import process_breath_file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('dir')
    args = parser.parse_args()

    files = glob(os.path.join(args.dir, '*.csv'))
    for filename in files:
        output_filename = os.path.splitext(filename)[0]

        process_breath_file(open(filename, encoding='ascii', errors='ignore'), False, output_filename)


if __name__ == "__main__":
    main()
