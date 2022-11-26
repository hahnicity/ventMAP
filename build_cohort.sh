#!/bin/sh

echo "Start anonymizing raw data ..."

# Please specify patient_directory and the place you want to store info.csv before you run the script in default.yaml
#patient_dir="../unanonymized_data/unanon_70/generalization_dataset/experiment1/all_data/raw/*/"
#new_dir="../anonymized_data/anon_70/experiment1/all_data/raw"
#info="../anonymized_data/anon_70/info.csv"

patient_dir="${PATIENT_DIR:-$(yq ".patient_dir" default.yaml)}"
new_dir="${NEW_DIR:-$(yq ".new_dir" default.yaml)}"
info="${INFO:-$(yq ".info" default.yaml)}"



for dir in ${patient_dir}; do
    python ventmap/anonymize_datatimes.py $dir --new-cohort-file=$info --new-dir=$new_dir
done

echo "Anonymization finished !!"


