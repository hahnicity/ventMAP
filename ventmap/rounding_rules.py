ROUNDING_RULES_DICT = {
    'IEnd': 2, 'I:E ratio': 2, 'BE': 2, 'iTime': 2, 'eTime': 2,
    'inst_RR': 2, 'tvi': 1, 'tve': 1, 'tve:tvi ratio': 2,
    'maxF': 2, 'minF': 2, 'maxP': 2,
    'Maw': 2, 'PEEP': 2, 'ipAUC': 2, 'epAUC': 2,
    'x01': 2, 'tvi1': 1, 'tve1': 1, 'x02': 2, 'tvi2': 1, 'tve2': 1
}


def IE_recalc_with_rounding(df):
    """
    redo calculation of IE based on rounded values
    """
    df['I:E ratio'] = df.apply(recalc_IE_ratio, axis=1)
    return df


def recalc_IE_ratio(row):
    """
    redo calculations of IE based off of rounded values
    """
    IEratio_pre_rounded = round(row['iTime'], 2) / round(row['eTime'], 2)
    return IEratio_pre_rounded


def force_round_df(df):
    """
    Uses the quicker rounding of pandas/numpy.

    Rounds values ending with 5 to the nearest even number
    (prevents rounding up bias)


    Versions
    --------
    20160804
    """
    df = df.round(ROUNDING_RULES_DICT)
    return df


def force_round_df2(df):
    """
    Rounds the results to be closer to TOR3 output

    Unlike force_round_df, this uses the native rounding rules of python.


    Items that need to be handled separately:
        IE Ratio-run recalc_IE_ratio first

    Ex:
    ---
        result_df = result_df[META_HEADER_TOR_3]
        result_df = IE_recalc_with_rounding(result_df)
        result_df = force_round_df2(result_df)

    """
    for col, decimal_place in ROUNDING_RULES_DICT.items():
        if col in df.columns: #so that fctn can run on det_dfs
            df.loc[:,col]=df[col].apply(lambda x: round(x,decimal_place))
    return df
