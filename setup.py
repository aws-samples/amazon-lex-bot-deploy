#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

import sys
import os

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist bdist_wheel')
    os.system('twine upload dist/*')
    sys.exit()

requirements = ['boto3', 'botocore', 'tenacity']

setup_requirements = [ ]

test_requirements = [ ]

setup(
    author="Martin Schade",
    author_email='amazon-lex-bot-deploy@amazon.com',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="The sample code provides a deploy function and an executable to easily deploy an Amazon Lex bot based on a Lex Schema file.",
    install_requires=requirements,
    scripts=['bin/lex-bot-deploy', 'bin/lex-bot-get-schema'],
    license="MIT-0 license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='amazon_lex_bot_deploy Amazon Lex Automation Deploy CICD',
    name='amazon_lex_bot_deploy',
    packages=find_packages(include=['amazon_lex_bot_deploy']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/aws-samples/amazon_lex_bot_deploy',
    version='0.1.7',
    zip_safe=False,
)
