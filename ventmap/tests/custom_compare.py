"""
custom_compare.py

This script can compare two CSV files or two directories
with CSV/.csv_test files.
Putting a "-O" before "custom_compare.py" to print all differences
(instead of first difference).
"""

import pandas as pd
from argparse import ArgumentParser
from os.path import isfile, isdir, join, basename
from glob import glob


def assert_df_items_equal(item, comparator_item, result_item, verbose=0):
    """
    Version?
    Now handles two items that are different sizes
    """
    assert isinstance(item, str)

    equal_ = comparator_item.equals(result_item)
    if not equal_:
        i1 = pd.DataFrame('1', index=['control'], columns=comparator_item)
        i2 = pd.DataFrame('1', index=['result'], columns=result_item)
        merged_items = pd.concat([i1, i2]).T
        merged_items = merged_items.fillna('missing')
        delta_item_names = merged_items.control != merged_items.result
        delta_item_names_for_print = merged_items[delta_item_names]

        message_for_print_1 = """ The {} are not equivalent.
        \n The original {} are: \n {}
        \n Here are the exact differences: \n {}""".format(
            item,
            item, merged_items,
            delta_item_names_for_print)

        assert False, message_for_print_1

        if verbose == 1:
            print(message_for_print_1)
        if verbose == 2:
            pass
        else:
            print("---- The {} are not equivalent".format(item))


def assert_dfs_equal(comparator, result, additional_cols=[],
                     verbose=0):
    """
    A super basic test on whether or not our data frames are equal
    """
    # assert that column names are the same
    assert_df_items_equal('indices', comparator.index, result.index, verbose)
    assert_df_items_equal('columns', comparator.columns, result.columns, verbose)

    assert isinstance(additional_cols, list)

    for colname in additional_cols:
        assert_df_items_equal(colname + 's', comparator[colname],
                              result[colname])
    for col in comparator.columns:
        if col == ' ':
            continue
        equals_ = comparator.loc[:, col].equals(result.loc[:, col])
        if not equals_:
            not_eq_comparator = comparator[(comparator.loc[:, col] != result.loc[:, col])]
            not_eq_result = result[(comparator.loc[:, col] != result.loc[:, col])]

            merged_df_for_print = pd.concat(
                [not_eq_comparator, not_eq_result],
                keys=['control', 'result'])
            merged_df_for_print = merged_df_for_print.reorder_levels([1, 0]).sortlevel().T

            message_for_print_1 = """The column '{}' is not equivalent;
                \n {}""".format(col, merged_df_for_print)

            assert False, message_for_print_1

            if verbose == 1:
                print(message_for_print_1)
            if verbose == 2:
                pass
            else:
                print("---- The column {} is not equivalent".format(col))


def get_csv_or_csv_test_list(dir):
    """
    obtain file path list for .csv or .csv_test

    Written 20160925 for agg_sta test
    """
    csv_list = glob(join(dir, "*.csv"))
    csv_test_list = glob(join(dir, "*.csv_test"))

    if len(csv_list) > len(csv_test_list):
        file_path_list = csv_list
    else:
        file_path_list = csv_test_list
    return file_path_list


def main(before, after, verbose=0, apply_rounding=True):
    """
    wrapper for comparing two files or two directories
    """
    print ("\n Comparing \n  {} \n with \n {}".format(before, after))
    print ("\n" + "*" * 30 + "\n")
    if isfile(before):
        if not isfile(after):
            raise TypeError("Second input is not a file")
        # import
        control_df = pd.read_csv(before)
        result_df = pd.read_csv(after)
        # compare
        assert_dfs_equal(
            control_df, result_df, additional_cols=[], verbose=verbose)
    elif isdir(before):
        if not isdir(after):
            raise TypeError("Second input is not a directory")
        # generate lists of csv files
        control_list = get_csv_or_csv_test_list(before)
        result_list = get_csv_or_csv_test_list(after)
        message_for_print = "Different lengths \nBefore: {} files \nAfter: {} files".format(
            len(control_list), len(result_list))
        assert len(control_list) == len(result_list), message_for_print

        for before_file, result_file in zip(control_list, result_list):
            control_df = pd.read_csv(before_file)
            result_df = pd.read_csv(result_file)
            if apply_rounding:
                from algorithms.rounding_rules import force_round_df
                control_df = force_round_df(control_df)
                result_df = force_round_df(result_df)

            print ("\n" + basename(before_file) + " v. " + basename(result_file))
            assert_dfs_equal(
                control_df, result_df, additional_cols=[],
                verbose=verbose)
    else:
        pass


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("before", help="Input file or directory")
    parser.add_argument("after", help="Input file or directory")
    parser.add_argument("-v", "--verbose", type=int,
                        help="specify the detail of written output",
                        choices=[0, 1, 2], default=0)

    args = parser.parse_args()
    main(args.before, args.after, args.verbose)
