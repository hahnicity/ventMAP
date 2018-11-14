# ventMAP
Open source multi-purpose ventilator analytics library for use analyzing ventilator waveform data.

Currently only data output from the Purittan Bennet 840 (PB-840) is supported, but we welcome
contributions to support addition of other ventilators as well.

## Install

    pip install ventmap

## API

### Basics
For reading ventilator data:

    from ventmap.raw_utils import extract_raw

    # create generator that will iterate through file. Specify False to ensure that
    # breaths without BS/BE markers will be dropped. If you say True, then breaths
    # without BS/BE will be kept
    generator = extract_raw(open(<filepath to vent data>), False)
    for breath in generator:
        # breath data is output in dictionary format
        flow, pressure = breath['flow'], breath['pressure']

For extracting metadata (I-Time, TVe, TVi) from files.

    from ventmap.breath_meta import get_file_breath_meta

    # Data output is normally in list format. Ordering information can be found in
    # ventmap.constants.META_HEADER.
    breath_meta = get_file_breath_meta(<filepath to vent data>)
    # If you want a pandas DataFrame then you can set the optional argument to_data_frame=True
    breath_meta = get_file_breath_meta(<filepath to vent data>, to_data_frame=True)


For extracting metadata from individual breaths

    # production breath meta refers to clinician validated algorithms
    # experimental breath meta refers to non-validated algorithms
    from ventmap.breath_meta import get_production_breath_meta, get_experimental_breath_meta
    from ventmap.raw_utils import extract_raw

    generator = extract_raw(open(<filepath to vent data>), False)
    for breath in generator:
        # Data output is normally in list format. Ordering information can be found in
        # ventmap.constants.META_HEADER.
        prod_breath_meta = get_production_breath_meta(breath)
        # Ordering information can be found in ventmap.constants.EXPERIMENTAL_META_HEADER.
        experimental_breath_meta = get_experimental_breath_meta(breath)

### Extras

Clear null bytes from a file

    from ventmap.clear_null_bytes import clear_descriptor_null_bytes

    cleared_descriptor = clear_descriptor_null_bytes(open(<filepath to vent data>))

Cut a file into specific BN interval and store for later use

    from ventmap.cut_breath_section import cut_breath_section

    # get file descriptor for the truncated data
    new_descriptor = cut_breath_section(open(<filepath to vent data>), <breath start num>, <breath end num>)
    # write output to file
    with open('new_file', 'w') as f:
        f.write(new_descriptor.read())

Check if there is a plateau pressure in a breath


    from ventmap.raw_utils import extract_raw
    from ventmap.SAM import check_if_plat_occurs

    generator = extract_raw(open(<filepath to vent data>), False)
    for breath in generator:
        flow, pressure = breath['flow'], breath['pressure']

        # .02 is the sampling rate for the PB-840 corresponding with 1 obs every .02 seconds
        did_plat_occur = check_if_plat_occurs(flow, pressure, .02)
