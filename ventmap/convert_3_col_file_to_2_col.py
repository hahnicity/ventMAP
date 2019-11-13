import argparse
from datetime import datetime
from io import open
import os

from ventmap.constants import IN_DATETIME_FORMAT, OUT_DATETIME_FORMAT
from ventmap.raw_utils import extract_raw


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file')
    args = parser.parse_args()

    file_txt = ""
    gen = extract_raw(open(args.file), False)
    for breath in gen:
        try:
            dt = datetime.strptime(breath['ts'][0], '%Y-%m-%d %H:%M:%S.%f')
        except:
            dt = datetime.strptime(breath['ts'][0][:-3], '%Y-%m-%d %H:%M:%S.%f')
        file_txt += dt.strftime(IN_DATETIME_FORMAT) + '\n'
        file_txt += "BS, S:{},".format(breath['vent_bn']) + '\n'
        for i, val in enumerate(breath['flow']):
            file_txt += '{}, {}'.format(round(val, 2), round(breath['pressure'][i], 2)) + '\n'
        file_txt += 'BE' + '\n'

    with open(args.file + '.conv', 'w') as f:
        f.write(unicode(file_txt))
    os.rename(args.file + '.conv', args.file)


if __name__ == "__main__":
    main()
