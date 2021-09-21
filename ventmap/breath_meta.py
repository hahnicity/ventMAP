"""
ventmap.breath_meta
~~~~~~~~~~~~~~~~~~~~~~

Extract breath meta data.
"""
from argparse import ArgumentParser
import csv
from datetime import datetime, timedelta
from dateutil import parser
from io import open

import numpy as np
import pandas as pd
from scipy import var
from scipy.integrate import simps

from ventmap import SAM
from ventmap.constants import EXPERIMENTAL_META_HEADER, IN_DATETIME_FORMAT, META_HEADER, OUT_DATETIME_FORMAT
from ventmap.detection import detect_version_v2
from ventmap.raw_utils import extract_raw


def write_breath_meta(array, outfile):
    with open(outfile, "wb") as out:
        writer = csv.writer(out)
        writer.writerows(array)


def get_file_breath_meta(file, tve_pos=True, ignore_missing_bes=True, rel_bn_interval=[], vent_bn_interval=[], to_data_frame=False, spec_vent_bns=[], spec_rel_bns=[]):
    return _get_file_breath_meta(
        get_production_breath_meta, file, tve_pos, ignore_missing_bes,
        rel_bn_interval, vent_bn_interval, to_data_frame, spec_vent_bns, spec_rel_bns
    )


def get_file_experimental_breath_meta(file, tve_pos=True, ignore_missing_bes=True, rel_bn_interval=[], vent_bn_interval=[], to_data_frame=False, spec_vent_bns=[], spec_rel_bns=[]):
    return _get_file_breath_meta(
        get_experimental_breath_meta, file, tve_pos, ignore_missing_bes,
        rel_bn_interval, vent_bn_interval, to_data_frame, spec_vent_bns, spec_rel_bns
    )


def _get_file_breath_meta(func, file, tve_pos, ignore_missing_bes, rel_bn_interval, vent_bn_interval, to_data_frame, spec_vent_bns, spec_rel_bns):
    if isinstance(file, str):
        file = open(file, encoding='ascii', errors='ignore')
    if "experimental" in func.__name__:
        array = [EXPERIMENTAL_META_HEADER]
    else:
        array = [META_HEADER]

    # case that the file is just a raw_utils array of breaths
    if isinstance(file, list):
        for b in file:
            array.append(func(b))
    else:  # case the file is a file descriptor
        for breath in extract_raw(file, ignore_missing_bes,
            rel_bn_interval=rel_bn_interval, vent_bn_interval=vent_bn_interval,
            spec_vent_bns=spec_vent_bns, spec_rel_bns=spec_rel_bns):
            array.append(func(breath))

    if not to_data_frame:
        return array
    else:
        return pd.DataFrame(array[1:], columns=array[0])


