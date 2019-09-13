"""
anonymize_datetimes
~~~~~~~~~~~~~~~~~~~

Randomly shifts patient datetimes by a certain factor. If given this script will accept a file
that has a patient:time shift mapping. Otherwise the script will randomly choose an amount of time
to shift the patient files by.

Shift file should take CSV format and look like

patient,shift_hours
XXXXRPIXXXXXXXXXX,100000
...
"""
from argparse import ArgumentParser
from datetime import datetime, timedelta
from glob import glob
import os
from random import randint
import re

old_file_date_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}__\d{2}:\d{2}:\d{2}.\d{9})')
text_date_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}.\d{6})')
file_date_pattern = text_date_pattern
patient_pattern = r'(\w{4}RPI\w{10}[-_]?\d?)'
old_file_datetime_time_pattern = '%Y-%m-%d__%H:%M:%S.%f'
data_datetime_time_pattern = '%Y-%m-%d-%H-%M-%S.%f'


def main():
    parser = ArgumentParser()
    parser.add_argument('patient_dir', help='path to the patient directory')
    parser.add_argument('--shift-file', help='mapping of patient to the amount of time (hours) we want to shift the data by')
    args = parser.parse_args()

    match = re.search(patient_pattern, args.patient_dir)
    if not match and args.shift_file:
        raise Exception('Patient not found for directory {}'.format(args.patient_dir))
    elif match:
        patient = match.groups()[0]
    else:
        patient = ''

    if not args.shift_file:
        # shift data in between 100-500 years in future
        shift_hours = randint(100*24*365, 500*24*365)
    else:
        shift_data = pd.read_csv(args.shift_file)
        patient_data = shift_data[shift_data.patient == patient]
        if len(patient_data) != 1:
            raise Exception('patient {} not found in shift file'.format(patient))
        shift_hours = patient_data.iloc[0].shift_hours

    print("shifting patient: {} data by hours: {}".format(patient, shift_hours))

    files = glob(os.path.join(args.patient_dir, '*.csv'))
    if len(files) == 0:
        raise Exception('No files found in directory {}'.format(args.patient_dir))

    new_files_to_move = []
    for file in files:
        places_to_change = []
        file_data = open(file).read()
        match_found = False
        for line in file_data.split('\n'):
            if text_date_pattern.search(line):
                match_found = True
                dt = datetime.strptime(line, data_datetime_time_pattern)
                new_dt = dt + timedelta(hours=shift_hours)
                places_to_change.append((file_data.index(line), new_dt.strftime(data_datetime_time_pattern)))

        if not match_found:
            raise Exception('file: {} had no matching datetime found.'.format(file))

        for index, new_dt in places_to_change:
            file_data = file_data[0:index] + new_dt + file_data[index+len(new_dt):]

        try:
            file_dt = file_date_pattern.search(file).groups()[0]
            new_file_dt = datetime.strptime(file_dt, data_datetime_time_pattern) + timedelta(hours=shift_hours)
        except:
            file_dt = old_file_date_pattern.search(file).groups()[0]
            new_file_dt = datetime.strptime(file_dt[:-3], old_file_datetime_time_pattern) + timedelta(hours=shift_hours)

        new_file_dt = new_file_dt.strftime(data_datetime_time_pattern)
        idx = file.index(file_dt)
        new_filename = os.path.basename(file[0:idx] + new_file_dt + file[idx+len(file_dt):])
        with open('/tmp/{}'.format(new_filename), 'w') as new_file:
            new_file.write(file_data)
            new_files_to_move.append('/tmp/{}'.format(new_filename))

    for i, file in enumerate(files):
        os.rename(new_files_to_move[i], os.path.join(args.patient_dir, os.path.basename(new_files_to_move[i])))
        os.remove(file)


if __name__ == "__main__":
    main()
