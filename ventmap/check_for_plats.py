"""
check_for_plats
~~~~~~~~~~~~~~~

Check specific raw file for plateau pressure areas. This script can either be used for purposes
of checking for the plat in file or improving the plat algo.
"""
import argparse
from io import open

from prettytable import PrettyTable

from ventmap.raw_utils import extract_raw
from ventmap.SAM import check_if_plat_occurs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file')
    parser.add_argument('--min-time', default=0.5, type=float)
    parser.add_argument('--flow-bound', default=0.2, type=float)
    args = parser.parse_args()

    gen = extract_raw(open(args.file, errors='ignore', encoding='ascii'), False)
    table = PrettyTable()
    table.field_names = ['rel_bn', 'abs_bs']
    for br in gen:
        is_plat = check_if_plat_occurs(br['flow'], br['pressure'], br['dt'], min_time=args.min_time, flow_bound=args.flow_bound)
        if is_plat:
            table.add_row([br['rel_bn'], br['abs_bs']])

    if len(table._rows) > 0:
        print(table)
    else:
        print('No plats found using min_time: {} flow_bound: {}'.format(args.min_time, args.flow_bound))


if __name__ == '__main__':
    main()
