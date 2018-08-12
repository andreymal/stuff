#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.md', 'r', encoding='utf-8-sig') as rfp:
    desc = rfp.read()


import tabun_stat


setup(
    name='tabun_stat',
    version=tabun_stat.__version__,
    description='Statictic calculator for Tabun',
    long_description=desc,
    long_description_content_type='text/markdown',
    author='andreymal',
    author_email='andriyano-31@mail.ru',
    license='MIT',
    platforms='any',
    python_requires='>=3.5',
    packages=find_packages(),
    install_requires=[
        'toml',
        'pytz',
    ],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'tabun_stat=tabun_stat.main:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Flask',
        'License :: OSI Approved',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
)
