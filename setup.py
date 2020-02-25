import re

from setuptools import setup

with open('tappay/__init__.py', 'r') as fd:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', fd.read(), re.MULTILINE).group(1)

setup(
    name='tappay',
    version=version,
    description='TapPay Client Library for Python',
    long_description='This is the Python client library for TapPay\'s API.',
    long_description_content_type="text/markdown",
    url='http://github.com/shihweilo/tappay-python',
    author='Shih Wei Chris Lo',
    author_email='shihwei@gmail.com',
    license='MIT',
    packages=['tappay'],
    platforms=['any'],
    install_requires=['requests>=2.4.2'],
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*",
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ]
)
