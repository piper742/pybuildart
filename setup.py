#!/usr/bin/env python3

from setuptools import setup

setup(
        name = 'pybuildart',
        version = '0.1.0',
        py_modules = ['pybuildart'],
        install_requires = [
            'toml',
            'Pillow',
            ],
        entry_points={
                'console_scripts': [
                    'pybuildart=pybuildart:main',
                ],
            },
        description="CLI BUILD engine ART file creator",
        long_description=open('README.md').read(),
        long_description_content_type='text/markdown',
        author='piper742',
        author_email='petko@matc.sk',
        url='https://github.com/piper742/pybuildart',
        license = "GPL-3.0-or-later",
        classifiers=[
            'Development Status :: 7 - Inactive',
            'Environment :: Console',
            'Topic :: Artistic Software',
            'Topic :: Multimedia :: Graphics :: Graphics Conversion',
            'Intended Audience :: Developers',
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: 3.10',
            'Programming Language :: Python :: 3.11',
            'Programming Language :: Python :: 3.12',
            'Programming Language :: Python :: 3.13',
            'Programming Language :: Python :: 3.14',
            'Operating System :: OS Independent',
        ],
    )
