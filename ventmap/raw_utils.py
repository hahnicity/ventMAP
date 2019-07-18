"""
ventmap.raw_utils
~~~~~~~~~~~~~~~~~~~~

Extract raw data from a text file and return it in some kind of presentable format
"""
import csv
from datetime import datetime, timedelta
import io
import re
from operator import xor
from io import StringIO
import sys

import numpy as np
import pandas as pd

from ventmap.clear_null_bytes import clear_descriptor_null_bytes
from ventmap.constants import IN_DATETIME_FORMAT, OUT_DATETIME_FORMAT
from ventmap.detection import detect_version_v2

csv.field_size_limit(sys.maxsize)
EMPTY_FLOAT_DELIMITER = -1000.0
EMPTY_DATE_DELIMITER = "2222-12-12 12:12:12.12"


def filter_arrays(flow, pressure, t_array, timestamp_array):
    # Array filtering speedup
    if flow[0] == EMPTY_FLOAT_DELIMITER:
        return [], [], [], []
    for idx, i in enumerate(flow):
        if i == EMPTY_FLOAT_DELIMITER:
            final_rel_idx = idx
            break
    else:
        raise Exception("You breath has overflowed the buffer for # observations in a breath. Something went wrong")
    if timestamp_array[0] == EMPTY_DATE_DELIMITER:
        final_ts_idx = 0
    else:
        final_ts_idx = final_rel_idx
    # Don't add  + 1 because we are tracking up to the empty delim
    flow = flow[:final_rel_idx]
    pressure = pressure[:final_rel_idx]
    t_array = t_array[:final_rel_idx]
    timestamp_array = timestamp_array[:final_ts_idx]
    return flow, pressure, t_array, timestamp_array


def reset_arrays(flow, pressure, t_array, timestamp_array):
    n_obs = 2000
    flow = [EMPTY_FLOAT_DELIMITER] * n_obs
    pressure = [EMPTY_FLOAT_DELIMITER] * n_obs
    t_array = [EMPTY_FLOAT_DELIMITER] * n_obs
    timestamp_array = [EMPTY_DATE_DELIMITER] * n_obs
    return flow, pressure, t_array, timestamp_array


