"""
anonymize_datetimes
~~~~~~~~~~~~~~~~~~~

Randomly shifts patient datetimes by a certain factor. If given this script will accept a file
that has a patient:time shift mapping. Otherwise the script will randomly choose an amount of time
to shift the patient files by.

Shift file should take CSV format and look like

patient,shift_hours,new_patient_id
XXXXRPIXXXXXXXXXX,100000,100
...

Another option is to specify a pre-made cohort file with prior information in it. The cohort file
should have the following information

patient,...,start_time,...
XXXXRPIXXXXXXXXXX,...,2018-10-10 04:00:00,...
"""
from argparse import ArgumentParser
from datetime import datetime, timedelta
from glob import glob
import os
from random import randint
import re
import shutil
from warnings import warn

import numpy as np
import pandas as pd

old_file_date_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}__\d{2}:\d{2}:\d{2}.\d{9})')
text_date_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}.\d{6})')
file_date_pattern = text_date_pattern
patient_pattern = r'(\w{4}RPI\w{10}[-_]?\d?)'
old_file_datetime_time_pattern = '%Y-%m-%d__%H:%M:%S.%f'
data_datetime_time_pattern = '%Y-%m-%d-%H-%M-%S.%f'
csv_datetime_time_pattern = '%Y-%m-%d %H-%M-%S'
npy_datetime_time_pattern = '%Y-%m-%d %H-%M-%S.%f'
max_patient_id = 10000
min_years = 100
max_years = 200


class NoFilesError(Exception):
    pass


class DataAlreadyShiftedError(Exception):
    pass


class NoPatientError(Exception):
    pass


def get_name_filepath(filename, shift_hours, patient, new_patient_id):
    try:
        file_dt = file_date_pattern.search(filename).groups()[0]
        new_file_dt = datetime.strptime(file_dt, data_datetime_time_pattern) + timedelta(hours=shift_hours)
    except:
        file_dt = old_file_date_pattern.search(filename).groups()[0]
        new_file_dt = datetime.strptime(file_dt[:-3], old_file_datetime_time_pattern) + timedelta(hours=shift_hours)

    new_file_dt = new_file_dt.strftime(data_datetime_time_pattern)
    idx = filename.index(file_dt)
    new_filename = (os.path.basename(filename[0:idx] + new_file_dt + filename[idx+len(file_dt):])).replace(patient, str(new_patient_id))
    return os.path.join('/tmp/', new_filename)


def process_csv_file(filename, shift_hours, patient, new_patient_id):
    match_found = False
    places_to_change = []
    with open(filename, 'r') as f:
        file_data = f.read()
        # XXX a regex findall might be more efficient?? Maybe test.
        for line in file_data.split('\n'):
            if text_date_pattern.search(line):
                match_found = True
                dt = datetime.strptime(line, data_datetime_time_pattern)
                new_dt = dt + timedelta(hours=shift_hours)
                places_to_change.append((file_data.index(line), new_dt.strftime(data_datetime_time_pattern)))

        if not match_found:
            warn('file: {} had no matching datetime found.'.format(filename))
            return False

        for index, new_dt in places_to_change:
            file_data = file_data[0:index] + new_dt + file_data[index+len(new_dt):]

        new_filename = get_name_filepath(filename, shift_hours, patient, new_patient_id)
        with open(new_filename, 'w') as new_file:
            new_file.write(file_data)
        return True


def process_npy_file(filename, shift_hours, patient, new_patient_id):
    processed = np.load(filename)
    abs_bs_loc = 2
    for i, arr in enumerate(processed):
        abs_bs = arr[abs_bs_loc]
        try:
            converted = datetime.strptime(abs_bs, npy_datetime_time_pattern) + timedelta(hours=shift_hours)
        except ValueError:
            warn('file: {} had improperly formated datetime information.'.format(filename))
            return False

        processed[i][abs_bs_loc] = converted.strftime(npy_datetime_time_pattern)
    new_filename = get_name_filepath(filename, shift_hours, patient, new_patient_id)
    np.save(new_filename, processed)
    return True


