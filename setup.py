from setuptools import setup

setup(
        name = 'pyartbuild',
        version = '0.1.0',
        py_modules = ['pyartbuild'],
        install_requires = [
            'toml',
            'Pillow',
            ],
        entry_points={
                'console_scripts': [
                    'pyartbuild=pyartbuild:main',
                ],
            },
        description="CLI BUILD engine ART file creator",
        long_description=open('README.md').read(),
        long_description_content_type='text/markdown',
        author='piper742',
        author_email='petko@matc.sk',
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Topic :: Artistic Software',
            'Topic :: Multimedia :: Graphics :: Graphics Conversion',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: 3.10',
            'Programming Language :: Python :: 3.11',
            'Programming Language :: Python :: 3.12',
            'Programming Language :: Python :: 3.13',
            'Operating System :: OS Independent',
            'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        ],
    )
