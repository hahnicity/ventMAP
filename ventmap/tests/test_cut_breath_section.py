from io import open

from ventmap.cut_breath_section import cut_breath_section
from ventmap.raw_utils import extract_raw
from ventmap.tests.constants import *


def test_newstyle_date_file():
    desc = open(CUT_BREATH_SECTION, encoding='ascii', errors='ignore')
    new_desc = cut_breath_section(desc, 1, 100)
    gen = extract_raw(new_desc, False)
    for b in gen:
        assert 1 <= b['rel_bn'] <= 100
