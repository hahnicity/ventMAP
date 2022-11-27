# ventMAP Anonymize dataset
vemtMAP software also provide you with data anonymization to avoid PHI

## Motiviation

The goal is to make entire data preprocessing more easier and safer

## Things that script does

 1. anonymize patient id and offshift datetime 
 2. update cohort description file to align with raw data
 3. run baseline machine learning model (Need to clone ccil_vwd repo first)


## Quick start

`build_cohort.sh` is a shell script that helps you anonymize your dataset with random date shifted and random patient id replacement

	# make sure you install yq on your machine
	brew install yq 

	# make sure you specify your data source in default.yaml

	# simply run the shell script, and let the script work for you
	
	sh ../build_cohort.sh


