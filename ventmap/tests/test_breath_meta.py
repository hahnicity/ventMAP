import csv
from os.path import dirname, join

from nose.tools import assert_list_equal, eq_
import pandas as pd

from ventmap.breath_meta import get_file_breath_meta, get_file_experimental_breath_meta, get_production_breath_meta
from ventmap.constants import META_HEADER, META_HEADER_TOR_3
from ventmap.raw_utils import extract_raw, extract_raw_speedup
from ventmap.tests.constants import (
    BREATH_META1,
    BREATH_META1_CONTROL,
    JIMMY_TEST,
    PT0149_BREATH_META,
    PT0149_CSV,
    PT0149_BREATH_META_200TO300,
    SPEEDUP_PARSER_ERROR_CASE,
    SPEEDUP_NULL_BYTES_ERROR_CASE,
    WITH_TIMESTAMP,
    WITH_TIMESTAMP_CONTROL
)
from ventmap.tests.custom_compare import assert_dfs_equal
from ventmap.rounding_rules import force_round_df, IE_recalc_with_rounding, force_round_df2


def perform_rounding(df):
    df = df.round({"tvi": 1, "tve": 1})
    df = df.round(2)
    return df


def breath_meta_raw_utils_speedup_helper(filename):
    slow_gen = extract_raw(open(filename), False)
    fast_gen = extract_raw_speedup(open(filename), False)
    for slow_b in slow_gen:
        fast_b = fast_gen.next()
        slow_meta = get_production_breath_meta(slow_b)
        fast_meta = get_production_breath_meta(fast_b)
        assert_list_equal(slow_meta, fast_meta)


def test_compare_speedup_bm_to_regular_bm():
    breath_meta_raw_utils_speedup_helper(JIMMY_TEST)


def test_compare_speedup_bm_to_regular_bm_parser_error_case():
    breath_meta_raw_utils_speedup_helper(SPEEDUP_PARSER_ERROR_CASE)


def test_compare_speedup_bm_to_regular_bm_null_bytes_error_case():
    breath_meta_raw_utils_speedup_helper(SPEEDUP_NULL_BYTES_ERROR_CASE)


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
