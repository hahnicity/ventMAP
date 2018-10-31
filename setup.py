#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


setup(name='ventmap',
      version="1.0",
      description='Ventilator Multi-Analytic Platform for analysis of ventilator waveform data',
      packages=find_packages(exclude=["*tests*"]),
      install_requires=[
          'numpy',
          'pandas',
          'scipy',
      ],
      entry_points={
          'console_scripts': [
              'cut_breath_section=ventmap.cut_breath_section:main',
              'breath_meta=ventmap.breath_meta:main',
          ]
      },
      include_package_data=True,
      )
