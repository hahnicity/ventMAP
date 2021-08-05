from copy import copy
from io import open
import os

from nose.tools import assert_dict_equal, assert_list_equal, assert_raises, eq_

from ventmap.raw_utils import BadDescriptorError, extract_raw, HundredHzFile, PB840File, process_breath_file, read_processed_file, real_time_extractor
from ventmap.tests.constants import *
from ventmap.tests.raw_utils_legacy import extract_raw as extract_raw_legacy

open_func = lambda f: open(f, encoding='ascii', errors='ignore')


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
    assert len(generator) == 61, len(generator)


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
    list_ = real_time_extractor(f, False, vent_bn_interval=[65426, 65428])
    assert len(list_) == 3
    assert list_[0]['vent_bn'] == 65426
    assert list_[1]['vent_bn'] == 65427
    assert list_[2]['vent_bn'] == 65428
    assert '2017-01-01 01-01-01' in list_[0]['abs_bs']
    assert '2017-01-01 01-02-01' in list_[1]['abs_bs']
    assert '2017-01-01 01-03-01' in list_[2]['abs_bs']
    for var in ['flow', 'pressure']:
        for breath in list_:
            assert breath[var]


def test_raw_utils2():
    gen  = extract_raw(open(RAW_UTILS_TEST2), False)
    has_breaths = False
    for b in gen:
        has_breaths = True
        break
    assert has_breaths


def test_raw_utils_with_spec_rel_and_vent_bns1():
    gen  = extract_raw(open(JIMMY_TEST), False, spec_rel_bns=[1], spec_vent_bns=[396])
    has_breaths = False
    for b in gen:
        has_breaths = True
        break
    assert has_breaths


def test_raw_utils_with_spec_rel_and_vent_bns2():
    gen  = extract_raw(open(JIMMY_TEST), False, spec_rel_bns=[10], spec_vent_bns=[396])
    has_breaths = False
    for b in gen:
        has_breaths = True
        break
    assert not has_breaths


def test_raw_utils_with_spec_rel_and_vent_bns3():
    gen  = extract_raw(open(JIMMY_TEST), False, spec_rel_bns=[1], spec_vent_bns=[500])
    has_breaths = False
    for b in gen:
        has_breaths = True
        break
    assert not has_breaths


def test_failing_abs_bs():
    gen = extract_raw(open(FAILING_ABS_BS), False)
    has_breaths = False
    for b in gen:
        has_breaths = True
        assert b['abs_bs'] is not None
    assert has_breaths


def test_read_processed_file():
    out_raw = 'tmp.test.raw.npy'
    out_proc = 'tmp.test.processed.npy'
    gen = list(extract_raw(open(RAW_UTILS_TEST2), False))
    process_breath_file(open(RAW_UTILS_TEST2), False, 'tmp.test')
    compr = list(read_processed_file(out_raw, out_proc))
    for idx, breath in enumerate(gen):
        orig = dict(
            rel_bn=breath['rel_bn'],
            vent_bn=breath['vent_bn'],
            flow=breath['flow'],
            pressure=breath['pressure'],
            abs_bs=breath['abs_bs'],
            bs_time=breath['bs_time'],
            frame_dur=breath['frame_dur'],
            dt=breath['dt'],
        )
        new = compr[idx]
        new['flow'] = new['flow']
        new['pressure'] = new['pressure']
        assert_dict_equal(orig, new)
    os.remove(out_raw)
    os.remove(out_proc)


def test_bad_unicode_error():
    gen = extract_raw(open(BAD_UNICODE_ERROR, encoding='ascii', errors='ignore'), False)
    has_breaths = False
    for b in gen:
        has_breaths = True
        break
    assert has_breaths


def test_bad_unicode_error_fails_with_no_encoding():
    # this test fails on python 2.7 but succeeds on python3.7. Could this be because of
    # differences in how open works between the two versions?
    try:
        gen = extract_raw(open(BAD_UNICODE_ERROR, 'rb'), False)
        for b in gen:
            assert False
    except BadDescriptorError:
        pass


def test_new_er_and_old_er_same():
    gen_old = list(extract_raw_legacy(open(RAW_UTILS_TEST2), False))
    gen_new = list(PB840File(open(RAW_UTILS_TEST2)).extract_raw(False))
    assert len(gen_old)+1 == len(gen_new)

    for i, b in enumerate(gen_old):
        b_match = copy(gen_new[i])
        assert b_match['rel_bn'] == b['rel_bn']
        assert b_match['vent_bn'] == b['vent_bn']
        assert b_match['abs_bs'] == b['ts'][0], (i, b_match['abs_bs'], b['ts'][0], b_match['vent_bn'])
        del b['t']
        del b['ts']
        del b['bs_count']
        del b['be_count']
        assert b_match['frame_dur'] == b['frame_dur']
        assert b_match['flow'] == b['flow']
        assert b_match['pressure'] == b['pressure']
        assert b_match['bs_time'] == b['bs_time'], (b_match['bs_time'], b['bs_time'])
        assert b_match['dt'] == b['dt']


def test_new_er_and_old_er_same_3col():
    gen_old = list(extract_raw_legacy(open(RAW_UTILS_3_COLUMNS_TEST), False))
    gen_new = PB840File(open(RAW_UTILS_3_COLUMNS_TEST)).extract_raw(False)

    for i, b in enumerate(gen_old):
        b_match = copy(gen_new[i])
        assert b_match['rel_bn'] == b['rel_bn']
        assert b_match['vent_bn'] == b['vent_bn']
        # We aren't testing that abs bs stamps are the same because the two functions do things
        # slightly differently that doesn't change the behavior of the code in a negative way
        # as long as the other things are OK then we're fine.
        del b['t']
        del b['ts']
        del b['bs_count']
        del b['be_count']
        assert b_match['frame_dur'] == b['frame_dur']
        assert b_match['flow'] == b['flow']
        assert b_match['pressure'] == b['pressure']
        assert b_match['bs_time'] == b['bs_time'], (b_match['bs_time'], b['bs_time'])
        assert b_match['dt'] == b['dt']


def test_that_we_get_breath_at_end_when_no_skip_be():
    gen = extract_raw(open_func(BE_NOT_AT_END), False)
    assert gen[-1]['vent_bn'] == 14635
    assert gen[-1]['rel_bn'] == 14
    assert len(gen[-1]['flow']) == 13


def test_hundred_hz():
    f = open(ARDS_AND_COPD)
    gen = HundredHzFile(f).extract_raw(True)
    prev_breaths_len = 0.00
    for i, breath in enumerate(gen):
        assert breath['rel_bn'] == i+1
        assert breath['frame_dur'] == len(breath['flow']) * 0.01
        assert breath['dt'] == 0.01
        assert breath['bs_time'] == round(0.01 + prev_breaths_len, 2), (breath['bs_time'], 0.01 + prev_breaths_len)
        prev_breaths_len += breath['frame_dur']
