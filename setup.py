#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


setup(name='ventmap',
      author='Gregory Rehm',
      author_email='grehm87@gmail.com',
      version="1.5.2",
      description='Ventilator Multi-Analytic Platform for analysis of ventilator waveform data',
      python_requires=">=2.7",
      packages=find_packages(exclude=["*tests*"]),
      install_requires=[
          'numpy',
          'pandas',
          'pathlib',
          'prettytable',
          'scipy',
      ],
      entry_points={
          'console_scripts': [
              'anonymize_datetimes=ventmap.anonymize_datatimes:main',
              'add_timestamp_to_vent_file=ventmap.add_timestamp_to_file:main',
              'clear_null_bytes=ventmap.clear_null_bytes:main',
              'cut_breath_section=ventmap.cut_breath_section:main',
              'breath_meta=ventmap.breath_meta:main',
              'preprocess_breath_files=ventmap.preprocess_all_files:main',
          ]
      },
      include_package_data=True,
      )
