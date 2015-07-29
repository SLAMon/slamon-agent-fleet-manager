#!/usr/bin/env python

from setuptools import find_packages, setup

short_description = 'SLAMon Agent Fleet Manager is part of the Coordinator, which controls deployed agents by giving ' \
                    'them tasks and receiving the results. The results are then propagated to e.g. a business process ' \
                    'management system (BPMS).'


setup(
    name='slamon-afm',
    version='1.0.0',
    description=short_description,
    url='https://github.com/SLAMon/slamon-agent-fleet-manager',
    author='SLAMon',
    author_email='slamon.organization@gmail.com',
    license='Apache License v2.0',
    platforms=['Python 3.3+'],
    packages=find_packages(),
    package_data={'slamon_afm.routes.testing': ['testing.html']},
    install_requires=[
        'bottle>=0.12.8, <1.0',
        'sqlalchemy>=1.0.6, <2.0',
        'jsonschema>=2.5.1, <3.0',
        'python_dateutil>= 2.4.2, <3.0'
    ],
    entry_points={
        'console_scripts': [
            'slamon-afm = slamon_afm.afm:main'
        ]
    },
    classifiers=[
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'License :: OSI Approved :: Apache Software License',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: Software Development :: Testing',
        'Topic :: System :: Monitoring'
    ]
)
