from nose.tools import assert_list_equal, assert_raises, eq_

from algorithms.raw_utils import extract_raw, extract_raw_speedup, real_time_extractor
from algorithms.tests.constants import (
    ARDS_AND_COPD,
    JIMMY_TEST,
    MALFORMED_BREATH,
    RAW_UTILS_TEST,
    RAW_UTILS_3_COLUMNS_TEST,
    REAL_TIME_TEST,
    SPEEDUP_BAD_ROW_ERROR_CASE,
    SPEEDUP_BE_ERROR_CASE,
    SPEEDUP_EMPTY_FILE_ERROR_CASE,
    SPEEDUP_EXTRA_COLS_ERROR_CASE,
    SPEEDUP_MULTI_BAD_FIRST_LINES_ERROR_CASE,
    SPEEDUP_NULL_COLS_ERROR_CASE,
    SPEEDUP_PARSER_ERROR_CASE,
)


def test_extract_raw_sunny_day():
    # To ensure everything is ok
    f = open(ARDS_AND_COPD)
    breaths = list(extract_raw(f, False))
    assert breaths


def test_extract_raw_ensure_no_empty_rows():
    f = open(RAW_UTILS_TEST)
    generator = extract_raw(f, False)
    has_data = False
    for sec in generator:
        has_data = True
        assert sec['flow']
    assert has_data


def test_extract_raw_with_spec_rel_bns():
    f = open(RAW_UTILS_TEST)
    generator = extract_raw(f, False, spec_rel_bns=[2, 3, 5, 7, 9])
    has_data = False
    for breath in generator:
        has_data = True
        if breath['rel_bn'] not in [2, 3, 5, 7, 9]:
            assert False, breath['rel_bn']
    assert has_data


def test_extract_raw_with_interval():
    f = open(RAW_UTILS_TEST)
    generator = extract_raw(f, False, vent_bn_interval=[65427, 65428])
    has_data = False
    for sec in generator:
        has_data = True
        if sec['vent_bn'] not in [65427, 65428]:
            assert False, data['vent_bn']
        # Ensure that bs_time doesn't start at 0.02
        assert sec['bs_time'] != 0.02
    assert has_data


def test_raw_utils_3_columns():
    f = open(RAW_UTILS_3_COLUMNS_TEST)
    generator = extract_raw(f, False)
    has_data = False
    for breath in generator:
        has_data = True
    assert has_data


def test_ensure_things_not_double_counter():
    f = open(RAW_UTILS_TEST)
    previous_vent_bn = None
    generator = extract_raw(f, False, vent_bn_interval=[65427, 65428])
    has_data = False
    for sec in generator:
        assert sec['vent_bn'] != previous_vent_bn
        has_data = True
        previous_vent_bn = sec['vent_bn']
    assert has_data


def test_malformed_breath_non_captured():
    """
    Ostensibly this would be because there is no BE
    """
    f = open(MALFORMED_BREATH)
    generator = extract_raw(f, True)
    breaths = list(generator)
    assert not breaths


def test_malformed_breath_is_captured():
    f = open(MALFORMED_BREATH)
    generator = extract_raw(f, False)
    breaths = list(generator)
    assert breaths


def test_extract_raw_list():
    f = open(REAL_TIME_TEST)
    list_ = real_time_extractor(f, False, vent_bn_interval=[65427, 65428])
    assert len(list_) == 2
    assert list_[0]['vent_bn'] == 65427
    assert list_[1]['vent_bn'] == 65428
    assert '2017-01-01 01-02-01' in list_[0]['ts'][0]
    assert '2017-01-01 01-03-01' in list_[1]['ts'][0]
    for var in ['flow', 'pressure']:
        for breath in list_:
            assert breath[var]


def extract_raw_speedup_helper(filename):
    f = open(filename)
    f2 = open(filename)
    gen = extract_raw(f, False)
    gen2 = extract_raw_speedup(f2, False)

    for slow_breath in gen:
        fast_breath = gen2.next()
        eq_(slow_breath['rel_bn'], fast_breath['rel_bn'])
        eq_(slow_breath['vent_bn'], fast_breath['vent_bn'])
        eq_(slow_breath['frame_dur'], fast_breath['frame_dur'])
        assert_list_equal(slow_breath['flow'], list(fast_breath['flow']))
        assert_list_equal(slow_breath['pressure'], list(fast_breath['pressure']))
        eq_(slow_breath['bs_time'], fast_breath['bs_time'])
        eq_(len(slow_breath['t']), len(fast_breath['t']))
        eq_(slow_breath['ts'][0], fast_breath['abs_bs'])


def test_extract_raw_speedup_sunny_day():
    extract_raw_speedup_helper(JIMMY_TEST)


def test_speedup_error_case():
    extract_raw_speedup_helper(SPEEDUP_PARSER_ERROR_CASE)


def test_speedup_bad_row_error_case():
    extract_raw_speedup_helper(SPEEDUP_BAD_ROW_ERROR_CASE)


def test_speedup_extra_cols_error_case():
    extract_raw_speedup_helper(SPEEDUP_EXTRA_COLS_ERROR_CASE)


def test_speedup_null_cols_error_case():
    extract_raw_speedup_helper(SPEEDUP_NULL_COLS_ERROR_CASE)


def test_speedup_multi_bad_first_lines_error_case():
    extract_raw_speedup_helper(SPEEDUP_MULTI_BAD_FIRST_LINES_ERROR_CASE)


def test_speedup_no_be_error_case():
    """
    Problem here is that speedup doesn't properly ignore missing BEs. Need to fix it
    """
    extract_raw_speedup_helper(SPEEDUP_BE_ERROR_CASE)


def test_speedup_empty_file_error_case():
    gen = extract_raw_speedup(open(SPEEDUP_EMPTY_FILE_ERROR_CASE), False)
    assert_raises(StopIteration, gen.next)
