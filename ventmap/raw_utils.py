"""
ventmap.raw_utils
~~~~~~~~~~~~~~~~~~~~

Extract raw data from a text file and return it in some kind of presentable format
"""
import csv
from datetime import datetime, timedelta
from dateutil import parser
import io
import re
from operator import xor
from io import StringIO
import sys

import numpy as np
import pandas as pd
from pathlib import Path

from ventmap.clear_null_bytes import clear_descriptor_null_bytes
from ventmap.constants import IN_DATETIME_FORMAT, OUT_DATETIME_FORMAT
from ventmap.detection import detect_version_v2


class BadDescriptorError(Exception):
    pass


class VentilatorBase(object):
    def __init__(self, descriptor):
        """
        :param descriptor: The file descriptor to use
        """
        self.descriptor = descriptor
        if not  isinstance(self.descriptor, StringIO) and \
        not "cStringIO" in str(self.descriptor.__class__) \
        and not isinstance(self.descriptor, io.TextIOWrapper) \
        and not isinstance(self.descriptor, io.BufferedReader):
            raise ValueError("Provide a file descriptor as input! Make sure you are using a Python3 compatible descriptor such as io.open.")
        self.rel_bs_time = 0
        self.abs_bs_time = None
        self.cur_abs_time = None
        self.vent_bn = 0
        self.rel_bn = 0
        try:
            self.descriptor = clear_descriptor_null_bytes(self.descriptor)
        except UnicodeDecodeError:
            raise BadDescriptorError('You seem to have opened a file with garbled bytes. you should open it using io.open(file, encoding="ascii", errors="ignore"')

        self.descriptor.seek(0)
        first_line = self.descriptor.readline()
        self.bs_col, self.ncol, self.ts_1st_col, self.ts_1st_row = detect_version_v2(first_line)
        self.descriptor.seek(0)

    def get_data(self, flow, pressure):
        return {
            "rel_bn": self.rel_bn,
            "vent_bn": self.vent_bn,
            "flow": flow,
            "pressure": pressure,
            "bs_time": round(self.rel_bs_time, 2),
            "frame_dur": round(len(flow) * self.dt, 2),
            "dt": self.dt,
            'abs_bs': self.abs_bs_time.strftime(OUT_DATETIME_FORMAT) if self.abs_bs_time else None,
        }

    def set_rel_bs_time(self, last_t):
        self.rel_bs_time = self.rel_bs_time + last_t

    def try_parse_1st_col_ts(self, ts):
        if len(ts) == 29:  # if extra 3 digits on end of microsecond
            ts = ts[:-3]
        try:
            self.abs_bs_time = parser.parse(ts)
        except:
            self.abs_bs_time = datetime.strptime(ts, IN_DATETIME_FORMAT)

    def set_abs_bs_time(self, row):
        if self.ts_1st_col:
            self.try_parse_1st_col_ts(row[0])
        else:
            self.abs_bs_time = datetime.strptime(row[0], IN_DATETIME_FORMAT)
        self.cur_abs_time = self.abs_bs_time

    def set_abs_bs_time_if_bs(self, row):
        if self.ts_1st_col:
            self.try_parse_1st_col_ts(row[0])
        elif self.abs_bs_time is not None:
            self.abs_bs_time = self.cur_abs_time + timedelta(seconds=self.dt)

    def extract_raw(self,
                    skip_breaths_without_be,
                    rel_bn_interval=[],
                    vent_bn_interval=[],
                    spec_rel_bns=[],
                    spec_vent_bns=[]):
        """
        Takes a file descriptor and returns the raw data on the
        breath for us to use. Returns data in format

        {
            'vent_bn': vent_bn,
            'ts': [ts1, ts2, ...],
            'flow': [flow1, flow2, ...],
            'pressure': [pressure1, pressure2, ...],
            ....
        }

        :param skip_breaths_without_be: boolean whether or not to skip breaths without BE. False for don't skip them, True for skip them
        :param rel_bn_interval: The relative [start, end] interval for the data
        :param vent_bn_interval: The vent bn [start, end] interval for the data
        :param spec_rel_bns: The specific relative bns that we want eg: [1, 10, 20]
        :param spec_vent_bns: The specific vent bns that we want eg: [1, 10, 20]
        """
        spec_rel_bns = sorted(spec_rel_bns)
        spec_vent_bns = sorted(spec_vent_bns)
        # this is a var used to keep track of time incase we dont see a datetime to update us
        last_breath_time = self.dt
        has_bs = False
        date_search = re.compile("^2\d{3}-\d{2}-")
        flow, pressure, data_list = [], [], []
        vent_bn_regex = re.compile("S:(\d+)")
        td = timedelta(seconds=self.dt)

        for row in self.descriptor.readlines():
            row = row.strip().split(',')
            try:
                row[self.bs_col]
            except IndexError:
                continue

            if date_search.search(row[0]) and not self.ts_1st_col:
                self.set_abs_bs_time(row)
                continue

            if row[self.bs_col].strip() == "BS":
                if not skip_breaths_without_be and has_bs:
                    if len(flow) > 0:
                        last_breath_time = self.dt * len(flow)
                        data_list.append(self.get_data(flow, pressure))
                self.set_rel_bs_time(last_breath_time)
                self.set_abs_bs_time_if_bs(row)
                self.rel_bn += 1
                has_bs = True
                flow, pressure = [], []
                try:
                    match = vent_bn_regex.search(row[self.bs_col + 1])
                except IndexError:
                    has_bs = False
                    continue

                if not match:
                    has_bs = False  # Don't collect data for the breath
                    continue
                self.vent_bn = int(match.groups()[0])
                if rel_bn_interval and self.rel_bn > rel_bn_interval[1]:
                    return data_list
                elif vent_bn_interval and self.vent_bn > vent_bn_interval[1]:
                    return data_list
                elif spec_rel_bns and self.rel_bn > spec_rel_bns[-1]:
                    return data_list
                elif spec_vent_bns and self.vent_bn > spec_vent_bns[-1]:
                    return data_list
                elif vent_bn_interval and not (vent_bn_interval[0] <= self.vent_bn <= vent_bn_interval[1]):
                    has_bs = False
                elif rel_bn_interval and not (rel_bn_interval[0] <= self.rel_bn <= rel_bn_interval[1]):
                    has_bs = False
                elif spec_rel_bns and (self.rel_bn not in spec_rel_bns):
                    has_bs = False
                elif spec_vent_bns and (self.vent_bn not in spec_vent_bns):
                    has_bs = False

            elif row[self.bs_col].strip() == "BE":
                has_bs = False
                if len(flow) > 0:
                    last_breath_time = self.dt * len(flow)
                    data_list.append(self.get_data(flow, pressure))
                    flow, pressure = [], []
            else:
                if self.cur_abs_time is not None:
                    self.cur_abs_time += td
                if not has_bs:
                    continue
                try:
                    flow.append(round(float(row[self.ncol - 2]), 2))
                    pressure.append(round(float(row[self.ncol - 1]), 2))
                except (IndexError, ValueError):
                    continue
        else:
            if not skip_breaths_without_be:
                if len(flow) > 0:
                    last_breath_time = self.dt * len(flow)
                    data_list.append(self.get_data(flow, pressure))

        return data_list


