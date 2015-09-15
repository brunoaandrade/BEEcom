#!/usr/bin/env python
# coding=utf-8

# Requirements for the application
INSTALL_REQUIRES = ["pyusb"]

from distutils.core import setup

setup(name='beedriver',
      version='0.1',
      description='BVC Python driver',
      long_description=open("README.md").read(),
      author="BVC Electronic Systems",
      author_email="support@beeverycreative.com",
      license="AGPLv3",
      # packages=['beedriver'],
      py_modules=['beedriver.connection', 'beedriver.commands', 'beedriver.transferThread', 'beedriver.printStatusThread']
      )
