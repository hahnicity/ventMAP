"""
SAM
~~

Supportive functions for breath algorithms
"""
from __future__ import division
from copy import copy
import csv
import math
import sys

import numpy as np
from scipy.integrate import simps


def calc_pressure_itime(t, pressure, peep, threshold):
    if peep == 0:
        return t[-1]
    # find first point
    first_idx, last_idx = 0, -1
    # get first point where pressure goes <threshold> above peep
    for idx, val in enumerate(pressure[::-1]):
        if val >= peep + threshold:
            last_idx = len(pressure) - (idx + 1)
            break
    if last_idx == -1:
        return np.nan
    return t[last_idx] - t[first_idx]


def calc_pressure_itime_by_pip(t, pressure, pip, threshold):
    # lets just assume inspiration starts at 0
    first_idx, last_idx = 0, -1
    # get first point where pressure goes <threshold> below  pip
    for idx, val in enumerate(pressure[::-1]):
        if val >= pip - threshold:
            last_idx = len(pressure) - (idx + 1)
            break
    if last_idx == -1:
        return np.nan
    return t[last_idx] - t[first_idx]


def calc_pressure_itime_by_dyn_threshold(t, pressure, pip, peep, frac):
    """
    Calculate the pressure itime by calculating a threshold based on a
    fraction of the pip - peep difference. This algorithm is also
    improved when median peep and median pip are provided since they
    are more robust against asynchrony
    """
    threshold = (pip - peep) * frac
    return calc_pressure_itime_by_pip(t, pressure, pip, threshold)


def calc_pressure_itime_from_front(t, pressure, pip, peep, frac):
    if len(pressure) == 0:
        return np.nan
    threshold = (pip - peep) * frac
    first_idx, last_idx, passed_thresh = 0, -1, False
    # get first point where pressure goes <threshold> below  pip
    for idx, val in enumerate(pressure):
        if val >= pip - threshold and not passed_thresh:
            passed_thresh = True
        elif passed_thresh and val < pip - threshold:
            last_idx = idx + 1 if idx + 1 < len(pressure) else idx
            break
    if last_idx == -1:
        return np.nan
    return t[last_idx] - t[first_idx]


def _check_for_plat(flow, pressure, dt, min_time, flow_bound, flow_bound_any_or_all, break_if_found):
    """
    Main logic for plat checking. Shouldn't be used directly, either use check_if_plat_occurs to just
    get True/False response, or calc_inspiratory_plateau for both a check and plateau value
    """
    if flow_bound_any_or_all not in ['any', 'all']:
        raise Exception('flow_bound_any_or_all can only be set to "any" or "all"')
    flow = np.array(flow)
    min_points = int(min_time / dt)
    found_plat = False
    skip_this_many = 10
    plat_idxs = []
    found_plat = False

    for idx, _ in enumerate(pressure[skip_this_many:-min_points]):
        idx = idx + skip_this_many
        is_plat = (np.logical_and(flow[idx:idx+min_points] < flow_bound, flow[idx:idx+min_points] > -flow_bound)).all()
        if is_plat and break_if_found:
            return True, [idx]
        elif is_plat:
            found_plat = True
            plat_idxs.append(idx)

        if found_plat and not is_plat:
            return True, plat_idxs
        # Maybe flow can be 0 but not be plat if pt is on heavy sedation
        # where the patient is not ready to exhale. This happens occassionally in practice
        # but I'm not sure for the reasons. This is just a theory of mine. Doctor would
        # probably know more
        below_flow_tol = getattr((flow[idx:idx+min_points] < -flow_bound), flow_bound_any_or_all)()
        # patient is probably exhaling, so just quit
        if below_flow_tol:
            break
    return False, []


def check_if_plat_occurs(flow, pressure, dt, min_time=.5, flow_bound=.2, flow_bound_any_or_all='any'):
    """
    Check if there is an inspiratory plateau pressure for a breath. Works by iterating over a breath
    and then forward checking to see if a plat has occurred in time period since an observation. The
    criteria for possible plat are that the flow is within some bound for a minimum amount of time.
    On PB-840 the minimum amount of time used to certify a plat is about 0.5 seconds, so this is the
    default for min_time. flow_bound is set to 0.2 because the PB-840 should provide 0 flow, but the
    flow sensors can be accurate within about 10%. So a flow_bound of 0.2 covers this margin of error
    plus a bit more. The algo quits if either any or all flow points are below a flow bound. This
    setting is configurable.

    :param flow: array vals of flow measurements in ml/s
    :param pressure: array vals of pressure measurements from vent
    :param dt: time delta between obs
    :param min_time: the minimum amount of time a plat must be held for
    :param flow_bound: if any/all points go below 0 within tolerance of this value
    :param flow_bound_any_or_all: If any or all points go below flow bound then quit. By default
                                  we set this to any because it is much more specific than any is.
                                  all can be far too sensitive for use if you dont want to have to
                                  go check through a bunch of false positives.
    """
    found_plat, idxs = _check_for_plat(flow, pressure, dt, min_time, flow_bound, flow_bound_any_or_all, True)
    return found_plat