def extract_raw(descriptor,
                ignore_missing_bes,
                rel_bn_interval=[],
                vent_bn_interval=[],
                spec_rel_bns=[],
                spec_vent_bns=[]):
    """
    Takes a file descriptor and returns the raw data on the
    breath for us to use. Returns data in format

    {
        'vent_bn': vent_bn,
        't': [rel_t1, rel_t2, ...],
        'ts': [ts1, ts2, ...],
        'flow': [flow1, flow2, ...],
        'pressure': [pressure1, pressure2, ...],
        'be_count': be_count,
        'bs_count': bs_count,
        ....
    }

    :param descriptor: The file descriptor to use
    :param ignore_missing_bes: boolean whether or not to ignore missing BEs in the data (False if we want to use breaths without a BE, True otherwise)
    :param rel_bn_interval: The relative [start, end] interval for the data
    :param vent_bn_interval: The vent bn [start, end] interval for the data
    :param spec_rel_bns: The specific relative bns that we want eg: [1, 10, 20]
    :param spec_vent_bns: The specific vent bns that we want eg: [1, 10, 20]
    """
    # XXX You could probably save yourself a ton of time if you
    # processed the BS/BE rows to remove their trailing commas.
    # then you could use a method like np.genfromtext or something faster
    # than the native csv lib.
    def get_data(flow, pressure, t_array, ts_array, rel_bn, vent_bn, bs_count, be_count, last_t, t_delta):
        flow, pressure, t_array, ts_array = filter_arrays(
            flow, pressure, t_array, ts_array
        )
        if flow:
            data_dict = {
                "rel_bn": rel_bn,
                "vent_bn": vent_bn,
                "flow": flow,
                "pressure": pressure,
                "t": t_array,
                "ts": ts_array,
                "bs_count": bs_count,
                "be_count": be_count,
                "bs_time": bs_time,
                "frame_dur": round(t_array[-1] + t_delta, 2),
                "dt": t_delta,
            }
            return data_dict

    if not  isinstance(descriptor, StringIO) and not "cStringIO" in str(descriptor.__class__) and not isinstance(descriptor, io.TextIOWrapper):
        raise ValueError("Provide a file descriptor as input! Make sure you are using a Python3 compatible descriptor such as io.open.")
    if (len(rel_bn_interval) == 0 and len(vent_bn_interval) == 0 and
        len(spec_rel_bns) == 0 and len(spec_vent_bns) == 0):
        pass
    elif not xor(
            xor(len(rel_bn_interval) > 0, len(vent_bn_interval) > 0),
            xor(len(spec_rel_bns) > 0, len(spec_vent_bns) > 0)
        ):
        raise ValueError("You can only specify one vent or rel bn filtering option for use!")
    spec_rel_bns = sorted(spec_rel_bns)
    spec_vent_bns = sorted(spec_vent_bns)
    collection_start = False
    last_t = 0  # first data point starts at 0
    bs_count = 0
    be_count = 0
    bs_time = 0.02
    t_delta = 0.02
    rel_ts = 0
    vent_bn = 0
    rel_bn = 0
    has_bs = False
    idx = 0
    flow, pressure, t_array, timestamp_array = reset_arrays(None, None, None, None)
    descriptor = clear_descriptor_null_bytes(descriptor)
    reader = csv.reader(descriptor)
    data_dict = {}
    vent_bn_regex = re.compile("S:(\d+)")
    descriptor.seek(0)
    first_line = descriptor.readline()
    bs_col, ncol, ts_1st_col, ts_1st_row = detect_version_v2(first_line)
    if ts_1st_row:
        abs_time = datetime.strptime(first_line.strip('\r\n'), IN_DATETIME_FORMAT)
    descriptor.seek(0)

    for row in reader:
        try:
            row[bs_col]
        except IndexError:
            continue
        if row[bs_col].strip() == "BS":
            collection_start = True
            if not ignore_missing_bes and has_bs:
                data = get_data(
                    flow, pressure, t_array, timestamp_array, rel_bn, vent_bn, bs_count, be_count, bs_time, t_delta
                )
                if data:
                    yield data
                bs_time = round(last_t + 0.02, 2)
            rel_ts = 0
            bs_count += 1
            rel_bn += 1
            idx = 0
            has_bs = True
            flow, pressure, t_array, timestamp_array = reset_arrays(
                flow, pressure, t_array, timestamp_array
            )
            try:
                match = vent_bn_regex.search(row[bs_col + 1])
            except IndexError:
                has_bs = False
                continue
            if not match:
                has_bs = False  # Don't collect data for the breath
                continue
            vent_bn = int(match.groups()[0])
            if rel_bn_interval and rel_bn > rel_bn_interval[1]:
                return
            elif vent_bn_interval and vent_bn > vent_bn_interval[1]:
                return
            elif spec_rel_bns and rel_bn > spec_rel_bns[-1]:
                return
            elif spec_vent_bns and vent_bn > spec_vent_bns[-1]:
                return
            elif vent_bn_interval and not (vent_bn_interval[0] <= vent_bn <= vent_bn_interval[1]):
                has_bs = False
            elif rel_bn_interval and not (rel_bn_interval[0] <= rel_bn <= rel_bn_interval[1]):
                has_bs = False
            elif spec_rel_bns and (rel_bn not in spec_rel_bns):
                has_bs = False
            elif spec_vent_bns and (vent_bn not in spec_vent_bns):
                has_bs = False
        elif row[bs_col].strip() == "BE":
            be_count += 1
            has_bs = False
            data = get_data(
                flow, pressure, t_array, timestamp_array, rel_bn, vent_bn, bs_count, be_count, bs_time, t_delta
            )
            if data:
                yield data
            bs_time = round(last_t + 0.02, 2)
            rel_ts = 0
        else:
            if collection_start:  # if there is stray data at the top of the file
                # make sure data is correctly formed
                try:
                    float(row[ncol - 2])
                    float(row[ncol - 1])
                except (IndexError, ValueError):
                    continue
                last_t = round(last_t + .02, 2)

            if not has_bs:
                continue
            try:
                flow[idx] = round(float(row[ncol - 2]), 2)
                pressure[idx] = round(float(row[ncol - 1]), 2)
            except (IndexError, ValueError):
                continue
            t_array[idx] = round(rel_ts, 2)
            if ts_1st_col:
                timestamp_array[idx] = row[0]
            elif ts_1st_row:
                timestamp_array[idx] = (abs_time + timedelta(seconds=last_t)).strftime(OUT_DATETIME_FORMAT)
            rel_ts = round(rel_ts + t_delta, 2)
            idx += 1


