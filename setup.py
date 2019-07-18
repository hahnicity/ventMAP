#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


setup(name='ventmap',
      author='Gregory Rehm',
      author_email='grehm87@gmail.com',
      version="1.3.1",
      description='Ventilator Multi-Analytic Platform for analysis of ventilator waveform data',
      python_requires=">=2.7",
      packages=find_packages(exclude=["*tests*"]),
      install_requires=[
          'numpy',
          'pandas',
          'scipy',
      ],
      entry_points={
          'console_scripts': [
              'clear_null_bytes=ventmap.clear_null_bytes:main',
              'cut_breath_section=ventmap.cut_breath_section:main',
              'breath_meta=ventmap.breath_meta:main',
              'preprocess_breath_files=ventmap.preprocess_all_files:main',
          ]
      },
      include_package_data=True,
      )
