import re

from setuptools import setup

with open('tappay/__init__.py', 'r') as fd:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', fd.read(), re.MULTILINE).group(1)

setup(name='tappay',
      version=version,
      description='TapPay Client Library for Python',
      long_description='This is the Python client library for TapPay\'s API. To use it you\'ll need a TapPay account. Sign up `for free at tappaysdk.com <https://portal.tappaysdk.com/register?src=python-client-library>`_.',
      url='http://github.com/shihweilo/tappay-python',
      author='Shihwei Lo',
      author_email='shihwei@gmail.com',
      license='MIT',
      packages=['tappay'],
      platforms=['any'],
      install_requires=['requests'],
      classifiers=[
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
      ])
