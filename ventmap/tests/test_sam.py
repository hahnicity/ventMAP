from io import open
from os.path import dirname, join

from nose.tools import assert_greater
import numpy

from ventmap.SAM import find_slope_from_minf_to_zero
from ventmap.tests.constants import ARDS_AND_COPD, ARDS_ONLY, BREATH_META1
from ventmap.tests.simple_data import gather_flow_and_pressure


def test_find_slope():
    with open(BREATH_META1) as f:
        data = gather_flow_and_pressure(f)
        flow = list(map(lambda x: x[1], data[0]))
        slope = find_slope_from_minf_to_zero(
            list(map(lambda x: x[0], data[0])), flow, min(flow)
        )
        assert_greater(slope, 0)


def test_find_slope_with_ards():
    with open(ARDS_ONLY) as f:
        data = gather_flow_and_pressure(f)
        flow = list(map(lambda x: x[1], data[0]))
        slope = find_slope_from_minf_to_zero(
            list(map(lambda x: x[0], data[0])), flow, min(flow)
        )
        # since ards we want this to be sky high
        assert_greater(slope, 0)


def test_find_slope_with_copd_patient():
    with open(ARDS_AND_COPD) as f:
        data = gather_flow_and_pressure(f)
        flow = list(map(lambda x: x[1], data[0]))
        time = list(map(lambda x: x[0], data[0]))
        slope = find_slope_from_minf_to_zero(time, flow, min(flow))
        assert_greater(slope, 0)


def test_find_slope_with_copd_patient2():
    with open(ARDS_AND_COPD) as f:
        data = gather_flow_and_pressure(f)
        flow = list(map(lambda x: x[1], data[1]))
        slope = find_slope_from_minf_to_zero(
            list(map(lambda x: x[0], data[1])), flow, min(flow)
        )
        assert_greater(slope, 0)


def test_find_slope_with_copd_patient3():
    with open(ARDS_AND_COPD) as f:
        data = gather_flow_and_pressure(f)
        flow = list(map(lambda x: x[1], data[2]))
        slope = find_slope_from_minf_to_zero(
            list(map(lambda x: x[0], data[2])), flow, min(flow)
        )
        assert_greater(slope, 0)


def test_find_slope_with_pos_flow():
    flow = [
        3.68, 47.23, 47.15, 47.44, 48.05, 45.7, 44.06, 43.84, 42.55, 41.69,
        40.87, 40.87, 38.13, 37.68, 35.87, 35.82, 35.35, 33.44, 32.04, 31.16,
        30.28, 29.12, 28.8, 28.35, 26.42, 25.29, 24.43, 23.26, 22.25, 21.45,
        20.13, 19.62, 18.54, 17.41, 16.48, 15.31, 14.78, 13.34, 11.62, 11.09,
        10.0, 9.0, 8.22, 7.35, 6.17, 5.2, 2.66, 1.28, 0.9, 0.9, 0.81,
        0.77, 0.7, 0.83, 0.82, 0.79
    ]
    t = [0.02 * i for i in range(len(flow))]
    slope = find_slope_from_minf_to_zero(t, flow, min(flow))
    assert numpy.isnan(slope), slope
