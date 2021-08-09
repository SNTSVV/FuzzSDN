#!/usr/bin/env python3

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    # Metadata
    name='rdfl_exp',
    version='0.0.1',
    description='Rule Detection with Feedback Loop Experiment',
    url='',
    author='raphael.ollando',
    author_email='raphael.ollando@uni.lu',

    # Install Instructions
    python_requires='>=3.8',
    zip_safe=False,

    # Requirements
    install_requires=[
        'pandas~=1.2.4',
        'numpy>=1.20.3',
        'matplotlib~=3.4.2',
        'sympy~=1.8',
        # 'scikit-learn~=0.24.2',
        # 'javabrigde>=1.0.16',
        # 'python-weka-wrapper3>=0.2.3',
        'mysqlclient~=2.0.3',
        'mininet~=2.3.0.dev6',
        'liac-arff>=2.5.0',
    ],

    # Packages and Scripts
    packages=[
        'rdfl_exp',
        'rdfl_exp/experiment',
        'rdfl_exp/machine_learning',
        'rdfl_exp/utils'
    ],
    scripts=[
        'bin/rdfl_exp'
    ],
)

