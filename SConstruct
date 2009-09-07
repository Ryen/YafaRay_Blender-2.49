#!/usr/bin/env python

PREFIX = '/usr/local'
SCRIPTS = PREFIX + '/share/yafaray/blender'

import sys

if sys.platform == 'linux2' or sys.platform == 'darwin':
	scripts = Glob('*.py')
	for s in scripts:
		Alias('install', InstallAs(SCRIPTS + '/' + str(s), str(s)))