def real_time_extractor(descriptor,
                        ignore_missing_bes,
                        rel_bn_interval=[],
                        vent_bn_interval=[],
                        spec_rel_bns=[],
                        spec_vent_bns=[]):
    """
    The exact same functionality as extract_raw, except this method
    returns a list of breaths and is also able to update timestamp based on
    whether/not a new timestamp is found in file. Both of these functions are
    necessary for real time TOR.

    In future, we might be able to consolidate this function with extract_raw,
    but for now this works fine and there is no need to expend the engineering
    effort

    :param descriptor: The file descriptor to use
    :param ignore_missing_bes: boolean whether or not to ignore missing BEs in the data (False if we want to use breaths without a BE, True otherwise)
    :param rel_bn_interval: The relative [start, end] interval for the data
    :param vent_bn_interval: The vent bn [start, end] interval for the data
    :param spec_rel_bns: The specific relative bns that we want eg: [1, 10, 20]
    :param spec_vent_bns: The specific vent bns that we want eg: [1, 10, 20]
    """
    def get_data(flow, pressure, t_array, ts_array, rel_bn, vent_bn, bs_count, be_count, last_t, t_delta):
        flow, pressure, t_array, ts_array = filter_arrays(
            flow, pressure, t_array, ts_array
        )
        if flow:
            data_dict = {
                "rel_bn": rel_bn,
                "vent_bn": vent_bn,
                "flow": flow,
                "pressure": pressure,
                "t": t_array,
                "ts": ts_array,
                "bs_count": bs_count,
                "be_count": be_count,
                "bs_time": bs_time,
                "frame_dur": t_array[-1] + t_delta,
                "dt": t_delta,
            }
            return data_dict

    if not isinstance(descriptor, StringIO) and not "cStringIO" in str(descriptor.__class__) and not isinstance(descriptor, io.TextIOWrapper):
        raise ValueError("Provide a file descriptor as input! Make sure you are using a Python3 compatible descriptor such as io.open.")
    if (len(rel_bn_interval) == 0 and len(vent_bn_interval) == 0 and
        len(spec_rel_bns) == 0 and len(spec_vent_bns) == 0):
        pass
    elif not xor(
            xor(len(rel_bn_interval) > 0, len(vent_bn_interval) > 0),
            xor(len(spec_rel_bns) > 0, len(spec_vent_bns) > 0)
        ):
        raise ValueError("You can only specify one vent or rel bn filtering option for use!")
    spec_rel_bns = sorted(spec_rel_bns)
    spec_vent_bns = sorted(spec_vent_bns)
    collection_start = False
    last_t = 0  # first data point starts at 0
    bs_count = 0
    be_count = 0
    bs_time = 0.02
    t_delta = 0.02
    rel_ts = 0
    vent_bn = 0
    rel_bn = 0
    has_bs = False
    idx = 0
    flow, pressure, t_array, timestamp_array = reset_arrays(None, None, None, None)
    descriptor = clear_descriptor_null_bytes(descriptor)
    reader = csv.reader(descriptor)
    data_dict = {}
    data_list = []
    vent_bn_regex = re.compile("S:(\d+)")
    date_search = re.compile("^20[12]\d-[01]\d-")
    descriptor.seek(0)
    first_line = descriptor.readline()

    # Should we be more strict and now allow breaths without a TS up top?
    bs_col, ncol, ts_1st_col, ts_1st_row = detect_version_v2(first_line)
    if ts_1st_row:
        abs_time = datetime.strptime(first_line.strip('\r\n'), IN_DATETIME_FORMAT)
        start_time = abs_time
    else:
        raise Exception("A breath timestamp must be on first row!")
    descriptor.seek(0)

    for row in reader:
        try:
            row[bs_col]
        except IndexError:
            continue

        # XXX fix bs_time! it is not accurate when we update the timestamp
        #
        # update abs time
        if date_search.search(row[0]):
            abs_time = datetime.strptime(row[0], IN_DATETIME_FORMAT)
            last_t = 0
            bs_time = round((abs_time + timedelta(seconds=0.02) - start_time).total_seconds(), 2)
            continue

        if row[bs_col].strip() == "BS":
            collection_start = True
            if not ignore_missing_bes and has_bs:
                data = get_data(
                    flow, pressure, t_array, timestamp_array, rel_bn, vent_bn, bs_count, be_count, bs_time, t_delta
                )
                if data:
                    data_list.append(data)
                bs_time = round((abs_time + timedelta(seconds=last_t) - start_time).total_seconds(), 2)
            rel_ts = 0
            bs_count += 1
            rel_bn += 1
            idx = 0
            has_bs = True
            flow, pressure, t_array, timestamp_array = reset_arrays(
                flow, pressure, t_array, timestamp_array
            )
            try:
                match = vent_bn_regex.search(row[bs_col + 1])
            except IndexError:
                has_bs = False
                continue
            if not match:
                has_bs = False  # Don't collect data for the breath
                continue
            vent_bn = int(match.groups()[0])
            if rel_bn_interval and rel_bn > rel_bn_interval[1]:
                break
            elif vent_bn_interval and vent_bn > vent_bn_interval[1]:
                break
            elif spec_rel_bns and rel_bn > spec_rel_bns[-1]:
                break
            elif spec_vent_bns and vent_bn > spec_vent_bns[-1]:
                break
            elif vent_bn_interval and not (vent_bn_interval[0] <= vent_bn <= vent_bn_interval[1]):
                has_bs = False
            elif rel_bn_interval and not (rel_bn_interval[0] <= rel_bn <= rel_bn_interval[1]):
                has_bs = False
            elif spec_rel_bns and (rel_bn not in spec_rel_bns):
                has_bs = False
            elif spec_vent_bns and (vent_bn not in spec_vent_bns):
                has_bs = False
        elif row[bs_col].strip() == "BE":
            be_count += 1
            has_bs = False
            data = get_data(
                flow, pressure, t_array, timestamp_array, rel_bn, vent_bn, bs_count, be_count, bs_time, t_delta
            )
            if data:
                data_list.append(data)
            bs_time = round((abs_time + timedelta(seconds=last_t) - start_time).total_seconds(), 2)
            rel_ts = 0
        else:
            if collection_start:  # if there is stray data at the top of the file
                # make sure data is correctly formed
                try:
                    float(row[ncol - 2])
                    float(row[ncol - 1])
                except (IndexError, ValueError):
                    continue
                last_t = round(last_t + .02, 2)

            if not has_bs:
                continue
            try:
                flow[idx] = round(float(row[ncol - 2]), 2)
                pressure[idx] = round(float(row[ncol - 1]), 2)
            except (IndexError, ValueError):
                continue
            t_array[idx] = round(rel_ts, 2)
            if ts_1st_col:
                timestamp_array[idx] = row[0]
            elif ts_1st_row:
                timestamp_array[idx] = (abs_time + timedelta(seconds=last_t)).strftime(OUT_DATETIME_FORMAT)
            rel_ts = round(rel_ts + t_delta, 2)
            idx += 1

    return data_list


