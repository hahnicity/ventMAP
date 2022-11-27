"""
    validate_data_type

    validate all files to make sure it can be read in anonymization

"""
import argparse 
from glob import glob
from io import open
import os
import pandas as pd

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('dir')
    args = parser.parse_args()

    files  = glob(os.path.join(args.dir, '*.csv'))
    for filename in files:
        try:
            with open(filename,'r') as f:
                data = f.read()
        except Exception as e:
            data = pd.read_csv(filename,on_bad_lines='skip', encoding="unicode_escape",delim_whitespace=True)
            data = data.astype(str)
            data.to_csv(filename) 

if  __name__=="__main__":
    main()





