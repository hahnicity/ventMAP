import csv
from io import open
import os
from os.path import dirname, join

from nose.tools import assert_list_equal, eq_
import pandas as pd

from ventmap.breath_meta import get_file_breath_meta, get_file_experimental_breath_meta, get_production_breath_meta
from ventmap.constants import META_HEADER, META_HEADER_TOR_3
from ventmap.raw_utils import extract_raw, HundredHzFile, process_breath_file, read_processed_file
from ventmap.tests.constants import *
from ventmap.tests.custom_compare import assert_dfs_equal
from ventmap.rounding_rules import force_round_df, IE_recalc_with_rounding, force_round_df2


def perform_rounding(df):
    df = df.round({"tvi": 1, "tve": 1})
    df = df.round(2)
    return df


class TestBreathMeta(object):
    def test_breath_meta_truncated(self):
        control_df = pd.read_csv(PT0149_BREATH_META)
        control_df = control_df.rename(columns={"BS.1":"BS"})

        metadata = get_file_breath_meta(PT0149_CSV, rel_bn_interval=[200,249])
        result_df = pd.DataFrame(metadata[1:], columns=metadata[0])

        result_df = result_df[META_HEADER_TOR_3]
        result_df = IE_recalc_with_rounding(result_df)
        control_df = control_df.iloc[199:249]
        control_df = force_round_df2(control_df)
        control_df.index = range(len(control_df))
        result_df = force_round_df2(result_df)
        assert_dfs_equal(control_df, result_df)

    def breath_meta_helper(self, to_test, control, experimental):
        control_breath_array = pd.read_csv(control)
        control_breath_array = control_breath_array.rename(columns={"BS.1": "BS"})
        control_breath_array = perform_rounding(control_breath_array)

        with open(to_test) as f:
            if experimental:
                array = get_file_experimental_breath_meta(f)
            else:
                array = get_file_breath_meta(f)
            array = pd.DataFrame(array[1:], columns=array[0])
            array = perform_rounding(array)

        # subsetting allows breath meta to add new columns
        array = array[control_breath_array.columns]
        assert_dfs_equal(control_breath_array, array)

    def test_breath_meta(self):
        self.breath_meta_helper(BREATH_META1, BREATH_META1_CONTROL, False)

    def test_breath_meta_experimental(self):
        self.breath_meta_helper(BREATH_META1, BREATH_META1_CONTROL, True)

    def test_files_with_timestamps(self):
        self.breath_meta_helper(WITH_TIMESTAMP, WITH_TIMESTAMP_CONTROL, False)

    def test_hundred_hz_limited_fields(self):
        # doing this for debraj running into problem
        f = open(ARDS_AND_COPD)
        gen = HundredHzFile(f).extract_raw(True)
        meta = get_file_breath_meta(gen, to_data_frame=True)
        for i, row in meta.iterrows():
            assert gen[i]['bs_time'] == row.BS
            assert row.BE == gen[i]['bs_time'] + gen[i]['frame_dur']-0.01

    def test_to_series_works(self):
        for i, breath in enumerate(extract_raw(open(RAW_UTILS_TEST2), False)):
            bm_orig = get_production_breath_meta(breath, to_series=True)
            assert isinstance(bm_orig, pd.Series)

    def test_preprocessed_files_work_with_breath_meta(self):
        raw_proc = 'tmp.test.raw.npy'
        proc_proc = 'tmp.test.processed.npy'
        process_breath_file(open(RAW_UTILS_TEST2), False, 'tmp.test')
        gen_processed = list(read_processed_file(raw_proc, proc_proc))
        os.remove(raw_proc)
        os.remove(proc_proc)
        for i, breath in enumerate(extract_raw(open(RAW_UTILS_TEST2), False)):
            bm_orig = get_production_breath_meta(breath)
            bm_new = get_production_breath_meta(gen_processed[i])
            assert_list_equal(bm_orig, bm_new)
