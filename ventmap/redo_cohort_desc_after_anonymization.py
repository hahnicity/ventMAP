import argparse

import pandas as pd


out_dt_fmt = '%Y-%m-%d %H:%M:%S'
parser = argparse.ArgumentParser()
parser.add_argument('--shift-file', required=True)
parser.add_argument('--non-anon-cohort-desc', required=True)
args = parser.parse_args()

shift_file = pd.read_csv(args.shift_file)
cohort_desc = pd.read_csv(args.non_anon_cohort_desc)
old_pt_id_col = 'Patient Unique Identifier'

cohort_desc = cohort_desc.rename(columns={old_pt_id_col: 'patient_id'})
merged = shift_file.merge(cohort_desc, on='patient_id', how='outer')
merged = merged[~merged.new_patient_id.isna()]
cols_to_keep = [
  'patient_id', 'new_patient_id', 'shift_hours', 'Pathophysiology',
  'Date when Berlin criteria first met (m/dd/yyy)', 'vent_start_time'
]
merged = merged[cols_to_keep]
merged = merged.loc[merged.patient_id.drop_duplicates().index]
shift_dt = pd.to_timedelta(merged.shift_hours, unit='hours')
ards_time_col = 'Date when Berlin criteria first met (m/dd/yyy)'
other_time_col = 'vent_start_time'
merged[other_time_col] = pd.to_datetime(merged[other_time_col]) + shift_dt
merged[ards_time_col] = pd.to_datetime(merged[ards_time_col]) + shift_dt
merged[ards_time_col] = merged[ards_time_col].dt.strftime(out_dt_fmt)
merged[other_time_col] = merged[other_time_col].dt.strftime(out_dt_fmt)
merged = merged.rename(columns={'new_patient_id': 'Patient Unique Identifier'})
new_cols = [
    old_pt_id_col,
    ards_time_col,
    other_time_col,
    'Pathophysiology',
]
merged = merged[new_cols]
merged[old_pt_id_col] = merged[old_pt_id_col].astype(int)
merged.to_csv(args.non_anon_cohort_desc, index=False)