def calc_inspiratory_plateau(flow, pressure, dt, min_time=0.5, flow_bound=0.2, flow_bound_any_or_all='any', take_last_n_points=5):
    """
    Calculate the inspiratory plateau pressure for a breath

    :param flow: array vals of flow measurements in ml/s
    :param pressure: array vals of pressure measurements from vent
    :param dt: time delta between obs
    :param min_time: the minimum amount of time a plat must be held for
    :param flow_bound: if any points go below 0 within tolerance of this value, quit
    :param flow_bound_any_or_all: If any or all points go below flow bound then quit. By default
                                  we set this to any because it is much more specific than any is.
                                  all can be far too sensitive for use if you dont want to have to
                                  go check through a bunch of false positives.
    :param take_last_n_points: number of final points to take in the last parts of the plateau to average for a plat pressure
    """
    min_points = int(min_time / dt)
    found_plat, idxs = _check_for_plat(flow, pressure, dt, min_time, flow_bound, flow_bound_any_or_all, False)
    if found_plat:
        if len(idxs) > 1:
            min_idx = (idxs[-1-take_last_n_points] if len(idxs) > take_last_n_points else idxs[0]) + min_points
            max_idx = (idxs[-1]) + min_points
        else:
            min_idx = idxs[0]
            max_idx = idxs[0] + min_points

        return True, sum(pressure[min_idx:max_idx]) / len(pressure[min_idx:max_idx])
    return False, None


def calc_expiratory_plateau(flow, pressure):
    """
    Calculate the expiratory plateau pressure for a breath

    :param flow: array vals of flow measurements in ml/s
    :param pressure: array vals of pressure measurements from vent
    """
    min_f_idx = np.argmin(flow)
    pressure = np.array(pressure[min_f_idx:])
    flow = np.array(flow[min_f_idx:])
    flow_tolerance_band = 0.3
    peep_var_thresh = .002
    min_points = int(.4 / .02)
    found_plat = False
    for idx, val in enumerate(pressure[:-min_points]):
        is_plat = (np.logical_and(flow[idx:idx+min_points] < flow_tolerance_band, flow[idx:idx+min_points] > -flow_tolerance_band)).all()
        if is_plat:
            found_plat = True
        if found_plat and not is_plat:
            return sum(pressure[idx+min_points-6:idx+min_points-1]) / 5
    if found_plat:
        return sum(pressure[-5:]) / 5
    return np.nan


def find_x0_if_plat_in_vent(t, pressure, flow, dt, x0):
    zeros = []
    p_last = 0
    p_tolerance_band = 0.02
    flow_tolerance_band = 0.5
    for idx, p in enumerate(pressure):
        if p == 0:
            continue
        if (abs(p_last - p) / p < p_tolerance_band) and (abs(flow[idx]) < flow_tolerance_band) and t[idx] <= x0:
            zeros.append(t[idx])
        if len(zeros) * dt >= 0.4:
            last_t = t[int(zeros[0] / 0.02) - 1]
            return last_t
        p_last = p
    else:
        raise Exception("something something fix your method")


def calc_plat_from_time_constant(peep, pip, tvi, tau, pif):
    """
    PEEP + ((tvi * (pip - peep)) / (tvi + (TC * PIF)))
    """
    return peep + ((tvi * (pip - peep)) / (tvi + (tau * pif)))


def calc_resistance(pif, pip, plat):
    """
    The resistance is calculated as (pip - plat) / pif
    """
    if pif == 0:
        return np.nan
    return (pip - plat) / pif


def find_mean_flow_from_pef(flow, pef, t_offset):
    """
    Find the mean flow from our pef to end of expiration
    """
    for idx, vol in enumerate(flow):
        if vol == pef:
            # Advance the index to account for the time offset
            idx = idx + int(t_offset / .02)
            break

    # filter out anything over -3
    # Wait should we do this? This has potential to catch copd.
    #remaining_flow = filter(lambda x: x <= -3, flow[idx:])
    remaining_flow = flow[idx:]
    if len(remaining_flow) == 0:
        return np.nan
    return sum(remaining_flow) / len(remaining_flow)


