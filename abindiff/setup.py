#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='abindiff',
    version='0.0.1',
    description='Utilities for creating and applying patches for binary files',
    author='andreymal',
    author_email='andriyano-31@mail.ru',
    license='MIT',
    platforms='linux',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'abindiff=abindiff.diff:main',
            'abinpatch=abindiff.patch:main',
            'adirdiff=abindiff.dirdiff:main',
            'adirpatch=abindiff.dirpatch:main',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    setup_requires=['pytest-runner'],
    test_suite="tests",
)