def main():
    parser = ArgumentParser()
    parser.add_argument('patient_dir', help='path to the patient directory')
    parser.add_argument('--shift-file', help='mapping of patient to the amount of time (hours) we want to shift the data by')
    parser.add_argument('--cohort-file', help='A pre-made cohort file')
    parser.add_argument('--rm-old-dir', help='remove old (non-anonymized) directory')
    parser.add_argument('--new-cohort-file', help='make a new cohort file with patient data. Allows us to track patients that we\'ve already processed')
    args = parser.parse_args()

    match = re.search(patient_pattern, args.patient_dir)
    if not match and (args.shift_file or args.cohort_file):
        raise NoPatientError('Patient pattern not found for directory {}'.format(args.patient_dir))
    elif match:
        patient = match.groups()[0]
    else:
        patient = ''

    shift_hours = randint(min_years*24*365, max_years*24*365)
    new_patient_id = randint(0, max_patient_id)

    if args.shift_file:
        shift_data = pd.read_csv(args.shift_file)
        patient_data = shift_data[shift_data.patient == patient]
        if len(patient_data) != 1:
            raise NoPatientError('patient {} not found in shift file, or may be duplicated'.format(patient))
        shift_hours = patient_data.iloc[0].shift_hours
        new_patient_id = patient_data.iloc[0].new_patient_id

    elif args.new_cohort_file:
        try:
            cohort_data = pd.read_csv(args.new_cohort_file)
            new_patient_ids = cohort_data.new_patient_id.unique()
            cohort_data = cohort_data.values.tolist()
        except:
            cohort_data = []
            new_patient_ids = []

        while new_patient_id in new_patient_ids:
            new_patient_id = randint(0, max_patient_id)

    elif args.cohort_file:
        cohort_data = pd.read_csv(args.cohort_file)
        patient_data = cohort_data[cohort_data.patient == patient]
        if len(patient_data) != 1:
            raise NoPatientError('patient {} not found in cohort file, or may be duplicated'.format(patient))
        try:
            shifted_start = patient_data.iloc[0].shifted_start
        except AttributeError:
            pass
        else:
            if not pd.isna(shifted_start):
                raise DataAlreadyShiftedError('you have already shifted data for patient {}'.format(patient))

        start_time = pd.to_datetime(patient_data.iloc[0].start_time)
        shifted_time = start_time + timedelta(hours=shift_hours)
        try:
            new_patient_ids = cohort_data.new_patient_id.unique()
        except AttributeError:
            new_patient_ids = []

        while new_patient_id in new_patient_ids:
            new_patient_id = randint(0, max_patient_id)

    print("shifting patient: {} data by hours: {}".format(patient, shift_hours))

    files = glob(os.path.join(args.patient_dir, '*.csv'))
    files += glob(os.path.join(args.patient_dir, '*.processed.npy'))
    if len(files) == 0:
        raise NoFilesError('No files found in directory {}'.format(args.patient_dir))

    new_files_to_move = []
    remove_files_from_arr = []
    for filename in files:
        if filename.endswith('.csv'):
            processsed_ok = process_csv_file(filename, shift_hours, patient, new_patient_id)
        elif filename.endswith('.processed.npy'):
            processsed_ok = process_npy_file(filename, shift_hours, patient, new_patient_id)

        if not processsed_ok:
            remove_files_from_arr.append(filename)
        else:
            new_filename = get_name_filepath(filename, shift_hours, patient, new_patient_id)
            new_files_to_move.append(new_filename)

    for file in remove_files_from_arr:
        idx = files.index(file)
        files.pop(idx)

    if len(files) == 0:
        raise NoFilesError("No files were found to move for patient {} after final check".format(patient))

    new_dir = os.path.join(args.patient_dir.replace(patient, str(new_patient_id)))
    os.mkdir(new_dir)
    for i, file in enumerate(files):
        new_filename = new_files_to_move[i]
        new_filepath = os.path.join(new_dir, os.path.basename(new_files_to_move[i]))
        shutil.move(new_filename, new_filepath)
        if file.endswith('.processed.npy'):
            old_raw_file = file.replace('.processed.npy', '.raw.npy')
            shutil.move(old_raw_file, new_filepath.replace('.processed.npy', '.raw.npy'))
        os.remove(file)

    if args.rm_old_dir:
        shutil.rmtree(args.patient_dir)

    if args.cohort_file:
        cohort_data.loc[patient_data.index, 'shifted_start'] = shifted_time.strftime(csv_datetime_time_pattern)
        cohort_data.loc[patient_data.index, 'new_patient_id'] = new_patient_id
        cohort_data.to_csv(args.cohort_file, index=False)

    elif args.new_cohort_file:
        cohort_data.append([patient, new_patient_id])
        df = pd.DataFrame(cohort_data, columns=['old_patient_id', 'new_patient_id'])
        df.to_csv(args.new_cohort_file, index=False)


if __name__ == "__main__":
    main()
