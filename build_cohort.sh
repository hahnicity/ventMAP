#!/bin/sh
# Please specify patient_directory and the place you want to store info.csv before you run the script in default.yaml

raw_patient_dir="${RAW_PATIENT_DIR:-$(yq ".raw_patient_dir" default.yaml)}" 
new_dir="${NEW_DIR:-$(yq ".new_dir" default.yaml)}" 
info="${INFO:-$(yq ".info" default.yaml)}"
anon_desc="${ANON_DESC:-$(yq ".anon_desc" default.yaml)}"

export raw_patient_dir new_dir info anon_desc

anonymize_rawdata(){
    echo "Start anonymizing raw data ..."
    for dir in ${raw_patient_dir}; do
        # Preprocessing file from each patient directories and then anonymize data
	python ventmap/validate_data_type.py $dir
	python ventmap/anonymize_datatimes.py $dir --new-cohort-file=$info --new-dir=$new_dir
    done

    echo "Anonymization on raw data finished !!"
}

update_cohort_description (){
    echo "Update cohort description"
    python $HOME/Desktop/deepards/deepards/redo_cohort_desc_after_anonymization.py --shift-file=$info --non-anon-cohort-desc=$anon_desc
    echo "Update cohort description finished !"

}

anonymize_rawdata
update_cohort_description