# 2015_06_22
# XXX this needs to be simplified to remove t and replace with dt
def findx0(t, waveform, time_threshold):
    """
    Finds where waveform crosses 0 (changes from + to -)

    Args:
    t: time
    waveform: line to be analyzed
    time-threshold: upper limit (max value) for absolute value of time
    forward_dt: future point in waveform that must be negative

    Updated 2015/09/24 (SAM1.1.9) Stop evaluating if next value is nan
        (as in, non-data rows filled with 'nan' stop being considered as
         waveform[i+1])

    Updated 2015/09/11 and renamed SAM1_1_7; neg flow thresholds changed from
    <= -8 to <= -5 (note that 1st elif clause was found to be < -8 and was
    changed to be <= -5)

    Updated 2015/09/11 and renamed SAM1_1_6; included change in all clauses to
    replace <= to < signs. This dealt with run failures presumably due to
    trailing zeros at the end of the array. Also updated to include 0 in the
    definition of i to account for failures where the value just before the 1st
    neg value was 0 instead of positive.

    Updated 2015/09/09 and renamed SAM1_1_5 to signify SAM v1.1.5; included
    fourth elif clause to x0 logic to allow for cases in which flow 'dribbles'
    along at low values (e.g. -3) for a sustained period, never reaching -8
    threshold, but representing true exhalation event

    Updated 2015/09/04 2.2.6 Improve x0 function sensitivity with 3rd OR clause
        and smaller neg threshold
    Updated: 2015/09/03 2.2.4 Additional OR clause
    Updated: 2015/06/11
    Written: ?
    """
    t.extend([np.nan] * 6)
    waveform.extend([np.nan] * 6)
    cross0_time = []
    for i in range(len(waveform)-2): #if change to append scheme, will have to worry about -1 error
        if waveform[i]>=0 and waveform[i+1] is not np.nan:
            if waveform[i + 1] <= -5 and waveform[i + 2] < 0:
                    cross0_time.append(t[i + 1])
            elif waveform[i + 1]<0 and waveform[i + 4] <= -5:
                    cross0_time.append(t[i + 1])
            elif waveform[i+1]<0 and waveform[i+2]<=-5:
                    cross0_time.append(t[i + 1])
            elif waveform[i+1]<0 and waveform[i+2]<0 and waveform[i+3]<0 and \
                waveform[i+4]<0 and waveform[i+5]<0:
                    cross0_time.append(t[i + 1])

    i = 0
    while i <= len(cross0_time) - 2:
        if abs(cross0_time[i] - cross0_time[i + 1]) < time_threshold:
            del cross0_time[i + 1]
        else:
            i += 1

    for i in range(6):
        t.pop(-1)
        waveform.pop(-1)
    return cross0_time


def findx02(wave,dt):
    """
    Finds where waveform crosses 0 after largest portion contiguous positive AUC

    Args:
    wave: line to be analyzed (ex. flow)

    V1.0 2015-09-23 (2.0) SAM 1.1.8
    Find x02 separates the the wave into positive portions and negative portions.
    The largest positive portion will be considered the inspiratory portion.

    V1.1 2015-10-27 (2.1) SAM 1.2.0
    Utilizes AUC instead of just duration/length of portion

    20150615-V1.1 SAM 1.2.3 default for x0_index is []
    """
    posPortions=[] #holds all positive portion arrays
    negPortions=[] #holds all negative portion arrays
    hold=[] #holding array that is being built
    largestPos=0 #eventually becomes the largest pos AUC (tvi)
    largestNeg=0 #eventually becomes the largest neg AUC (tve)
    x0_index=[] #index where x0 occurs

    for i in range(len(wave)-1): #for each value in the wave
        if wave[i]>0: # if the value is greater than 0, it is considered positive
            hold.append(wave[i]) # and will be added to the holding array
            sign = 'pos'
        else: # if the value isn't greater than 0, it is considered negative
            hold.append(wave[i]) # and will be added to the holding array
            sign = 'neg'

        if wave[i+1]>0: #determine the sign of the next value in the wave
            nextSign = 'pos'
        else:
            nextSign = 'neg'

        if sign != nextSign: #if the sign is different than the sign of next value
            # save the holding array
            if sign=='pos':
                posPortions.append(hold)
                #calculate areas under the curve (tvi)
                holdAUC = simps(hold, dx=dt)*1000/60 #1000ml/L, 60 sec/min
                if holdAUC>largestPos: #if holding array has largest AUC
                    largestPos=holdAUC #it is now considered the largest AUC array
                    x0_index=i+1 #x0 will be considered time + 1
            if sign =='neg': # similar to positive
                negPortions.append(hold)
                holdAUC = simps(hold, dx=dt)*1000/60 #1000ml/L, 60 sec/min
                if holdAUC<largestNeg:
                    largestNeg=holdAUC
            hold=[]
            #possibly add some additional thing here?
    return posPortions, negPortions, largestPos, largestNeg, x0_index
#    return posPortions, negPortions, longestPos,longestNeg, x0_index

