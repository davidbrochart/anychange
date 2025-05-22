from importlib.machinery import SourceFileLoader
from pathlib import Path

from setuptools import setup

THIS_DIR = Path(__file__).resolve().parent
long_description = THIS_DIR.joinpath('README.md').read_text()

# avoid loading the package before requirements are installed:
version = SourceFileLoader('version', 'anychange/version.py').load_module()

setup(
    name='anychange',
    version=str(version.VERSION),
    description='Simple, modern file watching and code reload in python.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: MacOS',
        'Environment :: MacOS X',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Filesystems',
        'Framework :: AnyIO',
    ],
    author='Samuel Colvin',
    author_email='s@muelcolvin.com',
    url='https://github.com/davidbrochart/anychange',
    entry_points="""
        [console_scripts]
        anychange=anychange.cli:cli
    """,
    license='MIT',
    packages=['anychange'],
    package_data={'anychange': ['py.typed']},
    install_requires=['anyio>=4.9.0,<5'],
    python_requires='>=3.9',
    zip_safe=True,
)