class PB840File(VentilatorBase):
    dt = 0.02


class HundredHzFile(VentilatorBase):
    dt = 0.01


def extract_raw(descriptor,
                ignore_missing_bes,
                rel_bn_interval=[],
                vent_bn_interval=[],
                spec_rel_bns=[],
                spec_vent_bns=[]):
    """
    Deprecated method for extracting VWD. Newer implementations should look at
    using a specific ventilator class like PB840File.extract_raw
    """
    pb840 = PB840File(descriptor)
    return pb840.extract_raw(ignore_missing_bes, rel_bn_interval, vent_bn_interval, spec_rel_bns, spec_vent_bns)


def real_time_extractor(descriptor,
                        ignore_missing_bes,
                        rel_bn_interval=[],
                        vent_bn_interval=[],
                        spec_rel_bns=[],
                        spec_vent_bns=[]):
    """
    Deprecated method for extracting VWD. Newer implementations should look at
    using a specific ventilator class like PB840File.extract_raw
    """
    pb840 = PB840File(descriptor)
    return pb840.extract_raw(ignore_missing_bes, rel_bn_interval, vent_bn_interval, spec_rel_bns, spec_vent_bns)


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
        timestamp = breath['abs_bs']
        processed_row = [breath['rel_bn'], breath['vent_bn'], timestamp, breath['bs_time'], breath['frame_dur'], breath['dt'], cur_idx]
        for i, val in enumerate(breath['flow']):
            flow.append(breath['flow'][i])
            pressure.append(breath['pressure'][i])
            cur_idx += 1
        processed_row.append(cur_idx)
        processed_rows.append(processed_row)
    np.save(proc_filename, processed_rows)
    np.save(raw_filename, np.array([flow, pressure]).transpose())


