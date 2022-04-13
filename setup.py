#!/usr/bin/env python3

# Import setuptools
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# Load requirements.txt file
with open('requirements.txt', 'r') as f:
    install_requires = f.read().splitlines()

# TODO: add non-python dependencies python-dev, libjpeg-dev, etc.
setup(
    # Metadata
    name='rdfl_exp',
    version='0.2.0',
    description='Rule Detection with Feedback Loop Experiment',
    url='',
    author='raphael.ollando',
    author_email='raphael.ollando@uni.lu',

    # Install Instructions
    python_requires='>=3.8',
    include_package_data=True,
    zip_safe=False,

    # Requirements
    install_requires=install_requires,

    # Packages and Scripts
    packages=[
        'rdfl_exp',
        'rdfl_exp/analytics',
        'rdfl_exp/drivers',
        'rdfl_exp/experiment',
        'rdfl_exp/utils'
    ],

    scripts=[
        'bin/rdfl_exp',
        'bin/rdfl_exp-install'
    ],
)

