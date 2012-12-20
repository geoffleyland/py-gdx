#!/usr/bin/env python

from distutils.core import setup

setup(
  name         = 'py-gdx',
  version      = '1.0',
  description  = 'Python tools for GAMS GDX',
  author       = 'Geoff Leyland',
  author_email = 'geoff.leyland@incremental.co.nz',
  url          = 'http://github.com/geoffleyland/py-gdx',
  py_modules   = ['gdxx', 'gdxdict'],
  scripts      = ['gdxdump.py', 'gdx_merge.py', 'gdx_list_symbols.py', 'gdx_insert_csv.py', 'gdx_extract_csv.py'],
  )