def get_production_breath_meta(breath, tve_pos=True, calc_tv3=False, to_series=False):
    """
    Get breath meta information for a given breath. This takes a breath parameter
    as given by raw_utils.py.

    As a TODO breath_meta has diverged slightly from TOR on the subject of x0_index.
    We need to reconcile these changes eventually and ensure that we can
    eventually integrate breath_meta with TOR

    :param breath: Breath information as given by raw_utils.py
    :param tve_pos: Give a positive value for TVe
    :param calc_tv3: Calculate tvi/tve3
    :param to_series: output breath to a pandas Series object
    """
    rel_bn = breath['rel_bn']
    vent_bn = breath['vent_bn']
    bs_time = breath["bs_time"]
    dt = breath["dt"]
    flow = breath["flow"]
    pressure = breath["pressure"]
    if 't' not in breath:
        rel_time_array = [i * dt for i in range(len(flow))]
    else:
        rel_time_array = breath["t"]
    frame_dur = breath["frame_dur"]
    rel_time_at_BS = bs_time
    rel_time_at_BE = bs_time + frame_dur - dt

    # find the one x0 and calculations based off x0
    # ---------------------------------------------
    x0_indices_dict = SAM.find_x0s_multi_algorithms(flow, rel_time_array, dt)

    iTime, x0_index=SAM.x0_heuristic(x0_indices_dict, rel_time_array)

    iTime = round(iTime, 2)
    eTime = round(frame_dur - iTime, 2)
    IEratio = round((iTime) / (eTime), 5)
    RR = 60 / (frame_dur)
    rel_time_at_x0 = bs_time + iTime

    if breath['abs_bs']:
        abs_time_at_x0 = (datetime.strptime(breath['abs_bs'], OUT_DATETIME_FORMAT) + timedelta(seconds=round(x0_index * .02, 2))).strftime(OUT_DATETIME_FORMAT)
        abs_time_at_BS = breath['abs_bs']
        abs_time_at_BE = (datetime.strptime(breath['abs_bs'], OUT_DATETIME_FORMAT) + timedelta(seconds=frame_dur - dt)).strftime(OUT_DATETIME_FORMAT)
    else:
        abs_time_at_x0 = "-"
        abs_time_at_BS = "-"
        abs_time_at_BE = "-"

    iPressure = pressure[0:x0_index]
    ePressure = pressure[x0_index:]
    wPressure = pressure[0:]
    iFlow = flow[0:x0_index]
    eFlow = flow[x0_index:]
    wFlow = flow[0:]

    try:
        PIP = max(iPressure)
    except ValueError:  # if no iPressure obs
        PIP = np.nan
    try:
        Maw = sum(iPressure) / len(iPressure)
    except ZeroDivisionError:
        Maw = np.nan

    # calculate PEEP (pos end exp pressure)
    # -------------------------------------
    # if ePressure and not dbl trigger or suction
    # the peep is the average of the end pressure
    if ePressure!=[]:
        last_obs = ePressure[-5:]
        peep = sum(last_obs) / len(last_obs)
    else:
        peep = 0

    # calculate the AUCS / integral of the last breath
    #------------------------------------------
    # calculate inspiratory TV
    # The initial measurement is in liters per minutes and the
    # typical clinical unit of measurement is milliliters per second.
    # Thus we need the unit conversions of 1000ml/L and (60 sec/min)^(-1)
    if iFlow:
        tvi = simps(iFlow, dx=dt) * 1000 / 60
    else:
        tvi = 0
    # if expiratory flow DNE, don't calculate expiratory TV (e.g. )
    if eFlow == []:
        tve = 0
    else:
        tve = simps(eFlow, dx=dt) * 1000 / 60

    if tve_pos:
        tve=abs(tve)

    try:
        TVratio = (abs(tve)) / tvi
    except ZeroDivisionError:
        TVratio = np.nan

    if iPressure:
        ipAUC = simps(iPressure, dx=dt)
    else:
        ipAUC = 0

    if ePressure == []:
        epAUC = 0
    else:
        epAUC = float(simps(ePressure, dx=dt))
    try:
        maxP = max(wPressure) #max pressure for whole breath
    except ValueError:
        maxP = np.nan
    try:
        maxF = max(wFlow)
    except ValueError:
        maxF = np.nan
    try:
        minF = min(wFlow)
    except ValueError:
        minF = np.nan


    # TODO: will probabily move this to somewhere else
    # calculating TVs different ways
    # ------------------------------

    x01index=int(x0_indices_dict['x01index'])
    x02index=int(x0_indices_dict['x02index'])

    x01time = round(bs_time + (x01index * 0.02), 2)
    iFlow1=flow[0:x01index]
    eFlow1=flow[x01index:-1]
    if iFlow1:
        tvi1 = simps(iFlow1, dx=dt)*1000/60 #1000ml/L, 60 sec/min
    else:
        tvi1 = 0
     #if expiratory flow DNE, don't calculate expiratory TV (e.g. )
    if eFlow1:
        tve1 = simps(eFlow1, dx=dt)*1000/60
    else:
        tve1=0
    #tvi/tve2
    x02time = round(bs_time + (x02index * 0.02), 2)
    iFlow2=flow[0:x02index]
    eFlow2=flow[x02index:-1]
    if iFlow2:
        tvi2 = simps(iFlow2, dx=dt)*1000/60 #1000ml/L, 60 sec/min
    else:
        tvi2 = 0
    if eFlow2:
        tve2 = simps(eFlow2, dx=dt)*1000/60 #1000ml/L, 60 sec/min
    else:
        tve2=0

    #tvi/tve3
    if calc_tv3:
        tvi3,tve3=SAM.calcTV3(flow,dt,x02index)
    else:
        tvi3, tve3 = np.nan, np.nan

    #make tvepos
    if tve_pos==True:
        tve1=abs(tve1)
        tve2=abs(tve2)
        tve3=abs(tve3)

    # minimum pressure during inspiration
    min_p_obs = pressure[5:x0_index]
    if min_p_obs:
        min_pressure = round(min(min_p_obs), 2)
    else:
        min_pressure = np.nan

    # Unfortunately pif, derived plat, resistance, and derived compliance just aren't there
    # yet. The calculations seem to work well on volume control and even pressure
    # control but I believe there are problems with pressure support.

    # writing output
    # ---------------
    #
    # The array indices go like this
    #
    # 0: rel_bn, 1: vent_bn, 2: rel_time_at_BS, 3: rel_time_at_x0,
    # 4: rel_time_at_BE, 5: IEratio, 6: iTime, 7: eTime, 8: RR, 9: tvi, 10: tve,
    # 11: TVratio, 12: maxF, 13: minF, 14: maxP, 15: PIP, 16: Maw, 17: peep,
    # 18: ipAUC, 19: epAUC, 20: '', 21: bs_time, 22: x01time, 23: tvi1, 24: tve1,
    # 25: x02index, 26: tvi2, 27: tve2, 28: x0_index, 29: abs_time_at_BS,
    # 30: abs_time_at_x0, 31: abs_time_at_BE, 32: rel_time_at_BS,
    # 33: rel_time_at_x0, 34: rel_time_at_BE, 35: min_pressure

    breath_metaRow = [
        rel_bn, vent_bn, round(rel_time_at_BS, 2), round(rel_time_at_x0, 2), round(rel_time_at_BE, 2), IEratio, iTime,
        eTime, RR, tvi, tve, TVratio, maxF, minF, maxP, PIP,
        Maw, peep, ipAUC, epAUC, '', bs_time, x01time, tvi1, tve1, x02time,
        tvi2, tve2, x0_index, abs_time_at_BS, abs_time_at_x0, abs_time_at_BE,
        rel_time_at_BS, rel_time_at_x0, rel_time_at_BE, min_pressure]

    if not to_series:
        return breath_metaRow
    else:
        return pd.Series(breath_metaRow, index=META_HEADER)


