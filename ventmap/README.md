# ventMAP Anonymize dataset
vemtMAP software also provide you with data anonymization to avoid PHI

## Motiviation

The goal is to make entire data preprocessing more easier and safer. 

## Things that script does

 1. Anonymize patient id and shift datetime from raw data you transfer from the database 
 2. Update cohort description file to align with raw data after anonymization
 3. Run baseline machine learning model (Need to clone ardsdetection repo before you do this ! ) [public ardsdetection repo](https://github.com/hahnicity/ardsdetection) 


## Quick start

`build_cohort.sh` is a shell script that helps you anonymize your dataset with random date shifted and random patient id replacement

	# make sure you install yq on your machine
	brew install yq 

	# specify your data source in default.yaml

	# simply run the shell script, and let the script work for you
		sh ../build_cohort.sh


