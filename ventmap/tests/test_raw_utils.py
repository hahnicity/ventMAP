from io import open
import os

from nose.tools import assert_dict_equal, assert_list_equal, assert_raises, eq_

from ventmap.raw_utils import BadDescriptorError, extract_raw, process_breath_file, read_processed_file, real_time_extractor
from ventmap.tests.constants import *


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
        print('foo')
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


def test_raw_utils2():
    gen  = extract_raw(open(RAW_UTILS_TEST2), False)
    has_breaths = False
    for b in gen:
        has_breaths = True
        break
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
            abs_bs=breath['ts'][0],
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
    gen = extract_raw(open(BAD_UNICODE_ERROR, 'rb'), False)
    try:
        for b in gen:
            assert False
    except BadDescriptorError:
        pass