def fmt_as_csv(array):
    csv_rows = ["{},{}".format(i, j) for i, j in array]
    return "\n".join(csv_rows)


def bs_be_denoting_extractor(descriptor, rel_bn_interval=[]):
    """
    Takes a file descriptor without BS/BE markers and then adds
    BS and BE markers to it, and then returns the breath data generator
    from extract_raw

    :param descriptor: A file descriptor for a ventilator data file without
    BS or BE markers.
    """
    last_bs_loc = None
    cur_bs_loc = None
    first_line = descriptor.readline()
    bs_col, ncol, ts_1st_col, ts_1st_row = detect_version_v2(first_line)
    if ts_1st_row:
        data = first_line
    else:
        descriptor.seek(0)
        data = ""
    breath_idx = 1

    flow_min_threshold = 10
    flow_diff_threshold = 5
    n_last_flow_obs = 4
    n_last_pressure_obs = 5
    n_lookback = 4
    n_lookback_fallback = 2
    median_peep = 0
    median_pip = 100
    observations = np.genfromtxt(descriptor, delimiter=',')
    thresh_not_met = True
    peep_buffer = []
    pip_buffer = []
    pressure_buffer_len = 25
    pressure_diff_frac = 0.7

    # The current index we are at in observations variable will always be
    # i+n_last_flow_obs
    for i, obs in enumerate(observations[n_last_flow_obs:]):
        true_idx = i + n_last_flow_obs

        # We are always <n_last_flow_obs> ahead of i in the observations array
        flow_diff = obs[0] - observations[i,0]
        pressure_diff_thresh = (median_pip - median_peep) * pressure_diff_frac

        if obs[1] >= (median_peep + pressure_diff_thresh):
            thresh_not_met = False

        if thresh_not_met and obs[0] >= flow_min_threshold and flow_diff >= flow_diff_threshold:
            thresh_not_met = False
            for offset in range(n_lookback):
                if (
                    true_idx - (offset + 1) < 0
                    or observations[true_idx - (offset + 1), 0] < 0
                ):
                    last_bs_loc = cur_bs_loc
                    # Would including the first negative point be best? Let's try
                    #
                    # Results indicate it's more of a problem than anything, but it
                    # might be worth reinvestigation
                    cur_bs_loc = true_idx - offset
                    break
            else:
                last_bs_loc = cur_bs_loc
                cur_bs_loc = true_idx - n_lookback_fallback

            # XXX Current methodology just constructs a basic file descriptor
            # to pass to extract_raw. This is not very efficient, but was
            # easiest to code for evaluation of algorithms. Future engineering
            # can just modify this function to return our canonical data dict
            if last_bs_loc:
                data += (
                    "BS, S:{}\n".format(breath_idx) +
                    fmt_as_csv(observations[last_bs_loc:cur_bs_loc]) +
                    "\nBE\n"
                )
                breath_idx += 1

            if breath_idx != 1:
                peep_idx = cur_bs_loc - n_last_pressure_obs if cur_bs_loc - n_last_pressure_obs > 0 else 0
                peep = np.mean(observations[peep_idx:true_idx,1])
                pip = np.max(observations[last_bs_loc:cur_bs_loc,1])
                if len(peep_buffer) < pressure_buffer_len:
                    peep_buffer.append(peep)
                    pip_buffer.append(pip)
                else:
                    peep_buffer.pop(0)
                    peep_buffer.append(peep)
                    pip_buffer.pop(0)
                    pip_buffer.append(pip)
                median_peep = np.median(peep_buffer)
                median_pip = np.median(pip_buffer)

            # when debugging the i index cannot be trusted as a gauge of time
            # in relation to the file with BS and BE.
            if breath_idx:
                #import IPython; IPython.embed()
                pass

        elif not thresh_not_met and obs[0] < flow_min_threshold and obs[1] < (median_peep + pressure_diff_thresh):
            thresh_not_met = True
    else:
        data += (
            "BS, S:{}\n".format(breath_idx) +
            fmt_as_csv(observations[cur_bs_loc:]) +
            "\nBE\n"
        )

    return extract_raw(StringIO(data), False, rel_bn_interval=rel_bn_interval)


