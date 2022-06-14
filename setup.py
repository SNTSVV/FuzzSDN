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
    name='figsdn',
    version='0.6.0',
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
        'figsdn',
        # Main Application
        'figsdn/app',
        'figsdn/app/analytics',
        'figsdn/app/drivers',
        'figsdn/app/experiment',
        # Commons
        'figsdn/common',
        'figsdn/common/metrics',
        'figsdn/common/openflow',
        'figsdn/common/openflow/v0x05',
        'figsdn/common/openflow/v0x05/common',
        'figsdn/common/openflow/v0x05/message',
        'figsdn/common/utils',
        # Report Application
        'figsdn/report',
    ],

    scripts=[
        'bin/figsdn',
    ],
)
