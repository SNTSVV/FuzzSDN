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
    name='fuzzsdn',
    version='0.7.0',
    description='A Failure-Inducing Model generation scheme for SDN based systems using Fuzzing and Machine Learning '
                'Techniques',
    url='',
    author='Raphaël Ollando',
    author_email='raphael.ollando@uni.lu',

    # Install Instructions
    python_requires='>=3.8',
    include_package_data=True,
    zip_safe=False,

    # Requirements
    install_requires=install_requires,

    # Packages and Scripts
    packages=[
        'fuzzsdn',
        # Main Application
        'fuzzsdn/app',
        'fuzzsdn/app/analytics',
        'fuzzsdn/app/drivers',
        'fuzzsdn/app/experiment',
        # Commons
        'fuzzsdn/common',
        'fuzzsdn/common/metrics',
        'fuzzsdn/common/openflow',
        'fuzzsdn/common/utils',
        # Report Application
        'fuzzsdn/report',
    ],

    scripts=[
        'bin/fuzzsdn',
    ],
)
