"""
tests.simple_data
~~~~~~~~~~~~~~~~~

Gather data for breaths simply without as much heavy logic as we normally need
"""
import csv

from ventmap.detection import detect_version_v2


def gather_flow_and_pressure(f_desc):
    """
    Gather time, flow, and pressure data given some file descriptor of a b2c
    data file.

    Returns data as a list of tuples

    [
        (t1, flow1, pressure1),
        (t2, flow2, pressure2),
        ...
    ]
    """
    reader = csv.reader(f_desc)
    f_desc.seek(0)
    bs_col, ncol, tsfc, tssc = detect_version_v2(f_desc.readline())
    f_desc.seek(0)

    data = []
    t = 0
    delta = 0.02
    for line in reader:
        if line[bs_col].strip() == "BS":
            points = []
        elif line[bs_col].strip() == "BE":
            data.append(points)
        else:
            t = t + delta
            points.append((t, float(line[bs_col]), float(line[bs_col + 1])))
    return data
