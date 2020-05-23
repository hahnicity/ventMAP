"""
anonymize_datetimes
~~~~~~~~~~~~~~~~~~~

Randomly shifts patient datetimes by a certain factor. If given this script will accept a file
that has a patient:time shift mapping. Otherwise the script will randomly choose an amount of time
to shift the patient files by.

Shift file should take CSV format and look like

patient,shift_hours,new_patient_id
XXXXRPIXXXXXXXXXX,100000,1314
...

If you do not want to go through the trouble of setting this up yourself at first, then you can just
opt to allow the script to do all this work for you by using the --new-cohort-file option. This will
run through your patient directory and then output information in a similar manner to how the shift-file
would originally. As a potentially useful side note: any file used for a --new-cohort-file can also
be used in the future as a --shift-file
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
three_col_regex_search_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6})')
file_date_pattern = text_date_pattern
patient_pattern = r'(\w{4}RPI\w{10}[-_]?\d?)'
old_file_datetime_time_pattern = '%Y-%m-%d__%H:%M:%S.%f'
regular_datetime_time_pattern = '%Y-%m-%d-%H-%M-%S.%f'
three_col_datetime_pattern = '%Y-%m-%d %H:%M:%S.%f'
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


class Filename(object):
    def __init__(self, filename, shift_hours, patient_id, new_patient_id, only_shift_date):
        self.filename = filename
        self.shift_hours = shift_hours
        self.only_shift_date = only_shift_date
        self.patient_id = patient_id
        self.new_patient_id = new_patient_id

    def shift_file_datetime(self):
        try:
            file_dt = file_date_pattern.search(self.filename).groups()[0]
            new_file_dt = datetime.strptime(file_dt, regular_datetime_time_pattern) + timedelta(hours=self.shift_hours)
        except AttributeError:
            file_dt = old_file_date_pattern.search(self.filename).groups()[0]
            new_file_dt = datetime.strptime(file_dt[:-3], old_file_datetime_time_pattern) + timedelta(hours=self.shift_hours)
        new_file_dt = new_file_dt.strftime(regular_datetime_time_pattern)
        idx = self.filename.index(file_dt)
        return os.path.basename(self.filename[0:idx] + new_file_dt + self.filename[idx+len(file_dt):])

    def get_new_filename_shift_all(self):
        new_filename = self.shift_file_datetime().replace(self.patient_id, str(self.new_patient_id))
        return os.path.join('/tmp/', new_filename)

    def get_new_filename_by_only_shifting_date(self):
        new_filename = self.shift_file_datetime()
        return os.path.join('/tmp/', new_filename)

    def get_new_filename(self):
        if self.only_shift_date:
            return self.get_new_filename_by_only_shifting_date()
        elif not self.only_shift_date and self.patient_id is not None and self.new_patient_id is not None:
            return self.get_new_filename_shift_all()
        else:
            raise NoPatientError('No patient id was found with filename {}'.format(self.filename))


class File(object):
    def __init__(self, filename, shift_hours, patient_id, new_patient_id, only_shift_date):
        self.filename = filename
        self.shift_hours = shift_hours
        self.patient_id = patient_id
        self.new_patient_id = new_patient_id
        self.only_shift_date = only_shift_date

    def process_csv_file(self):
        match_found = False
        places_to_change = []
        with open(self.filename, 'r') as f:
            file_data = f.read()
            cur_idx = 0
            for line in file_data.split('\n'):
                # XXX code can be simplified here because each if block is basically the
                # same thing.
                if text_date_pattern.search(line):
                    match_found = True
                    str_dt = text_date_pattern.search(line).groups()[0]
                    dt = datetime.strptime(str_dt, regular_datetime_time_pattern)
                    new_dt = dt + timedelta(hours=self.shift_hours)
                    data_idx = cur_idx + line.index(str_dt)
                    places_to_change.append((data_idx, new_dt.strftime(regular_datetime_time_pattern)))
                # shifting data formatted in 3 column syntax takes a bit of time because there
                # are just so many places the script has to modify.
                elif three_col_regex_search_pattern.search(line):
                    match_found = True
                    str_dt = three_col_regex_search_pattern.search(line).groups()[0]
                    dt = datetime.strptime(str_dt, three_col_datetime_pattern)
                    new_dt = dt + timedelta(hours=self.shift_hours)
                    data_idx = cur_idx + line.index(str_dt)
                    places_to_change.append((data_idx, new_dt.strftime(regular_datetime_time_pattern)))

                cur_idx = len(line) + cur_idx + 1  # +1 because of the \n split

            if not match_found:
                warn('file: {} had no matching datetime found.'.format(self.filename))
                return False, self.filename

            for index, new_dt in places_to_change:
                file_data = file_data[0:index] + new_dt + file_data[index+len(new_dt):]

            filename_obj = Filename(self.filename, self.shift_hours, self.patient_id, self.new_patient_id, self.only_shift_date)
            new_filename = filename_obj.get_new_filename()
            with open(new_filename, 'w') as new_file:
                new_file.write(file_data)
            return True, new_filename

    def process_npy_file(self):
        processed = np.load(self.filename)
        abs_bs_loc = 2
        for i, arr in enumerate(processed):
            abs_bs = arr[abs_bs_loc]
            try:
                converted = datetime.strptime(abs_bs, npy_datetime_time_pattern) + timedelta(hours=self.shift_hours)
            except ValueError:
                warn('file: {} had improperly formated datetime information.'.format(self.filename))
                return False, self.filename

            processed[i][abs_bs_loc] = converted.strftime(npy_datetime_time_pattern)
        filename_obj = Filename(self.filename, self.shift_hours, self.patient_id, self.new_patient_id, self.only_shift_date)
        new_filename = filename_obj.get_new_filename()
        np.save(new_filename, processed)
        return True, new_filename

    def process_file(self):
        if self.filename.endswith('.csv'):
            return self.process_csv_file()
        elif self.filename.endswith('.processed.npy'):
            return self.process_npy_file()


def main():
    parser = ArgumentParser()
    parser.add_argument('patient_dir', help='path to the patient directory')
    mutex = parser.add_mutually_exclusive_group()
    mutex.add_argument('--shift-file', help='mapping of patient to the amount of time (hours) we want to shift the data by')
    mutex.add_argument('--new-cohort-file', help='make a new cohort file with patient data. Allows us to track patients that we\'ve already processed. The difference between this and --shift-file is that that shift-file is already made, whereas this argument presumes no prior thought from the user')
    parser.add_argument('--rm-old-dir', help='remove old (non-anonymized) directory', action='store_true')
    parser.add_argument('--new-dir', help='specify a new directory path to save patient data. If not specified then script will save data into 1 level above where patient directory is located')
    parser.add_argument('--only-shift-date', action='store_true', help='only shift the date of the filename and not the patient. Helpful in cases where the patient name is already anonymized')
    args = parser.parse_args()

    match = re.search(patient_pattern, args.patient_dir)
    if args.only_shift_date:
        patient = None
    elif not match:
        raise NoPatientError('Patient pattern not found for directory {}. Did you mean to shift the files without a patient identifier?'.format(args.patient_dir))
    elif match:
        patient = match.groups()[0]


    shift_hours = randint(min_years*24*365, max_years*24*365)

    if args.only_shift_date:
        new_patient_id = None

    elif args.shift_file:
        new_patient_id = randint(0, max_patient_id)
        shift_data = pd.read_csv(args.shift_file)
        patient_data = shift_data[shift_data.patient == patient]
        if len(patient_data) != 1:
            raise NoPatientError('patient {} not found in shift file, or may be duplicated'.format(patient))
        shift_hours = patient_data.iloc[0].shift_hours
        new_patient_id = patient_data.iloc[0].new_patient_id

    elif args.new_cohort_file:
        new_patient_id = randint(0, max_patient_id)
        try:
            cohort_data = pd.read_csv(args.new_cohort_file)
            new_patient_ids = cohort_data.new_patient_id.unique()
            cohort_data = cohort_data.values.tolist()
        except:
            cohort_data = []
            new_patient_ids = []

        while new_patient_id in new_patient_ids:
            new_patient_id = randint(0, max_patient_id)

    print("shifting patient: {} data by hours: {} new id: {}".format(patient, shift_hours, new_patient_id))

    files = glob(os.path.join(args.patient_dir, '*.csv'))
    files += glob(os.path.join(args.patient_dir, '*.processed.npy'))
    if len(files) == 0:
        raise NoFilesError('No files found in directory {}'.format(args.patient_dir))

    new_files_to_move = []
    remove_files_from_arr = []
    for filename in files:
        file_obj = File(filename, shift_hours, patient, new_patient_id, args.only_shift_date)
        processsed_ok, new_filename = file_obj.process_file()

        if not processsed_ok:
            remove_files_from_arr.append(filename)
        else:
            new_files_to_move.append(new_filename)

    for file in remove_files_from_arr:
        idx = files.index(file)
        files.pop(idx)

    if len(files) == 0:
        raise NoFilesError("No files were found to move for patient {} after final check".format(patient))

    new_dir = args.patient_dir.replace(patient, str(new_patient_id)) if not args.new_dir else os.path.join(args.new_dir, str(new_patient_id))
    os.mkdir(new_dir)
    for i, file in enumerate(files):
        new_filename = new_files_to_move[i]
        new_filepath = os.path.join(new_dir, os.path.basename(new_files_to_move[i]))
        shutil.move(new_filename, new_filepath)
        # This bit of logic is a bit confusing but basically means that we only have .processed.npy files in the
        # list of collected files, but we still have to move the .raw.npy files as well. There's really nothing
        # to do with these files except change their name thankfully. Anyhow, we just reference the .processed.npy
        # file and since theres a 1-1 mapping between processed and raw files we can just do a string replacement
        # to get everything to work properly.
        if file.endswith('.processed.npy'):
            old_raw_file = file.replace('.processed.npy', '.raw.npy')
            shutil.copy(old_raw_file, new_filepath.replace('.processed.npy', '.raw.npy'))

    if args.rm_old_dir:
        shutil.rmtree(args.patient_dir)

    if args.new_cohort_file:
        cohort_data.append([patient, new_patient_id, shift_hours])
        df = pd.DataFrame(cohort_data, columns=['patient_id', 'new_patient_id', 'shift_hours'])
        df.to_csv(args.new_cohort_file, index=False)


if __name__ == "__main__":
    main()
