#!/usr/bin/env python3

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    # Metadata
    name='rdfl_exp',
    version='0.1.0',
    description='Rule Detection with Feedback Loop Experiment',
    url='',
    author='raphael.ollando',
    author_email='raphael.ollando@uni.lu',

    # Install Instructions
    python_requires='>=3.8',
    zip_safe=False,

    # Requirements
    install_requires=[
        # 'javabrigde>=1.0.16',
        'iteround~=1.0.3',
        'liac-arff>=2.5.0',
        'matplotlib~=3.4.2',
        'mininet~=2.3.0.dev6',
        'mysqlclient~=2.0.3',
        'numpy>=1.20.3',
        'pandas~=1.2.4',
        'pexpect~=4.8.0',
        # 'python-weka-wrapper3>=0.2.3',
        'sympy~=1.8',
        'z3-solver>=4.8.12.0',
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

