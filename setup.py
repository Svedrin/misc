#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup

setup(name='fluxd',
      version="0.1",
      description="Fluxmon data collector",
      author="Michael Ziegler",
      author_email='diese-addy@funzt-halt.net',
      url='http://www.fluxmon.de',
      py_modules=['fluxd'],
      packages=["sensors", "wolfgang"]
     )