def process_breath_file(descriptor,
                        ignore_missing_bes,
                        output_filename,
                        rel_bn_interval=[],
                        vent_bn_interval=[],
                        spec_rel_bns=[],
                        spec_vent_bns=[]):
    """
    Performs similar action to extract_raw but also requires an output filename to be
    designated. This filename will serve as storage for two files to be output. First
    a file of all the raw data from a file in simple linear format. Second a file with
    some basic metadata information of the breath including how to access it in the procesed
    file
    """
    generator = extract_raw(descriptor, ignore_missing_bes, rel_bn_interval, vent_bn_interval, spec_rel_bns, spec_vent_bns)
    cur_idx = 0
    raw_filename = output_filename + '.raw.npy'
    proc_filename = output_filename + '.processed.npy'
    # for raw it will be structured as flow,pressure
    # for processed it will be structured as 'rel_bn', 'vent_bn', 'abs_bs', 'bs_time', 'frame_dur', 'dt', 'start_idx', 'end_idx'
    flow = []
    pressure = []
    processed_rows = []
    for breath in generator:
        timestamp = None if not breath['ts'] else breath['ts'][0]
        processed_row = [breath['rel_bn'], breath['vent_bn'], timestamp, breath['bs_time'], breath['frame_dur'], breath['dt'], cur_idx]
        for i, val in enumerate(breath['flow']):
            flow.append(breath['flow'][i])
            pressure.append(breath['pressure'][i])
            cur_idx += 1
        processed_row.append(cur_idx)
        processed_rows.append(processed_row)
    np.save(proc_filename, processed_rows)
    np.save(raw_filename, np.array([flow, pressure]).transpose())


def read_processed_file(raw_file, processed_file):
    """
    After a file has been processed into its constituent parts, this function will then
    re-read it and output it in similar format to extract_raw
    """
    raw = np.load(raw_file)
    processed = np.load(processed_file)
    for breath_info in processed:
        # for processed it will be structured as 'rel_bn', 'vent_bn', 'abs_bs', 'bs_time', 'frame_dur', 'dt', 'start_idx', 'end_idx'
        end_idx = int(breath_info[-1])
        start_idx = int(breath_info[-2])
        raw_breath_data = raw[start_idx:end_idx]
        dt = float(breath_info[-3])
        bs_time = float(breath_info[3])
        abs_bs = breath_info[2]
        # The output here is slightly different because we are just simplifying keys
        yield {
            "rel_bn": int(breath_info[0]),
            "vent_bn": int(breath_info[1]),
            "flow": list(raw_breath_data[:,0]),
            "pressure": list(raw_breath_data[:,1]),
            "abs_bs": abs_bs,
            "bs_time": bs_time,
            "frame_dur": float(breath_info[-4]),
            "dt": dt,
        }