def get_experimental_breath_meta(breath, tve_pos=True):
    """
    Add experimental breath meta information to the original breath meta info
    """
    dt = breath["dt"]
    flow = breath["flow"]
    pressure = breath["pressure"]
    if 't' not in breath:
        rel_time_array = [i * dt for i in range(len(flow))]
    else:
        rel_time_array = breath["t"]
    # set last data point as last value of breath

    non_experimental = get_production_breath_meta(breath, tve_pos)
    x0_index = non_experimental[28]
    tvi = non_experimental[9]
    minF = non_experimental[13]
    PIP = non_experimental[15]
    peep = non_experimental[17]
    eFlow = flow[x0_index:]  # technically this might need to be +1

    # convert tvi to liters. Units are L / cm H20
    dyn_compliance = (tvi / 1000) / (PIP - peep)
    pef_to_zero = SAM.find_slope_from_minf_to_zero(rel_time_array, flow, minF)
    # XXX must add additional time params here so we can see what works best
    pef_plus_16_to_zero = SAM.find_slope_from_minf_to_zero(
        rel_time_array, flow, minF, t_offset=0.16)
    mean_flow_from_pef = SAM.find_mean_flow_from_pef(flow, minF, 0.16)
    if eFlow:
        vol_at_05 = simps(eFlow[:int(.5 / dt)], dx=dt) * 1000 / 60
        vol_at_076 = simps(eFlow[:int(.76 / dt)], dx=dt) * 1000 / 60
        vol_at_1 = simps(eFlow[:int(1 / dt)], dx=dt) * 1000 / 60
    else:
        vol_at_05 = 0
        vol_at_076 = 0
        vol_at_1 = 0
    pressure_itime4 = SAM.calc_pressure_itime(rel_time_array, pressure, peep, 4)
    pressure_itime5 = SAM.calc_pressure_itime(rel_time_array, pressure, peep, 5)
    pressure_itime6 = SAM.calc_pressure_itime(rel_time_array, pressure, peep, 6)
    pressure_itime_pip5 = SAM.calc_pressure_itime_by_pip(rel_time_array, pressure, PIP, 5)
    pressure_itime_pip6 = SAM.calc_pressure_itime_by_pip(rel_time_array, pressure, PIP, 6)
    pressure_itime_from_front = SAM.calc_pressure_itime_from_front(rel_time_array, pressure, PIP, peep, .4)

    # The array indices go like this
    #
    # 0: rel_bn, 1: vent_bn, 2: rel_time_at_BS, 3: rel_time_at_x0,
    # 4: rel_time_at_BE, 5: IEratio, 6: iTime, 7: eTime, 8: RR, 9: tvi, 10: tve,
    # 11: TVratio, 12: maxF, 13: minF, 14: maxP, 15: PIP, 16: Maw, 17: peep,
    # 18: ipAUC, 19: epAUC, 20: '', 21: bs_time, 22: x01time, 23: tvi1, 24: tve1,
    # 25: x02index, 26: tvi2, 27: tve2, 28: x0_index, 29: abs_time_at_BS,
    # 30: abs_time_at_x0, 31: abs_time_at_BE, 32: rel_time_at_BS,
    # 33: rel_time_at_x0, 34: rel_time_at_BE, 35: min_pressure
    # 36: pef_to_zero, 37: pef_plus_16_to_zero, 38: mean_flow_from_pef,
    # 39: dyn_compliance, 40: vol_at_05, 41: vol_at_076, 42: vol_at_1,
    # 43: pressure_itime4, 44: pressure_itime5, 45: pressure_itime6,
    # 46: pressure_itime_pip5, 47: pressure_itime_by_pip6, 48: pressure_itime_from_front
    return non_experimental + [
        pef_to_zero, pef_plus_16_to_zero,
        mean_flow_from_pef, dyn_compliance, vol_at_05,
        vol_at_076, vol_at_1, pressure_itime4, pressure_itime5, pressure_itime6,
        pressure_itime_pip5, pressure_itime_pip6, pressure_itime_from_front,
    ]


def main():
    parser = ArgumentParser()
    parser.add_argument("input_file")
    parser.add_argument("output_file")
    parser.add_argument("--experimental", action="store_true")
    args = parser.parse_args()
    with open(args.input_file) as f:
        if args.experimental:
            array = get_file_experimental_breath_meta(f)
        else:
            array = get_file_breath_meta(f)
        write_breath_meta(array, args.output_file)


if __name__ == "__main__":
    main()
