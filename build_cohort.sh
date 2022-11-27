#!/bin/sh
# Please specify patient_directory and the place you want to store info.csv before you run the script in default.yaml

raw_patient_dir="${RAW_PATIENT_DIR:-$(yq ".raw_patient_dir" default.yaml)}" 
new_dir="${NEW_DIR:-$(yq ".new_dir" default.yaml)}" 
data_path="${ANON_DATA_PATH:-$(yq ".anon_data_path" default.yaml)}" 

export raw_patient_dir new_dir data_path

anonymize_rawdata(){
    echo "Start anonymizing raw data ..."
    for dir in ${raw_patient_dir}; do
        # Preprocessing file from each patient directories and then anonymize data
	python ventmap/validate_data_type.py $dir
	python ventmap/anonymize_datatimes.py $dir --new-cohort-file $data_path/info.csv --new-dir $new_dir
    done

    echo "Anonymization on raw data finished !!"
}

update_cohort_description(){
    echo "Update cohort description ..."
    python ventmap/redo_cohort_desc_after_anonymization.py --shift-file $data_path/info.csv --non-anon-cohort-desc $data_path/anon-desc.csv
    echo "Update cohort description finished !!"

}

conda_activate(){
    echo "conda activate ards ..."
    cd $HOME/Desktop/ccil_vwd/
    source activate ards
}

baseline(){
    echo "Preprocessed dataset and run baseline ..."    
    python train.py -dp $data_path --cohort-description $data_path/anon-desc.csv --to-pickle processed_dataset.pkl
    echo "Preprocessing dataset finished !!"
}

anonymize_rawdata
update_cohort_description
conda_activate
baseline

