import argparse
from datetime import datetime
from io import open
import os
import re
import subprocess


def does_file_have_old_timestamp_pat(filename):
    pattern = re.compile(
        "(?P<year>\d{4})-(?P<month>[01]\d)-(?P<day>[0123]\d)"
        "__(?P<hour>[012]\d):(?P<minute>\d{2}):(?P<second>\d{2})"
        ".(?P<millis>[0-9]+).csv"
    )
    match = pattern.search(filename)
    return match if match else False


def does_file_have_new_timestamp_pat(filename):
    pattern = re.compile(
        "(?P<year>\d{4})-(?P<month>[01]\d)-(?P<day>[0123]\d)"
        "-(?P<hour>[012]\d)-(?P<minute>\d{2})-(?P<second>\d{2})"
        ".(?P<millis>[0-9]{6}).csv"
    )
    match = pattern.search(filename)
    return match if match else False


def check_if_file_already_has_timestamp(filename):
    with open(filename) as f:
        first_line = f.readline()
        pat = "\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}"
        pat2 = "\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
        if not re.search(pat, first_line):
            if not re.search(pat2, first_line):
                return False
        return True


def add_timestamp(filename):
    old_match = does_file_have_old_timestamp_pat(filename)
    new_match = does_file_have_new_timestamp_pat(filename)
    if not old_match and not new_match:
        raise Exception("no file-to-regex match for file {}".format(filename))
    match = old_match if old_match else new_match
    if check_if_file_already_has_timestamp(filename):
        return
    dict_ = match.groupdict()
    if old_match:
        dict_['millis'] = dict_['millis'][:-3]
    time = "{year}-{month}-{day}-{hour}-{minute}-{second}.{millis}".format(**dict_)
    # ensure the date can be read properly
    datetime.strptime(time, '%Y-%m-%d-%H-%M-%S.%f')
    os.system('echo {} > /tmp/time.stamp'.format(time))
    os.system('cat /tmp/time.stamp {} > /tmp/vent.file'.format(filename))
    proc = subprocess.Popen(['mv', '/tmp/vent.file', filename])
    proc.communicate()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    args = parser.parse_args()
    add_timestamp(args.file)


if __name__ == "__main__":
    main()
