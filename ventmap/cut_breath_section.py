from argparse import ArgumentParser
import csv
from operator import itemgetter
from io import open, StringIO

from ventmap.detection import detect_version_v2
from ventmap.clear_null_bytes import clear_null_bytes


def cut_breath_section(descriptor, bn_start, bn_end):
    """
    Cut up a file by relative breath number
    """
    try:
        bn_start = int(bn_start)
        bn_end = int(bn_end)
    except:
        raise ValueError(
            "Must input bn_start and bn_end as integers! Your input "
            "bn_start: {}, bn_end: {}".format(bn_start, bn_end)
        )
    i = 0
    bn = 0  # on APL the relative breath number starts at 1
    record_lines = False
    end_next = False
    lines_to_keep = []
    bs_col, ncol, _, __ = detect_version_v2(descriptor.readline())
    descriptor.seek(0)
    reader = csv.reader(descriptor)
    for line in reader:
        if line[bs_col].strip() == "BS":
            bn += 1
        if bn == bn_start:
            record_lines = True

        if record_lines:
            lines_to_keep.append(i)

        if bn == bn_end and line[bs_col].strip() == "BE":
            descriptor.seek(0)
            lines = descriptor.read().split("\n")
            return StringIO("\n".join(list(itemgetter(*lines_to_keep)(lines))))

        i += 1
    else:
        raise Exception("Something went wrong. The input breath numbers seem to "
                        "be incorrect or the file format does not match a raw "
                        "ventilator waveform file")


def cut_breath_section_wrapper(raw_file, out_file, relBN_start, relBN_end):
    """
    similar to main
    2017-05-19: written
    """

    descriptor = clear_null_bytes(raw_file)
    stringio = cut_breath_section(descriptor, relBN_start, relBN_end)
    open(out_file, 'w').write(stringio.read())


def main():
    parser = ArgumentParser(description="cut up a file by relative breath number")
    parser.add_argument("file", help="the input file to partition")
    parser.add_argument("-s", "--bn-start", type=int, required=True, help="relative starting breath number")
    parser.add_argument("-e", "--bn-end", type=int, required=True, help="relative ending breath number")
    parser.add_argument("-o", "--outfile", required=True, help="name of file to output results to")
    args = parser.parse_args()
    descriptor = clear_null_bytes(args.file)
    stringio = cut_breath_section(descriptor, args.bn_start, args.bn_end)
    open(args.outfile, "w").write(stringio.read())


if __name__ == "__main__":
    main()
