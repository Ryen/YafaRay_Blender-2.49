#!BPY

"""
Name: 'YafaRay Instant Render'
Blender: 249
Group: 'Render'
Tooltip: 'Run this and render Yafaray instantly with no ui'
"""

__author__ = ['Rodrigo Placencia (DarkTide) & mods by Mitch Hughes (lobo_nz)']
__version__ = '0.0.1'
__url__ = ['http://www.yafaray.org','http://www.farmerjoe.info']
__bpydoc__ = """\

"""
# This script can be used from a command line like this:
#WINDOWS
#call SET "YAFRENDERDIR=r:\path to output\frames"&SET YAFANIM="true"&"r:\bin\path to blender\Blender.exe" -b "r:\path to blend\yafaray.blend" -s "1" -e "1" -P "r:\path to script\yafCliRender.py"
#*NIX (Including OSX)
#YAFRENDERDIR="r:\path to output\frames" YAFANIM="true" "r:\bin\path to blender\Blender.exe" -b "r:\path to blend\yafaray.blend" -s "1" -e "1" -P "r:\path to script\yafCliRender.py"

#########

# import order IS important for sys.path.append seemingly
import sys
import os
import platform
import Blender

# Enter the abolsute path to the YafaRay directory or the relative path
# (as seen from Blender.exe)
# If you have a directory structure like this:
#
# ,- Blender (containing Blender.exe)
# +- YafaRay
# + ...
#
# then set dllPath = "..\\YafaRay\\"
# dllPath = "..\\YafaRay\\"

dllPath = ""
IESPath = ""
pythonPath = ""
haveQt = False

_SYS = platform.system()

if _SYS == 'Windows':
	if dllPath == "":
		import _winreg
		regKey = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, 'Software\\YafRay Team\\YafaRay')
		dllPath = _winreg.QueryValueEx(regKey, 'InstallDir')[0] + '\\'

	if pythonPath == "":
		pythonPath = dllPath + 'python\\'

	from ctypes import cdll
	dlls = ['zlib1','libpng3','jpeg62','Iex','Half','IlmThread',\
		'IlmImf','mingwm10','freetype6','yafraycore', 'yafarayplugin']

	for dll in dlls:
		print "Loading DLL: " + dllPath + dll + '.dll'
		cdll.LoadLibrary(dllPath + dll + '.dll')
	
	IESPath = str(dllPath + 'iesFiles\\')
	dllPath = str(dllPath + 'plugins\\')

# append a non-empty pythonpath to sys
if pythonPath != "":
	pythonPath = os.path.normpath(pythonPath)
	sys.path.append(pythonPath)

# assume for all non-windows systems unix-like paths,
# add search paths for the scripts
if _SYS != 'Windows':
	if pythonPath == "":
		searchPaths = []
		searchPaths.append(os.environ['HOME'] + '/.blender/scripts/yafaray/')
		searchPaths.append('/usr/local/share/yafaray/blender/')
		searchPaths.append('/usr/share/yafaray/blender/')
		searchPaths.append(Blender.Get('scriptsdir') + '/yafaray/')
		for p in searchPaths:
			if os.path.exists(p):
				if os.path.exists( str(p + 'iesFiles/') ):
					IESPath = str(p + 'iesFiles/')

				sys.path.append(p)

import string
import math

import yaf_export
from yaf_export import yafrayRender
import yafrayinterface

from Blender import *

yaf_export.dllPath = dllPath
yaf_export.IESPath = IESPath
yaf_export.haveQt = haveQt

yafanim = False

yRender = yafrayRender()

print "Starting render process: Animation [" + str(yafanim) + "]"

if not yafanim:
	yRender.renderCL()
else:
	yRender.renderAnim()

