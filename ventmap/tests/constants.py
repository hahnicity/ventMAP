from os.path import dirname, join

NO_BOILERPLATE = lambda x: join(dirname(__file__), "samples", x)

ARDS_AND_COPD = join(dirname(__file__), "samples", "ards-with-copd-and-neg-flows.csv.test")
ARDS_ONLY = join(dirname(__file__), "samples", "ards-alone.csv.test")
BREATH_META1 = join(dirname(__file__), "samples", "breath_meta_test1.csv.test")
BREATH_META1_CONTROL = join(dirname(__file__), "samples", "breath_meta_test1.csv_v5_1_0__breath_meta.csv_test")
JIMMY_TEST = join(dirname(__file__), "samples", "jimmy-example-data.csv.test")
JIMMY_TEST_TOR5 = join(dirname(__file__), "samples/jimmy-example-data/jimmy-example-data.csv_v5_1_0__solo3.csv_test")
RAW_UTILS_TEST = join(dirname(__file__), "samples", "raw_utils.test")
RAW_UTILS_3_COLUMNS_TEST = NO_BOILERPLATE('raw_utils_3_columns.csv.test')
MALFORMED_BREATH = NO_BOILERPLATE("malformed_breath.test")
WITH_TIMESTAMP = join(dirname(__file__), "samples", "vent-file-with-timestamp.csv.test")
WITH_TIMESTAMP_CONTROL = join(dirname(__file__), "samples", "vent-file-with-timestamp_v5_1_0__breath_meta.csv.test")
REAL_TIME_TEST = join(dirname(__file__), "samples", "real_time_raw_utils.test")
TOR_REAL_TIME1 = NO_BOILERPLATE("real_time_tor1.csv.test")
TOR_REAL_TIME2 = NO_BOILERPLATE("real_time_tor2.csv.test")
SPEEDUP_PARSER_ERROR_CASE = NO_BOILERPLATE("speedup-error-case.csv.test")
SPEEDUP_NULL_BYTES_ERROR_CASE = NO_BOILERPLATE("speedup-bm-error-case.csv.test")
SPEEDUP_BAD_ROW_ERROR_CASE = NO_BOILERPLATE("speedup-bad-row-error-case.csv.test")
SPEEDUP_EXTRA_COLS_ERROR_CASE = NO_BOILERPLATE("speedup-extra-cols-error-case.csv.test")
SPEEDUP_NULL_COLS_ERROR_CASE = NO_BOILERPLATE("speedup-null-breath-data-error-case.csv.test")
SPEEDUP_MULTI_BAD_FIRST_LINES_ERROR_CASE = NO_BOILERPLATE("speedup-multi-bad-first-lines-error-case.csv.test")
SPEEDUP_EMPTY_FILE_ERROR_CASE = NO_BOILERPLATE("speedup-empty-file-error-case.csv.test")
SPEEDUP_BE_ERROR_CASE = NO_BOILERPLATE("speedup-no-be-last-row-error-case.csv.test")
PT0149_CSV = join(dirname(__file__), "samples", "0149_2016-02-17-08-38-13_1.csv_test")
PT0149_SUBDIR = join(dirname(__file__), "samples", "0149")
PT0149_BREATH_META = join(PT0149_SUBDIR, "0149_2016-02-17-08-38-13_1_v5_1_0__breath_meta.csv_test")
PT0149_BREATH_META_200TO300 = join(dirname(__file__), "samples", "0149_2016-02-17-08-38-13_1_v5_1_0__breath_meta.csv_test")
