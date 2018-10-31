"""
ventmap.detection
~~~~~~~~~~~~~~~~~~~~

This module is a spin off of a function in TOR. Can be used as a library module now
"""

def detect_version(first):
    """
    Count number of splits. The format should look something like

    2015-06-08 15:10:32.568477572, 9.93, 0.50

    so this splits into 4 entries. If this isn't applicable everywhere we
    need to revisit this logic

    It is better if we feed the input into this function as a string instead of
    a file descriptor because that means we have more control over our file
    descriptor in the program we are calling this function from. Otherwise we
    would have to introduce logic in here to perform actions on the file descriptor
    correctly which would not be good.
    """
    if len(first.split(' ')) == 4:
        timestamp = True
        BScol = 1
        ncol = 3
    else:
        timestamp = False
        BScol = 0
        ncol = 2
    return  BScol, ncol, timestamp


def detect_version_v2(first):
    """
    detect timestamp
    needs to open up a separate file or else the big algorithm skips first line

    having 2 versions just in case the first line is partial

    detect 2nd type, with first column as time column
    2015-06-09 02:35:07.685091508, BS, S:114,
    """
    first = first.strip(',\r\n')
    if len(first.split(','))==3 or len(first.split('-'))==3:
        timestamp_1st_col = True
        timestamp_1st_row = False
        BScol = 1
        ncol = 3

    #detect 3rd type, with date time in first row
    elif len(first.split('-'))==6:
        timestamp_1st_col = False
        timestamp_1st_row = True
        BScol = 0
        ncol = 2

    #detect 1st type, 2 col  #BS, S:52335,\n (by default)
    else:
        timestamp_1st_col = False
        timestamp_1st_row = False
        BScol = 0
        ncol = 2
    return  BScol, ncol, timestamp_1st_col, timestamp_1st_row


def detect_version_v3(first):
    """
    detect timestamp
    needs to open up a separate file or else the big algorithm skips first line

    having 2 versions just in case the first line is partial

    detect 2nd type, with first column as time column
    2015-06-09 02:35:07.685091508, BS, S:114,
    2016-10-13
    """
    version_info = {}
    first = first.strip(',\r\n')
    if len(first.split(',')) == 3 or len(first.split('-')) == 3:
        version_info["timestamp_1st_col"] = True
        version_info["timestamp_1st_row"] = False
        version_info["BScol"] = 1
        version_info["ncol"] = 3
        version_info["version"] = 2

    # detect 3rd type, with date time in first row
    elif len(first.split('-')) == 6:
        version_info["timestamp_1st_col"] = False
        version_info["timestamp_1st_row"] = True
        version_info["BScol"] = 0
        version_info["ncol"] = 2
        version_info["version"] = 3

    # detect 1st type, 2 col  #BS, S:52335,\n (by default)
    else:
        version_info["timestamp_1st_col"] = False
        version_info["timestamp_1st_row"] = False
        version_info["BScol"] = 0
        version_info["ncol"] = 2
        version_info["version"] = 1
    return version_info
