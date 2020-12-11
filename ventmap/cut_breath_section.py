from argparse import ArgumentParser
import csv
from datetime import datetime
from io import open, StringIO
from operator import itemgetter

from ventmap.detection import detect_version_v2
from ventmap.clear_null_bytes import clear_null_bytes


def cut_breath_section(descriptor, bn_start, bn_end, start_abs_bs):
    """
    Cut up a file by relative breath number

    :param descriptor: file  descriptor for file to chunk up
    :param bn_start: starting (inclusive) relative breath number
    :param bn_end: ending (inclusive) relative breath number
    :param start_abs_bs: because this function cuts off the absolute breath start timestamp we can provide a new one for the file if we need. If we dont care we can just provide None
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
    if start_abs_bs:
        try:
            datetime.strptime(start_abs_bs, '%Y-%m-%d-%H-%M-%S.%f')
        except:
            raise Exception('start_abs_bs must be in format %Y-%m-%d-%H-%M-%S.%f')
    record_lines = False
    end_next = False
    lines_to_keep = []
    bs_col, ncol, _, __ = detect_version_v2(descriptor.readline())
    descriptor.seek(0)
    reader = csv.reader(descriptor)
    for line in reader:
        if not line:
            continue
        if line[bs_col].strip() == "BS":
            bn += 1
        if bn == bn_start:
            record_lines = True

        if record_lines:
            lines_to_keep.append(i)

        if bn == bn_end and line[bs_col].strip() == "BE":
            descriptor.seek(0)
            lines = descriptor.read().split("\n")
            text = "\n".join(list(itemgetter(*lines_to_keep)(lines)))
            text = start_abs_bs + '\n' + text if start_abs_bs else text
            return StringIO(text)

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
    stringio = cut_breath_section(descriptor, relBN_start, relBN_end, None)
    open(out_file, 'w').write(stringio.read())


def main():
    parser = ArgumentParser(description="cut up a file by relative breath number")
    parser.add_argument("file", help="the input file to partition")
    parser.add_argument("-s", "--bn-start", type=int, required=True, help="relative starting breath number")
    parser.add_argument("-e", "--bn-end", type=int, required=True, help="relative ending breath number")
    parser.add_argument("-o", "--outfile", required=True, help="name of file to output results to")
    args = parser.parse_args()
    descriptor = clear_null_bytes(args.file)
    stringio = cut_breath_section(descriptor, args.bn_start, args.bn_end, None)
    open(args.outfile, "w").write(stringio.read())


if __name__ == "__main__":
    main()