def read_processed_file(raw_file, processed_file=None):
    """
    After a file has been processed into its constituent parts, this function will then
    re-read it and output it in similar format to extract_raw

    :param raw_file: filename for the raw numpy pickled file. Should have a file prefix of '.raw.npy'
    :param processed_file: stale argument around for backwards compatibility sake
    """
    raw = np.load(raw_file, allow_pickle=True)
    processed = np.load(raw_file.replace('.raw.npy', '.processed.npy'), allow_pickle=True)
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


def consolidate_files(paths, ignore_missing_bes, output_dir, to_npy=True, to_csv=False):
    """
    Consolidate a number of previously separate files together.

    :param paths: Can be a list of strs of pathlib.Path objects
    :param ignore_missing_bes: Should we not care if BE marker exists?
    :param output_dir: output directory to place new file(s). can be str or pathlib.Path obj
    :param to_npy: (bool) create npy processed output
    :param to_csv: (bool) create csv output for file in traditional format
    """

    paths = sorted(paths)
    flow = []
    pressure = []
    processed_rows = []

    # absolute idx for new file
    abs_idx = 0
    rel_bn = 1
    bs_time = 0.02
    prior_ts = None
    for path in paths:
        descriptor = io.open(str(path), errors='ignore', encoding='ascii')
        generator = extract_raw(descriptor, ignore_missing_bes)
        # relative idx for currently iterated file
        for breath in generator:
            # sanity check. If somehow the breath is malformed
            if len(breath['flow']) != len(breath['pressure']):
                continue

            # bs_time is a bit unknown here. I can do my best with it using abs
            # timestamps tho. The downside is that this method will error out if
            # no timestamps are present.
            timestamp = breath['abs_bs']
            if prior_ts is not None:
                bs_delta = (datetime.strptime(timestamp, OUT_DATETIME_FORMAT) - datetime.strptime(prior_ts, OUT_DATETIME_FORMAT))
                bs_time += round(bs_delta.total_seconds(), 2)
            processed_row = [
                rel_bn, breath['vent_bn'], timestamp, bs_time,
                breath['frame_dur'], breath['dt'], abs_idx
            ]

            for i, val in enumerate(breath['flow']):
                flow.append(val)
                pressure.append(breath['pressure'][i])
                abs_idx += 1
            processed_row.append(abs_idx)
            processed_rows.append(processed_row)
            rel_bn += 1
            prior_ts = timestamp

    output_filename = str(paths[0]).replace('.csv', '')

    if to_csv:
        output_buf = []
        for breath_info in processed_rows:
            rel_bn = int(breath_info[0])
            vent_bn = int(breath_info[1])
            end_idx = int(breath_info[-1])
            start_idx = int(breath_info[-2])
            flow_data = flow[start_idx:end_idx]
            pressure_data = pressure[start_idx:end_idx]
            abs_bs = datetime.strptime(breath_info[2], OUT_DATETIME_FORMAT).strftime(IN_DATETIME_FORMAT)
            bs_line = ['BS', ' S:{}'.format(vent_bn), '']
            be_line = ['BE']
            output_buf.append([abs_bs])
            output_buf.append(bs_line)
            for i, val in enumerate(flow_data):
                output_buf.append([round(val, 2), round(pressure_data[i], 2)])
            output_buf.append(be_line)

        output_path = str(Path(output_dir).joinpath(Path(output_filename+'.csv').name))
        with open(output_path, 'w') as f:
            writer = csv.writer(f)
            writer.writerows(output_buf)

    if to_npy:
        raw_filename = Path(output_filename + '.raw.npy').name
        proc_filename = Path(output_filename + '.processed.npy').name
        np.save(str(Path(output_dir).joinpath(proc_filename)), processed_rows)
        np.save(str(Path(output_dir).joinpath(raw_filename)), np.array([flow, pressure]).transpose())