def calcTV3(wave,dt,x02index):
    """
    Written 2015/10/27
    """
    tvi=0
    tve=0
    hold=[] #holding array
    for i in range(len(wave)-1):#for each value in the wave
        if wave[i]>0: # if the value is greater than 0, it is considered positive
            hold.append(wave[i]) # and will be added to the holding array
            sign = 'pos'
        else: # if the value isn't greater than 0, it is considered negative
            hold.append(wave[i]) # and will be added to the holding array
            sign = 'neg'

        if wave[i+1]>0: #determine the sign of the next value in the wave
            nextSign = 'pos'
        else:
            nextSign = 'neg'

        if sign != nextSign: #if the sign is different than the sign of next value
            if i<x02index and sign=='pos':
                holdAUC = simps(hold, dx=dt)*1000/60 #1000ml/L, 60 sec/min
                tvi+=holdAUC
            elif i>=x02index and sign =='neg':
                holdAUC = simps(hold, dx=dt)*1000/60 #1000ml/L, 60 sec/min
                tve+=holdAUC
            else:
                pass

    return tvi, tve


def isFlat(data, epsilon = 1, y=0):
    """
    Determines if a region is flat around the horizontal line y.

    This function is used in the delayed trigger algorithms

    ARGS:
    data: 1D list or array (ex. e_pressure)
    epsilon: upper/lower bound
    y: value that the data approaches

    RETURNS:
    flatLengths: list containing lengths of regions that meet criteria
    maxFlat: longest length (units: index numbers, NOT time)
    sumFlat: sum of flatLenghts, another way of measuring time spent near y

    written: 2015/05/23
    """
    flatLengths = []
    k = 0
    for row in data:
        if abs(row-y)<epsilon:
            k+=1
        else:
            if k>0:
                flatLengths.append(k)
                k = 0
    if flatLengths !=[]:
        maxFlat = max(flatLengths)
        sumFlat = sum(flatLengths)
    else:
        maxFlat = 0
        sumFlat = 0

    return flatLengths, maxFlat, sumFlat


# XXX this needs to be simplified to remove t
def find_x0s_multi_algorithms(flow, t, dt):
    """
    Calculate x0s based on multiple algorithms

    versions
    20160503 V1 Original, from TOR 3.5.1
    20160613 V1.1 Disregard ts (time stamp)
    20160721 V1.2 Change output to dictionary
    20160722 V2 Make only output indices
    """
    x0_indices_dict = {}

    #index #1
    x01s = findx0(t, flow, 0.5)

    if x01s!=[]: #if x01 has multiple values, use the first value to mark end of breath
        x01index=t.index(x01s[0])
    else:# if breath doesn't cross 0 (eg. double trigger, nubbin)
        x01index = t.index(t[-1]) #???perhaps we should set to beginning of breath?

    #index #2
    pos,neg,FlowLargePos,FlowLargeNeg,x02index = findx02(flow,dt)
    if x02index==[]:
        x02index = len(flow) - 1

    #save output
    x0_indices_dict['x01index'] = x01index
    x0_indices_dict['x02index'] = x02index

    return x0_indices_dict


# XXX this needs to be simplified to remove t and replace with dt
def x0_heuristic(x0_indices_dict,t):
    """
    Determine which x0 to use
    20160503 V1 Original, from TOR 3.5.1
    20160716 V2 Remove ts dependency
    """

    x01index=int(x0_indices_dict['x01index'])
    x02index=int(x0_indices_dict['x02index'])

    # THIS IS ESPECIALLY IMPORTANT IN NUBBIN BREATHS
    if x02index>x01index:
        x0_index=x02index
        iTime=t[x02index]
    else:
        iTime=t[x01index]
        x0_index=x01index

    return iTime,x0_index


def find_slope_from_minf_to_zero(t, flow, pef, t_offset=0):
    """
    We can take a surrogate time constant measure by calculating the
    slope from min flow to 0.
    """
    t_off_idx = int(t_offset / 0.02)
    min_idx = flow.index(pef) + t_off_idx
    try:
        flow_min = (t[min_idx], min_idx, flow[min_idx])
    except IndexError:
        return np.nan
    flow_zero = (0, 0, sys.maxsize)  # (time, idx, flow)

    flow_threshold = 2
    for offset_idx, time in enumerate(t[flow_min[1]:]):
        idx = offset_idx + flow_min[1]
        if abs(flow[idx]) < flow_threshold and abs(flow[idx]) < flow_zero[2]:
            flow_zero = (time, idx, flow[idx])

    if flow_zero == (0, 0, sys.maxsize):
        return np.nan

    if (float(flow_zero[0]) - flow_min[0]) == 0:
        return np.nan

    slope = (float(flow_zero[2]) - flow_min[2]) / (float(flow_zero[0]) - flow_min[0])
    if slope < 0:
        return np.nan
    else:
        return slope
