#!BPY

"""
Name: 'YafaRay Export 0.1.1'
Blender: 248
Group: 'Render'
Tooltip: 'YafaRay Export'
"""

__author__ = ['Bert Buchholz, Alvaro Luna, Michele Castigliego, Rodrigo Placencia']
__version__ = '0.1.1'
__url__ = ['http://yafaray.org']
__bpydoc__ = ""


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
pythonPath = ""
haveQt = True

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
		'IlmImf','mingwm10','libfreetype-6','yafraycore', 'yafarayplugin']

	qtDlls = ['QtCore4', 'QtGui4', 'yafarayqt']
	if os.path.exists(dllPath + 'yafarayqt.dll'):
		dlls += qtDlls
	else:
		haveQt = False
		print "WARNING: Qt GUI will NOT be available."

	for dll in dlls:
		print "Loading DLL: " + dllPath + dll + '.dll'
		cdll.LoadLibrary(dllPath + dll + '.dll')
	
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
				sys.path.append(p)

if haveQt:
	try:
		import yafqt
	except:
		haveQt = False
		print "ERROR: Importing yafqt failed, Qt GUI will NOT be available."


import string
import math

import yaf_export
from yaf_export import yafrayRender
import yafrayinterface

from Blender import *

yaf_export.dllPath = dllPath
yaf_export.haveQt = haveQt

#####################################
#
#  Utility functions
#
#####################################

# compare the version of the script against that of the interface _only_
# if we have a release version number (i.e. MAJOR.MINOR.SOMETHING)
def checkVersion(ver):
	yi = yafrayinterface.yafrayInterface_t()
	interfaceVersion = yi.getVersion()
	verNumbers = interfaceVersion.split('.')
	if verNumbers != None:
		if len(verNumbers) == 3:
			# print "intVer", interfaceVersion, "ver", ver
			if interfaceVersion != ver:
				return [False, interfaceVersion]
	return [True, interfaceVersion]

uniqeCounter = 0

def getUniqueValue():
	global uniqeCounter
	uniqeCounter += 1
	return uniqeCounter

def drawHLine(x, y, width):
	BGL.glColor3f(0,0,0)
	BGL.glBegin(BGL.GL_LINES)
	BGL.glVertex2i(x, y)
	BGL.glVertex2i(x + width, y)
	BGL.glEnd()

def drawSepLine(x, y, width):
	y -= 15
	drawHLine(x, y, width)
	y -= 25
	return y

def drawSepLineText(x, y, width, text):
	y -= 15
	drawText(x, y - 3, text)
	width = width - 5 - Draw.GetStringWidth(text, "small")
	drawHLine(x + Draw.GetStringWidth(text, "small") + 5, y, width)
	y -= 25
	return y

def drawText(x, y, text, size = "small"):
	BGL.glRasterPos2i(x, y)
	Draw.Text(text, size)

def drawTextLine(x, y, text, size = "small"):
	BGL.glRasterPos2i(x, y)
	Draw.Text(text, size)
	y -= 13;
	return y

# draw a complete paragraph, lines will be on wordlength longer than maxWidth
def drawTextParagraph(x, y, maxWidth, text, size = "small"):
	BGL.glRasterPos2i(x, y)
	words = string.split(text, ' ')
	length = 0
	line = ""
	i = 0
	for w in words:
		line += w + " "
		length = Draw.GetStringWidth(line, size)

		if i < len(words)-1:
			lenNextWord = Draw.GetStringWidth(words[i+1], size)
		else: lenNextWord = 0

		if length + lenNextWord > maxWidth:
			y = drawTextLine(x, y, line, size)
			line = ""
			length = 0

		if w == '\n':
			y = drawTextLine(x, y, line, size)
			line = ""
			length = 0

		i += 1

	y = drawTextLine(x, y, line, size)

	return y

# create a menu string for blender draw.menu out of a list of strings
def makeMenu(text, list):
	i = 0
	MenuStr = text + "%t|"

	for c in list:
		MenuStr += c + " %x" + str(i) + "|"
		i = i + 1

	return MenuStr

def copyParams(source, target):
	for p in source:
		if not target.has_key(p):
			target[p] = source[p]

def copyParamsOverwrite(source, target):
	for p in source:
		try:
			# print "no problem with: ", source, target, p, source[p], target[p]
			target[p] = source[p]
		except:
			print "problem with: ", source, target, p, source[p]
			target[p] = 0.0

def setParam(gui, key, poly, field):
	# poly is either a list or the initVal (latter here not needed)
	if type(poly) == list:
		field[key] = poly[gui.val]
	else:
		field[key] = gui.val


def setGUIVals(gui, key, poly, field):
	# poly is either a list or the initial value (latter here not needed)
	# print gui, key, poly, field
	if type(poly) == list: # lists (for menus)
		if field.has_key(key):
			# need this exception handling in case a list item has been set that has been removed in the meantime (for example,
			# a material has been renamed or deleted from the Blend file)
			try:
				gui.val = poly.index(field[key])
			except:
				gui.val = 0
	elif type(poly) == tuple: # color
		if field.has_key(key):
			gui.val = (field[key][0], field[key][1], field[key][2])
	elif type(poly) == str: # string
		if field.has_key(key):
			gui.val = field[key][:]
	else: # ints, floats
		if field.has_key(key):
			gui.val = field[key]

# checks if key exists in field and if not, create property and assign initial value
def checkParam(gui, key, poly, field):
	try:
		if not field.has_key(key):
			if type(poly) == list: # lists (for menus)
				field[key] = poly[0]
			else: # ints, floats, strings, colors etc.
				field[key] = poly
	except:
		pass

# A standin function to give to Draw.Number. For some weird reason it does not
# except a simple None
def dummyfunc(*args):
	pass

# ### tab material ### #


# TODO: experimental new structure, fubar atm
class BlendMat:
	def __init__(self, mat):
		#print "init blend mat"
		self.matProp = mat.properties['YafRay']
		self.evEdit = getUniqueValue()

		self.mats = Blender.Material.Get()
		self.index = self.mats.index(mat)
		#print self.index

		self.menuMat1 = Draw.Create(0)
		self.material = mat
		#print " with mat: ", self.material
		#(self.guiMatBlendMat1, "material1", "", matProp),
		#(self.guiMatBlendMat2, "material2", "", matProp)]

	def draw(self, height, guiWidgetHeight):
		height += guiHeightOffset
		drawText(10, height + 4, "Absorp. color:")
		height += guiHeightOffset

		i = 0
		matMenuEntries = "Material 1 %t|"
		for mat in self.mats:
			if mat.lib:
				matMenuEntries += "L " + mat.name + " %x" + str(i) + "|"
			else:
				matMenuEntries += mat.name + " %x" + str(i) + "|"
			i = i + 1

		self.menuMat1 = Draw.Menu(matMenuEntries,
			self.evEdit, 100, height, 150, guiWidgetHeight, self.index + 1, "")
			#self.evEdit, 100, height, 150, guiWidgetHeight, self.index, "")
			#self.evEdit, 100, height, 150, guiWidgetHeight, self.menuMat1.val, "")

		return height

	def event(self):
		self.matProp['material1'] = self.mats[self.menuMat1.val].name
		#self.matProp['material2'] = self.mats[self.menuMat2.val]

class clTabMaterial:
	def __init__(self):
		# preview image
		self.yRender = yaf_export.yafrayRender(isPreview = True)
		self.previewImage = Image.New("yafPrev", 320, 320, 32)
		self.previewSize = 100

		# events
		self.evShow = getUniqueValue()
		self.evEdit = getUniqueValue()
		self.evChangeMat = getUniqueValue()
		self.evRefreshPreview = getUniqueValue()
		self.evMatFromObj = getUniqueValue()

		self.tabNum = getUniqueValue()

		self.matObject = None

		self.materialsByMenu = False
		#yafDict = Registry.GetKey('YafaRay', True)
		#try:
		#	self.materialsByMenu = yafDict['materialsByMenu']
		#except:
		#	yafDict = {}
		#	yafDict['materialsByMenu'] = self.materialsByMenu
		#	Blender.Registry.SetKey('YafaRay', yafDict, True)

		# lists
		self.connector = []
		# class-specific types and lists
		self.matTypes = ["shinydiffusemat", "glossy", "coated_glossy", "glass", "Rough Glass", "blend"]
		self.BRDFTypes = ["Normal (Lambert)", "Oren-Nayar"]

		self.materials = []

		self.blenderMat = None # actual blender material currently shown

		for mat in Blender.Material.Get():
			# Check if this is a linked material
			if mat.lib:
				self.materials.append("L "+mat.name)
			else:
				self.materials.append(mat.name)

		# properties
		self.curMat = {}

		# gui elements
		self.guiMatShowPreview = Draw.Create(1)
		self.guiMatPreviewSize = Draw.Create(self.previewSize)
		self.guiMatMenu = Draw.Create(0)
		self.guiMatSelectFromObj = Draw.Create(0)
		self.guiMatDiffuse = Draw.Create(1.0)
		self.guiMatSpecular = Draw.Create(0.0)
		self.guiMatColor = Draw.Create(1.0,1.0,1.0)
		self.guiMatDiffuseColor = Draw.Create(1.0,1.0,1.0)
		self.guiMatMirrorColor = Draw.Create(1.0,1.0,1.0)
		self.guiMatTransparency = Draw.Create(0.0)
		self.guiMatTranslucency = Draw.Create(0.0)
		self.guiMatEmit = Draw.Create(0.0)
		self.guiMatFresnel = Draw.Create(0) # Toggle
		self.guiMatGlossyReflect = Draw.Create(0.0)
		self.guiMatExponent = Draw.Create(0.0)
		self.guiMatAsDiffuse = Draw.Create(0)
		self.guiMatIOR = Draw.Create(1.0) # slider
		self.guiMatFilterColor = Draw.Create(1.0,1.0,1.0)
		self.guiMatAnisotropy = Draw.Create(0) # toggle
		self.guiMatExpU = Draw.Create(50.0) # slider
		self.guiMatExpV = Draw.Create(50.0) # slider
		self.guiMatAbsorptionColor = Draw.Create(1.0,1.0,1.0)
		self.guiMatAbsorptionDist = Draw.Create(1.0)
		self.guiMatTransmit = Draw.Create(0.0)
		self.guiMatDispersion = Draw.Create(0.0)
		self.guiMatFakeShadow = Draw.Create(0) # toggle
		self.guiMatAssign = Draw.Create(1)
		self.guiMatType = Draw.Create(1) # menu
		self.guiMatBlendMat1 = Draw.Create(1) # menu
		self.guiMatBlendMat2 = Draw.Create(1) # menu
		self.guiMatBlendValue = Draw.Create(0.5) # slider
		self.guiMatDiffuseBRDF = Draw.Create(1) # menu
		self.guiMatSigma = Draw.Create(0.0) # number
		#self.guiMatByMenu = Draw.Create(self.materialsByMenu) # toggle
		self.guiShowActiveMat = Draw.Create(0) # toggle

		for mat in Blender.Material.Get():
			self.setPropertyList(mat)

	# call before drawing and once in __init__
	def setPropertyList(self, mat = None):
		if mat == None:
			try:
				mat = Blender.Material.Get()[self.guiMatMenu.val]
			except:
				print "Material doesn't exist!"
				self.curMat = {}
				return

		# print "setProps:", mat
		if not mat.properties.has_key("YafRay"):
			mat.properties['YafRay'] = {}

		self.curMat = mat.properties['YafRay']
		matProp = self.curMat

		self.blenderMat = mat

		self.materials = []
		for m in Blender.Material.Get():
			self.materials.append(m.name)

		# connect gui elements with id properties
		# <gui element>, <property name>, <default value or type list>, <property group>
		self.connector = [(self.guiMatType, "type", self.matTypes, matProp),
			(self.guiMatDiffuse, "diffuse_reflect", 1.0, matProp),
			(self.guiMatSpecular, "specular_reflect", 0.0, matProp),
			(self.guiMatColor, "color", (1.0, 1.0, 1.0), matProp),
			(self.guiMatDiffuseColor, "diffuse_color", (1, 1, 1), matProp),
			(self.guiMatMirrorColor, "mirror_color", (1.0, 1.0, 1.0), matProp),
			(self.guiMatTransparency, "transparency", 0.0, matProp),
			(self.guiMatTranslucency, "translucency", 0.0, matProp),
			(self.guiMatEmit, "emit", 0.0, matProp),
			(self.guiMatFresnel, "fresnel_effect", False, matProp),
			(self.guiMatGlossyReflect, "glossy_reflect", 0.0, matProp),
			(self.guiMatExponent, "exponent", 500.0, matProp),
			(self.guiMatAsDiffuse, "as_diffuse", False, matProp),
			(self.guiMatIOR, "IOR", 1.0, matProp),
			(self.guiMatFilterColor, "filter_color", (1.0, 1.0, 1.0), matProp),
			(self.guiMatAnisotropy, "anisotropic", False, matProp),
			(self.guiMatExpU, "exp_u", 50.0, matProp),
			(self.guiMatExpV, "exp_v", 50.0, matProp),
			(self.guiMatAbsorptionColor, "absorption", (1.0, 1.0, 1.0), matProp),
			(self.guiMatAbsorptionDist, "absorption_dist", 1.0, matProp),
			(self.guiMatTransmit, "transmit_filter", 1.0, matProp),
			(self.guiMatDispersion, "dispersion_power", 0.0, matProp),
			(self.guiMatFakeShadow, "fake_shadows", False, matProp),
			(self.guiMatBlendMat1, "material1", self.materials, matProp),
			(self.guiMatBlendMat2, "material2", self.materials, matProp),
			(self.guiMatBlendValue, "blend_value", 0.5, matProp),
			(self.guiMatDiffuseBRDF, "brdfType", self.BRDFTypes, matProp),
			(self.guiMatSigma, "sigma", 0.1, matProp)]

		#print "mat connecting"
		 # add missing parameters to the property ID
		for el in self.connector:
			checkParam(el[0], el[1], el[2], el[3])

		#yafDict = {}
		#self.materialsByMenu = not self.guiShowActiveMat.val
		#yafDict['materialsByMenu'] = self.materialsByMenu
		#Blender.Registry.SetKey('YafaRay', yafDict, True)



	def draw(self, height):
		global libmat, PanelHeight
		if self.blenderMat.lib:
			libmat = True
		else:
			libmat = False

		drawText(10, height, "Material settings", "large")

		height = drawSepLineText(10, height, 320, "Material")

		try:
			Blender.Material.Get()[0]
		except:
			self.curMat = {}
			drawText(10, height, "No materials defined in Blender UI!", "large")
			return

		self.guiShowActiveMat = Draw.Toggle("Always show active object", self.evChangeMat, 10,
			height, 320, guiWidgetHeight, self.guiShowActiveMat.val, "Always show the material of the active object")
		height += guiHeightOffset

		# always init the menu for the blend mat
		i = 0
		matMenuEntries = "Materials %t|"
		for mat in Blender.Material.Get():
			if mat.lib:
				matMenuEntries += "L " + mat.name + " %x" + str(i) + "|"
			else:
				matMenuEntries += mat.name + " %x" + str(i) + "|"
			i = i + 1

		if not self.guiShowActiveMat.val:
			self.guiMatMenu = Draw.Menu(matMenuEntries, self.evChangeMat, 10, height, 150, guiWidgetHeight,
				self.guiMatMenu.val, "selects an existing Blender material")
			self.guiMatSelectFromObj = Draw.PushButton("From active object", self.evMatFromObj, 180, height,
				150, guiWidgetHeight, "Select material from active object")
		else:
			try:
				currentSelection = Object.GetSelected()[0]
			except:
				currentSelection = None

			if currentSelection == None:
				drawText(10, height, "Nothing selected", "large")
				return

			if currentSelection.getType() not in ['Mesh', 'Curve']:
				drawText(10, height, "Object is no mesh", "large")
				return
			num = currentSelection.activeMaterial
			mesh = currentSelection.getData()
			if len(mesh.materials) == 0:
				drawText(10, height, "Object has no material", "large")
				return
			m = mesh.materials[num - 1]
			if m != self.blenderMat:
				self.setPropertyList(m)
				for el in self.connector:
					setGUIVals(el[0], el[1], el[2], el[3])
				self.refreshPreview()

			drawText(10, height + 4, m.name)


		height = drawSepLineText(10, height, 320, "Material Preview")

		self.guiMatShowPreview = Draw.Toggle("Show Preview ", 0, 10,
			height, 150, guiWidgetHeight, self.guiMatShowPreview.val, "")

		if (self.guiMatShowPreview.val == 1):
			self.guiMatPreviewSize = Draw.Slider("Size: ", 0, 180,
				height, 150, guiWidgetHeight, self.guiMatPreviewSize.val, 100, 320)

			height += guiHeightOffset
			Draw.Image(self.previewImage, 10, height - self.previewSize + 10, 1, 1, 0, 0, self.previewSize, self.previewSize)

			height -= self.previewSize - guiHeightOffset;

			self.guiRefreshPreview = Draw.PushButton("Refresh Preview", self.evRefreshPreview, 10, height,
				self.previewSize, guiWidgetHeight, "Refresh the preview image.")


		height = drawSepLineText(10, height, 320, "Settings")

		drawText(10, height + 4, "Material type: ")
		self.guiMatType = Draw.Menu(makeMenu("Material type", self.matTypes),
			self.evEdit, 100, height, 230, guiWidgetHeight, self.guiMatType.val, "Assign material type")

		if self.curMat['type'] == "shinydiffusemat":
			height += guiHeightOffset
			drawText(10, height + 4, "Color:")
			self.guiMatColor = Draw.ColorPicker(self.evEdit, 100,
				height, 230, guiWidgetHeight, self.guiMatColor.val, "Base color of diffuse component")

			height += guiHeightOffset
			drawText(10, height + 4, "Mirror color:")
			self.guiMatMirrorColor = Draw.ColorPicker(self.evEdit, 100,
				height, 230, guiWidgetHeight, self.guiMatMirrorColor.val , "Color filter for mirrored rays")

			height += guiHeightOffset
			self.guiMatDiffuse = Draw.Slider("Diffuse reflection: ", self.evEdit, 10,
				height, 320, guiWidgetHeight, self.guiMatDiffuse.val, 0.0, 1.0, 0, "Amount of diffuse reflection")

			height += guiHeightOffset
			self.guiMatSpecular = Draw.Slider("Mirror strength: ", self.evEdit, 10,
				height, 320, guiWidgetHeight, self.guiMatSpecular.val, 0.0, 1.0, 0, "Amount of perfect specular reflection (mirror)")

			height += guiHeightOffset
			self.guiMatTransparency = Draw.Slider("Transparency: ", self.evEdit, 10,
				height, 320, guiWidgetHeight, self.guiMatTransparency.val, 0.0, 1.0, 0, "material transparency")

			height += guiHeightOffset
			self.guiMatTranslucency = Draw.Slider("Translucency: ", self.evEdit, 10,
				height, 320, guiWidgetHeight, self.guiMatTranslucency.val, 0.0, 1.0, 0, "Amount of diffuse transmission (translucency)")

			height += guiHeightOffset
			self.guiMatTransmit = Draw.Slider("Transmit filter: ", self.evEdit, 10,
				height, 320, guiWidgetHeight, self.guiMatTransmit.val, 0.0, 1.0, 0, "Amount of tinting of light passing through material")

			height += guiHeightOffset
			
			self.guiMatEmit = Draw.Number("Emit: ", self.evEdit, 10,
				height, 320, guiWidgetHeight, self.guiMatEmit.val, 0.0, 1000.0, "Amount of light the material emits",
				dummyfunc, 10.0, 1.0)

			height += guiHeightOffset
			self.guiMatFresnel = Draw.Toggle("Fresnel ", self.evEdit, 10,
				height, 320, guiWidgetHeight, self.guiMatFresnel.val, "Apply fresnel effect to specular components")

			if self.guiMatFresnel.val == 1:
				height += guiHeightOffset
				self.guiMatIOR = Draw.Slider("IOR: ", self.evEdit, 10,
					height, 320, guiWidgetHeight, self.guiMatIOR.val, 1.0, 30.0, 0, "Refraction index for fresnel effect")

			height += guiHeightOffset
			self.guiMatDiffuseBRDF = Draw.Menu(makeMenu("BRDF type", self.BRDFTypes),
				self.evEdit, 10, height, 150, guiWidgetHeight, self.guiMatDiffuseBRDF.val, "")
				
			height += guiHeightOffset

			if (self.BRDFTypes[self.guiMatDiffuseBRDF.val] == 'Oren-Nayar'):
				height += guiHeightOffset
				self.guiMatSigma = Draw.Number("Sigma", self.evEdit, 10,
					height, 150, guiWidgetHeight, self.guiMatSigma.val, 0.0, 1.0, "")


			height += guiHeightOffset
			height = drawTextLine(10, height, "Mappable texture slots, Yafaray <- Blender:")
			height = drawTextLine(10, height, "Bump <- Nor")
			height = drawTextLine(10, height, "Diffuse <- Col")
			height = drawTextLine(10, height, "Mirror <- RayMir")
			height = drawTextLine(10, height, "Transparency <- Alpha")
			height = drawTextLine(10, height, "Translucency <- TransLu")

		elif self.curMat['type'] == "glossy" or self.curMat['type'] == "coated_glossy": # Glossy material settings
			height += guiHeightOffset
			drawText(10, height + 4, "Diff. color:")
			self.guiMatDiffuseColor = Draw.ColorPicker(self.evEdit, 100,
				height, 230, guiWidgetHeight, self.guiMatDiffuseColor.val, "Diffuse Reflection Color")

			height += guiHeightOffset
			drawText(10, height + 4, "Glossy color:")
			self.guiMatColor = Draw.ColorPicker(self.evEdit, 100,
				height, 230, guiWidgetHeight, self.guiMatColor.val, "Glossy Color")

			height += guiHeightOffset
			self.guiMatDiffuse = Draw.Slider("Diffuse reflection: ", self.evEdit, 10,
				height, 320, guiWidgetHeight, self.guiMatDiffuse.val, 0.0, 1.0, 0, "Amount of diffuse reflection")

			height += guiHeightOffset
			self.guiMatGlossyReflect = Draw.Slider("Glossy reflection: ", self.evEdit, 10,
				height, 320, guiWidgetHeight, self.guiMatGlossyReflect.val, 0.0, 1.0, 0, "Amount of glossy reflection")

			height += guiHeightOffset
			self.guiMatExponent = Draw.Slider("Exponent: ", self.evEdit, 10,
				height, 320, guiWidgetHeight, self.guiMatExponent.val, 1.0, 5000.0, 0, "Reflection blur, no effect if Anisotropic is on")

			height += guiHeightOffset
			self.guiMatAsDiffuse = Draw.Toggle("As diffuse ", self.evEdit, 10,
				height, 320, guiWidgetHeight, self.guiMatAsDiffuse.val, "Treat glossy component as diffuse")

			height += guiHeightOffset
			self.guiMatAnisotropy = Draw.Toggle("Anisotropic ", self.evEdit, 10,
				height, 320, guiWidgetHeight, self.guiMatAnisotropy.val, "Use anisotropic reflections")

			if (self.guiMatAnisotropy.val == 1):
				height += guiHeightOffset
				self.guiMatExpU = Draw.Slider("Exponent Horizontal: ", self.evEdit, 10,
					height, 320, guiWidgetHeight, self.guiMatExpU.val, 1.0, 10000.0, 0, "u-exponent for anisotropy")
				height += guiHeightOffset
				self.guiMatExpV = Draw.Slider("Exponent Vertical: ", self.evEdit, 10,
					height, 320, guiWidgetHeight, self.guiMatExpV.val, 1.0, 10000.0, 0,"v-exponent for anisotropy")

			if self.curMat['type'] == "coated_glossy": # extension for coatedGlossy material
				height += guiHeightOffset
				self.guiMatIOR = Draw.Slider("IOR: ", self.evEdit, 10,
					height, 320, guiWidgetHeight, self.guiMatIOR.val, 1.0, 30.0, 0, "Index of refraction for fresnel effect of the coating top layer")

			height += guiHeightOffset
			height = drawTextLine(10, height, "Mappable texture slots, Yafaray <- Blender:")
			height = drawTextLine(10, height, "Bump <- Nor")
			height = drawTextLine(10, height, "Diffuse <- Col")
			height = drawTextLine(10, height, "Glossy Reflection <- Spec")
			height = drawTextLine(10, height, "Glossy Color <- Csp")


		if self.curMat['type'] == "glass" or self.curMat['type'] == "Rough Glass": # glass material
			height += guiHeightOffset
			drawText(10, height + 4, "Absorp. color:")
			self.guiMatAbsorptionColor = Draw.ColorPicker(self.evEdit, 100, height,
				230, guiWidgetHeight, self.guiMatAbsorptionColor.val, "Glass volumetric absorption color. White disables absorption")

			height += guiHeightOffset
			self.guiMatAbsorptionDist = Draw.Slider("Absorp. Distance:", self.evEdit, 10, height,
				320, guiWidgetHeight, self.guiMatAbsorptionDist.val, 0.0, 100.0, True, "Absorption distance scale")

			height += guiHeightOffset
			drawText(10, height + 4, "Filter color:")
			self.guiMatFilterColor = Draw.ColorPicker(self.evEdit, 100, height,
				230, guiWidgetHeight, self.guiMatFilterColor.val, "Filter color applied for refracted light")

			height += guiHeightOffset
			drawText(10, height + 4, "Mirror color:")
			self.guiMatMirrorColor = Draw.ColorPicker(self.evEdit, 100, height,
				230, guiWidgetHeight, self.guiMatMirrorColor.val, "Filter color applied for reflected light")

			height += guiHeightOffset
			self.guiMatIOR = Draw.Slider("IOR: ", self.evEdit, 10,
				height, 320, guiWidgetHeight, self.guiMatIOR.val, 1.0, 30.0, 0, "Index of refraction")
			
			if self.curMat['type'] == "Rough Glass":
				height += guiHeightOffset
				self.guiMatExponent = Draw.Slider("Exponent: ", self.evEdit, 10,
					height, 320, guiWidgetHeight, self.guiMatExponent.val, 1.0, 5000.0, 0, "Exponent of glass roughness (lower = rougher)")

			height += guiHeightOffset
			self.guiMatTransmit = Draw.Slider("Transmit Filter: ", self.evEdit, 10,
				height, 320, guiWidgetHeight, self.guiMatTransmit.val, 0.0, 1.0, 0, "Filter strength applied to refracted light")

			height += guiHeightOffset
			self.guiMatDispersion = Draw.Slider("Dispersion Power: ", self.evEdit, 10,
				height, 320, guiWidgetHeight, self.guiMatDispersion.val, 0.0, 10000.0, 0, "Strength of dispersion effect, disabled when 0")

			height += guiHeightOffset
			self.guiMatFakeShadow = Draw.Toggle("Fake shadows ", self.evEdit, 10,
				height, 320, guiWidgetHeight, self.guiMatFakeShadow.val, "Let light straight through for shadow calculation. Not to be used with dispersion")

			height += guiHeightOffset
			height = drawTextLine(10, height, "Mappable texture slots, Yafaray <- Blender:")
			height = drawTextLine(10, height, "Bump <- Nor")

		elif self.curMat['type'] == "blend":
			#height = self.matObject.draw(height, guiWidgetHeight)
			height += guiHeightOffset
			height = drawTextLine(10, height, " ")
			height = drawTextParagraph(10, height, 300, "Choose the two materials you wish to blend. " +
				"You can weight them with the blend value or texture maps. Use the COL texture channel "+
				"of the blending material to blend two materials using a texture map.")

			height += guiHeightOffset
			self.guiMatBlendMat1 = Draw.Menu(matMenuEntries, self.evEdit, 10, height, 150, guiWidgetHeight, self.guiMatBlendMat1.val, "Material 1")
			self.guiMatBlendMat2 = Draw.Menu(matMenuEntries, self.evEdit, 180, height, 150, guiWidgetHeight, self.guiMatBlendMat2.val, "Material 2")

			height += guiHeightOffset
			self.guiMatBlendValue = Draw.Slider("Blend value: ", self.evEdit, 10,
				height, 150, guiWidgetHeight, self.guiMatBlendValue.val, 0.0, 1.0, 0, "")

			height += guiHeightOffset

		PanelHeight = height

	def event(self, evt = None):
		# print "mat evt", evt

		if self.guiShowActiveMat.val:
			try:
				currentSelection = Object.GetSelected()[0]
			except:
				currentSelection = None

			if currentSelection == None:
				return

			if currentSelection.getType() not in ['Mesh', 'Curve']:
				return

			num = currentSelection.activeMaterial
			mesh = currentSelection.getData()
			if len(mesh.materials) == 0:
				return
			m = mesh.materials[num - 1]
			self.setPropertyList(m)
			for el in self.connector:
				setParam(el[0],el[1],el[2],el[3])

		elif evt == None:
			self.setPropertyList()
			# set the parameters from the GUI to their respective ID properties
			for el in self.connector:
				setParam(el[0],el[1],el[2],el[3])

			#if self.curMat['type'] == "blend":
			#	mat = Blender.Material.Get()[self.guiMatMenu.val]
			#	self.matObject = BlendMat(mat)
		elif evt == self.evMatFromObj:
			try:
				mat = Blender.Object.GetSelected()[0].getData().materials[0]
				index = Blender.Material.Get().index(mat)
				self.guiMatMenu.val = index
				self.changeMat()
			except:
				print "No object selected"

	def changeMat(self):
		#print "change mat"
		self.setPropertyList()
		for el in self.connector:
			setGUIVals(el[0], el[1], el[2], el[3])

	def refreshPreview(self):
		if not self.guiMatShowPreview.val: return
		self.previewSize = int(self.guiMatPreviewSize.val)

		imageMem = yafrayinterface.new_floatArray(self.previewSize * self.previewSize * 4)
		self.yRender.createPreview(self.blenderMat, self.previewSize, imageMem)

		for x in range(self.previewSize):
			for y in range(self.previewSize):
				# first row is on the bottom, therefor the idx must be reversed
				idx = (x + (self.previewSize - 1) * self.previewSize - self.previewSize * y) * 4
				col = yafrayinterface.floatArray_getitem(imageMem, idx + 0)
				colR = min(255, int(col * 255))
				col = yafrayinterface.floatArray_getitem(imageMem, idx + 1)
				colG = min(255, int(col * 255))
				col = yafrayinterface.floatArray_getitem(imageMem, idx + 2)
				colB = min(255, int(col * 255))

				# still getting exceptions from time to time about
				# values out of range which should be impossible using
				# min above

				try:
					self.previewImage.setPixelI(x, y, (colR, colG, colB, 255))
				except:
					pass
					#print colR, colG, colB

		yafrayinterface.delete_floatArray(imageMem)



# ### tab environment ### #

class clTabWorld:
	def __init__(self):
		# events
		self.evShow = getUniqueValue()
		self.evEdit = getUniqueValue()
		self.evChangeSetName = getUniqueValue()

		self.tabNum = getUniqueValue()

		# Sanne: sunsky, also add "Sunsky" to self.BGTypes
		self.evGetSunAngle = getUniqueValue()
		self.evGetSunPos = getUniqueValue()
		self.evUpdateSun = getUniqueValue()
		self.evSunNormalToNumber = getUniqueValue()
		self.evSunNumberToNormal = getUniqueValue()

		# lists
		self.connector = []
		# class-specific types
		self.BGTypes = ["Single Color", "Gradient", "Texture", "Sunsky", "DarkTide's SunSky"]
		self.VolumeIntTypes = ["None", "Single Scatter"] 
		#self.VolumeIntTypes += ["Sky"]

		# properties
		self.World = {}

		self.scene = Scene.Get()[0]
		#self.scene = Scene.GetCurrent()
		if not self.scene.properties.has_key("YafRay"): self.scene.properties['YafRay']={}

		try:
			self.World = Blender.World.GetCurrent().properties['YafRay']
		except:
			Blender.World.New("World").setCurrent()
			Blender.World.GetCurrent().properties['YafRay'] = {}
			self.World = Blender.World.GetCurrent().properties['YafRay']

		# world bg stuff

		self.guiRenderBGType = Draw.Create(0) # menu
		self.guiRenderBGIBL = Draw.Create(0) # Toggle
		self.guiRenderBGIBLSamples = Draw.Create(1) # numberbox
		self.guiRenderBGIBLRot = Draw.Create(0.0) # Slider
		self.guiRenderBGPower = Draw.Create(1.0) # Slider
		self.guiRenderBGColor = Draw.Create(0.0,0.0,0.0) # color
		self.guiRenderBGHoriCol = Draw.Create(0.0,0.0,0.0) # color
		self.guiRenderBGZeniCol = Draw.Create(0.0,0.0,0.0) # color
		self.guiRenderBGHoriGCol = Draw.Create(0.0,0.0,0.0) # color
		self.guiRenderBGZeniGCol = Draw.Create(0.0,0.0,0.0) # color
		# Sanne: Sunsky
		self.guiRenderBGTurbidity = Draw.Create(1.0) # numberbox
		self.guiRenderBGAVar = Draw.Create(1.0) # numberbox
		self.guiRenderBGBVar = Draw.Create(1.0) # numberbox
		self.guiRenderBGCVar = Draw.Create(1.0) # numberbox
		self.guiRenderBGDVar = Draw.Create(1.0) # numberbox
		self.guiRenderBGEVar = Draw.Create(1.0) # numberbox
		self.guiRenderBGFrom = Draw.Create(0.0,0.0,0.0) # normal
		self.guiRenderBGFromX = Draw.Create(0.0) # numberbox
		self.guiRenderBGFromY = Draw.Create(0.0) # numberbox
		self.guiRenderBGFromZ = Draw.Create(0.0) # numberbox
		self.guiRenderBGCreateSun = Draw.Create(0) # toggle
		self.guiRenderBGSunPower = Draw.Create(0.0) # slider
		self.guiRenderBGSkyLight = Draw.Create(0) # toggle
		self.guiRenderBGSkySamples = Draw.Create(0) # numberbox

		# DarkTide's Sunsky
		self.guiRenderDSTurbidity = Draw.Create(2.0) # numberbox
		self.guiRenderDSRealSun = Draw.Create(0) # toggle
		self.guiRenderDSSunPower = Draw.Create(0.0) # slider
		self.guiRenderDSSkyBright = Draw.Create(1.0) # slider
		self.guiRenderDSSkyLight = Draw.Create(0) # toggle
		self.guiRenderDSSkySamples = Draw.Create(0) # numberbox
		self.guiRenderDSA = Draw.Create(1.0) # numberbox
		self.guiRenderDSB = Draw.Create(1.0) # numberbox
		self.guiRenderDSC = Draw.Create(1.0) # numberbox
		self.guiRenderDSD = Draw.Create(1.0) # numberbox
		self.guiRenderDSE = Draw.Create(1.0) # numberbox
		self.guiRenderDSAltitude = Draw.Create(0.0) # numberbox
		self.guiRenderDSNight = Draw.Create(0) # toggle

		# volume integrator
		self.guiRenderVolumeIntType = Draw.Create(0) # menu
		self.guiRenderVolumeStepSize = Draw.Create(0.0) # numberbox
		self.guiRenderVolumeAdaptive = Draw.Create(0) # toggle
		self.guiRenderVolumeOptimize = Draw.Create(0) # toggle
		self.guiRenderVolumeAttMapScale = Draw.Create(0) # numberbox
		self.guiRenderVolumeSkyST = Draw.Create(0.0) # numberbox
		self.guiRenderVolumeSkyAlpha = Draw.Create(0.0) # numberbox

		self.setPropertyList()



	# call once before and once after drawing and once in __init__
	def setPropertyList(self):

		# connect gui elements with id properties
		# <gui element>, <property name>, <default value or type list>, <property group>
		self.connector = [
			# background settings
			(self.guiRenderBGType, "bg_type", self.BGTypes, self.World),
			(self.guiRenderBGIBL, "ibl", 0, self.World),
			(self.guiRenderBGIBLSamples, "ibl_samples", 16, self.World),
			(self.guiRenderBGIBLRot, "rotation", 0.0, self.World),
			(self.guiRenderBGPower, "power", 1.0, self.World),
			(self.guiRenderBGColor, "color", (0.0, 0.0, 0.0), self.World),
			(self.guiRenderBGHoriCol, "horizon_color", (1.0, 1.0, 0.5), self.World),
			(self.guiRenderBGHoriGCol, "horizon_ground_color", (.65, .6, .45), self.World),
			(self.guiRenderBGZeniCol, "zenith_color", (.57, .65, 1.0), self.World),
			(self.guiRenderBGZeniGCol, "zenith_ground_color", (.28, .26, .2), self.World),
			# Sanne: Sunsky
			(self.guiRenderBGTurbidity, "turbidity", 3.0, self.World),
			(self.guiRenderBGAVar, "a_var", 1.0, self.World),
			(self.guiRenderBGBVar, "b_var", 1.0, self.World),
			(self.guiRenderBGCVar, "c_var", 1.0, self.World),
			(self.guiRenderBGDVar, "d_var", 1.0, self.World),
			(self.guiRenderBGEVar, "e_var", 1.0, self.World),
			(self.guiRenderBGFrom, "from", (1.0, 1.0, 1.0), self.World),
			(self.guiRenderBGCreateSun, "add_sun", 0, self.World),
			(self.guiRenderBGSunPower, "sun_power", 1.0, self.World),
			(self.guiRenderBGSkyLight, "background_light", 0, self.World),
			(self.guiRenderBGSkySamples, "light_samples", 8, self.World),
			# DarkTide's Sunsky
			(self.guiRenderDSTurbidity, "dsturbidity", 2.0, self.World),
			(self.guiRenderDSAltitude, "dsaltitude", 0.0, self.World),
			(self.guiRenderDSA, "dsa", 1.0, self.World),
			(self.guiRenderDSB, "dsb", 1.0, self.World),
			(self.guiRenderDSC, "dsc", 1.0, self.World),
			(self.guiRenderDSD, "dsd", 1.0, self.World),
			(self.guiRenderDSE, "dse", 1.0, self.World),
			(self.guiRenderDSRealSun, "dsadd_sun", 0, self.World),
			(self.guiRenderDSNight, "dsnight", 0, self.World),
			(self.guiRenderDSSunPower, "dssun_power", 1.0, self.World),
			(self.guiRenderDSSkyBright, "dsbright", 1.0, self.World),
			(self.guiRenderDSSkyLight, "dsbackground_light", 0, self.World),
			(self.guiRenderDSSkySamples, "dslight_samples", 8, self.World),
			# volume integrator
			(self.guiRenderVolumeIntType, "volType", self.VolumeIntTypes, self.World),
			(self.guiRenderVolumeStepSize, "stepSize", 1.0, self.World),
			(self.guiRenderVolumeAdaptive, "adaptive", 0, self.World),
			(self.guiRenderVolumeOptimize, "optimize", 0, self.World),
			(self.guiRenderVolumeAttMapScale, "attgridScale", 1, self.World),
			(self.guiRenderVolumeSkyST, "sigma_t", 0.1, self.World),
			(self.guiRenderVolumeSkyAlpha, "alpha", 0.5, self.World)]

		for el in self.connector:
			checkParam(el[0], el[1], el[2], el[3]) # adds missing params as property ID


	def drawBGSettings(self, height):
		# background settings
		height = drawSepLineText(10, height, 320, "Background settings")

		self.guiRenderBGType = Draw.Menu(makeMenu("Background ", self.BGTypes), self.evEdit,
			10, height, 150, guiWidgetHeight, self.guiRenderBGType.val, "Sets the background type")

		height += guiHeightOffset
		if self.World['bg_type'] == "Single Color":
			drawText(10, height + 4, "BG color:")
			self.guiRenderBGColor = Draw.ColorPicker(self.evEdit, 120,
				height, 210, guiWidgetHeight, self.guiRenderBGColor.val, "Background color")

			height += guiHeightOffset
			self.guiRenderBGIBL = Draw.Toggle("Use IBL", self.evEdit, 10, height, 150, guiWidgetHeight,
				self.guiRenderBGIBL.val, "Use the background color as the light source for your image.")
			self.guiRenderBGIBLSamples = Draw.Number("IBL Samples: ",
				self.evEdit, 180, height, 150, guiWidgetHeight, self.guiRenderBGIBLSamples.val, 1, 512, "Number of samples for direct lighting from background")

		elif self.World['bg_type'] == "Gradient":

			drawText(10, height + 4, "Horizon color:")
			self.guiRenderBGHoriCol = Draw.ColorPicker(self.evEdit, 120, height, 210, guiWidgetHeight,
				self.guiRenderBGHoriCol.val, "Horizon color")

			height += guiHeightOffset
			drawText(10, height + 4, "Zenith color:")
			self.guiRenderBGZeniCol = Draw.ColorPicker(self.evEdit, 120, height, 210, guiWidgetHeight,
				 self.guiRenderBGZeniCol.val, "Zenith color")

			height += guiHeightOffset
			drawText(10, height + 4, "Hor. ground color:")
			self.guiRenderBGHoriGCol = Draw.ColorPicker(self.evEdit, 120, height, 210, guiWidgetHeight,
				self.guiRenderBGHoriGCol.val, "Horizon ground color")

			height += guiHeightOffset
			drawText(10, height + 4, "Zen. ground color:")
			self.guiRenderBGZeniGCol = Draw.ColorPicker(self.evEdit, 120, height, 210, guiWidgetHeight,
				self.guiRenderBGZeniGCol.val, "Zenith ground color")

			height += guiHeightOffset
			self.guiRenderBGIBL = Draw.Toggle("Use IBL", self.evEdit, 10, height, 150, guiWidgetHeight,
				self.guiRenderBGIBL.val, "Use the background gradient as the light source for your image.")
			self.guiRenderBGIBLSamples = Draw.Number("IBL Samples: ",
				self.evEdit, 180, height, 150, guiWidgetHeight, self.guiRenderBGIBLSamples.val, 1, 512, "Number of samples for direct lighting from background")

		elif self.World['bg_type'] == "Texture":
			self.guiRenderBGIBL = Draw.Toggle("Use IBL", self.evEdit, 10, height, 150, guiWidgetHeight,
				self.guiRenderBGIBL.val, "Use the background image as the light source for your image, HDRIs highly recommended!")
			self.guiRenderBGIBLSamples = Draw.Number("IBL Samples: ",
				self.evEdit, 180, height, 150, guiWidgetHeight, self.guiRenderBGIBLSamples.val, 1, 512, "Number of samples for direct lighting from background")
			height += guiHeightOffset
			self.guiRenderBGIBLRot = Draw.Slider("Rotation: ", self.evEdit, 10,
				height, 150, guiWidgetHeight, self.guiRenderBGIBLRot.val, 0.0, 360.0, 0, "Rotation offset of background")

		# Sanne: Sunsky
		elif self.World['bg_type'] == "Sunsky":
			self.guiRenderBGTurbidity = Draw.Number("Turbidity: ", self.evEdit, 10,
				height, 150, guiWidgetHeight, self.guiRenderBGTurbidity.val, 1.0, 20.0, "Turbidity of the atmosphere")
			self.guiRenderBGAVar = Draw.Number("A (HorBrght): ", self.evEdit, 180,
				height, 150, guiWidgetHeight, self.guiRenderBGAVar.val, 0.0, 10.0, "Horizon brightness")

			height += guiHeightOffset
			self.guiRenderBGBVar = Draw.Number("B (HorSprd): ", self.evEdit, 10,
				height, 150, guiWidgetHeight, self.guiRenderBGBVar.val, 0.0, 10.0, "Spread of horizon edge transition")
			self.guiRenderBGCVar = Draw.Number("C (SunBrght): ", self.evEdit, 180,
				height, 150, guiWidgetHeight, self.guiRenderBGCVar.val, 0.0, 10.0, "Sun brightness")

			height += guiHeightOffset
			self.guiRenderBGDVar = Draw.Number("D (Sunsize): ", self.evEdit, 10,
				height, 150, guiWidgetHeight, self.guiRenderBGDVar.val, 0.0, 10.0, "Sun size")
			self.guiRenderBGEVar = Draw.Number("E (Backlight): ", self.evEdit, 180,
				height, 150, guiWidgetHeight, self.guiRenderBGEVar.val, 0.0, 10.0, "Backscattered light")

			# sun direction
			height += guiHeightOffset
			buttonmargin = -(guiWidgetHeight + guiHeightOffset)
			normbuttonwidth = 3 * guiWidgetHeight + 2 * buttonmargin
			normbuttonstartY = height - normbuttonwidth + guiWidgetHeight
			coordbuttonstart = 180 + normbuttonwidth + buttonmargin
			coordbuttonwidth = 150 - normbuttonwidth - buttonmargin

			self.guiRenderBGFromAngle = Draw.PushButton("From (get angle)", self.evGetSunAngle, 10,
				height, 150, guiWidgetHeight, "Get angle from selected sun lamp")
			self.guiRenderBGFrom = Draw.Normal(self.evSunNormalToNumber, 180,
				normbuttonstartY, normbuttonwidth, normbuttonwidth, self.guiRenderBGFrom.val, "Sun direction")
			self.guiRenderBGFromX = Draw.Number("x: ", self.evSunNumberToNormal, coordbuttonstart,
				height, coordbuttonwidth, guiWidgetHeight, self.guiRenderBGFrom.val[0], -1, 1, "Sun x direction")

			height += guiHeightOffset
			self.guiRenderBGFromPosition = Draw.PushButton("From (get position)", self.evGetSunPos, 10,
				height, 150, guiWidgetHeight, "Get position from selected sun lamp")
			self.guiRenderBGFromY = Draw.Number("y: ", self.evSunNumberToNormal, coordbuttonstart,
				height, coordbuttonwidth, guiWidgetHeight, self.guiRenderBGFrom.val[1], -1, 1, "Sun y direction")

			height += guiHeightOffset
			self.guiRenderBGFromUpdate = Draw.PushButton("From (update sun)", self.evUpdateSun, 10,
				height, 150, guiWidgetHeight, "Update position and angle of selected sun lamp according to GUI values")
			self.guiRenderBGFromZ = Draw.Number("z: ", self.evSunNumberToNormal, coordbuttonstart,
				height, coordbuttonwidth, guiWidgetHeight, self.guiRenderBGFrom.val[2], -1, 1, "Sun z direction")

			height += guiHeightOffset
			self.guiRenderBGCreateSun = Draw.Toggle("Add real sun", self.evEdit, 10, height, 150,
				guiWidgetHeight, self.guiRenderBGCreateSun.val, "")
			self.guiRenderBGSunPower = Draw.Slider("Power: ", self.evEdit, 180,
				height, 150, guiWidgetHeight, self.guiRenderBGSunPower.val, 0.0, 10.0, 0, "Sun power")

			height += guiHeightOffset
			self.guiRenderBGSkyLight = Draw.Toggle("Skylight", self.evEdit, 10, height, 150,
				guiWidgetHeight, self.guiRenderBGSkyLight.val, "")
			self.guiRenderBGSkySamples = Draw.Number("Samples: ", self.evEdit, 180,
				height, 150, guiWidgetHeight, self.guiRenderBGSkySamples.val, 1, 128, "")
			
		# DarkTide's Sunsky
		elif self.World['bg_type'] == "DarkTide's SunSky":
			self.guiRenderDSTurbidity = Draw.Number("Turbidity: ", self.evEdit, 10,
				height, 320, guiWidgetHeight, self.guiRenderDSTurbidity.val, 2.0, 12.0, "Turbidity of the athmosphere")
			height += guiHeightOffset
			self.guiRenderDSA = Draw.Number("Brightness of horizon gradient: ", self.evEdit, 10,
				height, 320, guiWidgetHeight, self.guiRenderDSA.val, -10.0, 10.0, "Darkening or brightening towards horizon")

			height += guiHeightOffset
			self.guiRenderDSB = Draw.Number("Luminance of horizon: ", self.evEdit, 10,
				height, 320, guiWidgetHeight, self.guiRenderDSB.val, -10.0, 10.0, "Luminance gradient near the horizon")

			height += guiHeightOffset
			self.guiRenderDSC = Draw.Number("Solar region intensity: ", self.evEdit, 10,
				height, 320, guiWidgetHeight, self.guiRenderDSC.val, 0.0, 50.0, "Relative intensity of circumsolar region")

			height += guiHeightOffset
			self.guiRenderDSD = Draw.Number("Width of circumsolar region: ", self.evEdit, 10,
				height, 320, guiWidgetHeight, self.guiRenderDSD.val, 0.0, 50.0, "Width of circumsolar region")

			height += guiHeightOffset
			self.guiRenderDSE = Draw.Number("Backscattered light: ", self.evEdit, 10,
				height, 320, guiWidgetHeight, self.guiRenderDSE.val, -30.0, 30.0, "Relative backscattered light")

			# sun direction
			height += guiHeightOffset
			buttonmargin = -(guiWidgetHeight + guiHeightOffset)
			normbuttonwidth = 3 * guiWidgetHeight + 2 * buttonmargin
			normbuttonstartY = height - normbuttonwidth + guiWidgetHeight
			coordbuttonstart = 180 + normbuttonwidth + buttonmargin
			coordbuttonwidth = 150 - normbuttonwidth - buttonmargin

			self.guiRenderBGFromAngle = Draw.PushButton("From (get angle)", self.evGetSunAngle, 10,
				height, 150, guiWidgetHeight, "Get angle from selected sun lamp")
			self.guiRenderBGFrom = Draw.Normal(self.evSunNormalToNumber, 180,
				normbuttonstartY, normbuttonwidth, normbuttonwidth, self.guiRenderBGFrom.val, "Sun direction")
			self.guiRenderBGFromX = Draw.Number("x: ", self.evSunNumberToNormal, coordbuttonstart,
				height, coordbuttonwidth, guiWidgetHeight, self.guiRenderBGFrom.val[0], -1, 1, "Sun x direction")

			height += guiHeightOffset
			self.guiRenderBGFromPosition = Draw.PushButton("From (get position)", self.evGetSunPos, 10,
				height, 150, guiWidgetHeight, "Get position from selected sun lamp")
			self.guiRenderBGFromY = Draw.Number("y: ", self.evSunNumberToNormal, coordbuttonstart,
				height, coordbuttonwidth, guiWidgetHeight, self.guiRenderBGFrom.val[1], -1, 1, "Sun y direction")

			height += guiHeightOffset
			self.guiRenderBGFromUpdate = Draw.PushButton("From (update sun)", self.evUpdateSun, 10,
				height, 150, guiWidgetHeight, "Update position and angle of selected sun lamp according to GUI values")
			self.guiRenderBGFromZ = Draw.Number("z: ", self.evSunNumberToNormal, coordbuttonstart,
				height, coordbuttonwidth, guiWidgetHeight, self.guiRenderBGFrom.val[2], -1, 1, "Sun z direction")

			height += guiHeightOffset
			self.guiRenderDSAltitude = Draw.Number("Altitude: ", self.evEdit, 10,
				height, 150, guiWidgetHeight, self.guiRenderDSAltitude.val, -1.0, 2.0, "Moves the sky dome above or below the camera position")
			self.guiRenderDSNight = Draw.Toggle("Night ", self.evEdit, 180,
				height, 150, guiWidgetHeight, self.guiRenderDSNight.val, "Activate experimental night mode")

			height += guiHeightOffset
			self.guiRenderDSRealSun = Draw.Toggle("Add real sun", self.evEdit, 10, height, 150,
				guiWidgetHeight, self.guiRenderDSRealSun.val, "Add a real sun light")
			self.guiRenderDSSunPower = Draw.Slider("Sun Power: ", self.evEdit, 180,
				height, 150, guiWidgetHeight, self.guiRenderDSSunPower.val, 0.0, 10.0, 0, "Sun power")

			height += guiHeightOffset
			self.guiRenderDSSkyLight = Draw.Toggle("Add Skylight", self.evEdit, 10, height, 150,
				guiWidgetHeight, self.guiRenderDSSkyLight.val, "")
			self.guiRenderDSSkySamples = Draw.Number("Samples: ", self.evEdit, 180,
				height, 150, guiWidgetHeight, self.guiRenderDSSkySamples.val, 1, 256, "SkyLight and Sunlight sample number")
        		height += guiHeightOffset
        		self.guiRenderDSSkyBright = Draw.Slider("Sky Brightnes: ", self.evEdit, 10,
                                height, 320, guiWidgetHeight, self.guiRenderDSSkyBright.val, 0.0, 10.0, 0, "Multiplier for Sky Brightness")

		height += guiHeightOffset
		self.guiRenderBGPower = Draw.Number("Power: ", self.evEdit, 10,
			height, 150, guiWidgetHeight, self.guiRenderBGPower.val, 0.0, 10000.0, "Multiplier for background color",
			dummyfunc, 10.0, 1.0)

		return height

	def drawVolumeSettings(self, height):
		# volume integrator
		height = drawSepLineText(10, height, 320, "Volume Integrator")
		self.guiRenderVolumeIntType = Draw.Menu(makeMenu("Volume Integrator ", self.VolumeIntTypes), self.evEdit,
			10, height, 150, guiWidgetHeight, self.guiRenderVolumeIntType.val, "Set the volume integrator")
		height += guiHeightOffset
		self.guiRenderVolumeStepSize = Draw.Number("Step size", self.evEdit,
			10, height, 150, guiWidgetHeight, self.guiRenderVolumeStepSize.val, 0, 100, "Exactness of volume calculation (in Blender units)")
		if self.World['volType'] == "Single Scatter":
			height += guiHeightOffset
			self.guiRenderVolumeAdaptive = Draw.Toggle("Adaptive", self.evEdit,
				10, height, 150, guiWidgetHeight, self.guiRenderVolumeAdaptive.val, "Exactness of volume calculation (in Blender units)")

			height += guiHeightOffset
			self.guiRenderVolumeOptimize = Draw.Toggle("Optimize", self.evEdit,
				10, height, 150, guiWidgetHeight, self.guiRenderVolumeOptimize.val, "Optimization, might lead to artifacts in some cases, increase grid resolution in that case")
			if self.guiRenderVolumeOptimize.val:
				height += guiHeightOffset
				self.guiRenderVolumeAttMapScale = Draw.Number("Att. grid resolution", self.evEdit,
					10, height, 150, guiWidgetHeight, self.guiRenderVolumeAttMapScale.val, 1, 50, "Optimization attenuation grid resolution")
		elif self.World['volType'] == "Sky":
			self.guiRenderVolumeSkyST = Draw.Number("scale", self.evEdit,
				180, height, 150, guiWidgetHeight, self.guiRenderVolumeSkyST.val, 0.0001, 10, "")
			height += guiHeightOffset
			self.guiRenderVolumeSkyAlpha = Draw.Number("alpha", self.evEdit,
				10, height, 150, guiWidgetHeight, self.guiRenderVolumeSkyAlpha.val, 0.001, 10, "")

		return height;


	def draw(self, height):
		global PanelHeight
		
		for el in self.connector:
			setGUIVals(el[0], el[1], el[2], el[3]) # adds missing params as property ID

		drawText(10, height, "World settings", "large")

		height = self.drawBGSettings(height)
		height = self.drawVolumeSettings(height)
		
		PanelHeight = height


	def event(self):
		#print "event for render tab"
		self.setPropertyList()

		for el in self.connector:
			setParam(el[0],el[1],el[2],el[3])

		Draw.Redraw(1)

	# Sanne: functions for sunsky
	def sunPosAngle(self, mode="get", val="position"):
		activeob = self.scene.objects.active
		warningmessage = True

		if activeob:
			if activeob.type == "Lamp":
				lamp = activeob.data
				if lamp.type == Lamp.Types["Sun"]:
					warningmessage = False

					if mode == "get":
						if val == "position":
							sunpos = Mathutils.Vector(activeob.loc)
							if sunpos.length:
								sunpos.normalize()
							self.guiRenderBGFromX.val = sunpos.x
							self.guiRenderBGFromY.val = sunpos.y
							self.guiRenderBGFromZ.val = sunpos.z
							self.guiRenderBGFrom.val = (sunpos.x, sunpos.y, sunpos.z)
							self.event()
						elif val == "angle":
							# analogue to sunflow exporter sun lamp export for sunsky
							invmatrix = Mathutils.Matrix(activeob.getInverseMatrix())
							self.guiRenderBGFromX.val = invmatrix[0][2]
							self.guiRenderBGFromY.val = invmatrix[1][2]
							self.guiRenderBGFromZ.val = invmatrix[2][2]
							self.guiRenderBGFrom.val = (invmatrix[0][2], invmatrix[1][2], invmatrix[2][2])
							self.event()

					elif mode == "update":
						# get gui from vector and normalize it
						vguifrom = Mathutils.Vector(self.guiRenderBGFrom.val)
						if vguifrom.length:
							vguifrom.normalize()

						# set location -----------------------------------
						sundist = Mathutils.Vector(activeob.loc).length
						activeob.setLocation(sundist * vguifrom)

						# compute and set rotation -----------------------
						# initialize rotation angle
						ang = 0.0

						# set reference vector for angle to -z
						vtrack = Mathutils.Vector(0, 0, -1)

						# compute sun ray direction from position
						vray = vguifrom.copy()
						if vguifrom.length:
							vray.negate().normalize()

						# get angle between sun ray and reference vector
						if vtrack.length and vray.length:
							ang = Mathutils.AngleBetweenVecs(vtrack, vray)
						else:
							print "Zero length input vector - sun angle set to 0\n"

						# get rotation axis
						axis = Mathutils.CrossVecs(vtrack, vray).normalize()

						# get quaternion representing rotation and get corresponding euler angles
						quat = Mathutils.Quaternion(axis, ang)
						eul = quat.toEuler().unique()

						# convert euler values to radians
						eulrad = []
						for i in eul:
							#eulrad.append((i * 3.14159265) / 180.0)   # if module math is not available
							eulrad.append(math.radians(i))

						# update sun rotation and redraw the 3D windows
						activeob.setEuler(eulrad)
						Window.Redraw()

		if warningmessage:
			Draw.PupMenu("No or wrong selection %t | Please select a sun lamp.")
			print "No or wrong selection\nPlease select a sun lamp."


	def sunNormalToNumber(self):
		self.guiRenderBGFromX.val = self.guiRenderBGFrom.val[0]
		self.guiRenderBGFromY.val = self.guiRenderBGFrom.val[1]
		self.guiRenderBGFromZ.val = self.guiRenderBGFrom.val[2]
		self.event()

	def sunNumberToNormal(self):
		self.guiRenderBGFrom.val = (self.guiRenderBGFromX.val, self.guiRenderBGFromY.val, self.guiRenderBGFromZ.val)
		self.event()

# ### end classTabWorld ### #





# ### tab render ### #

class clTabRender:
	def __init__(self):
		# events
		self.evShow = getUniqueValue()
		self.evEdit = getUniqueValue()
		self.evChangeRenderset = getUniqueValue()
		self.evChangeSetName = getUniqueValue()

		self.tabNum = getUniqueValue()

		# lists
		self.connector = []
		# class-specific types
		self.AATypes = ["box", "mitchell", "gauss"]
		self.LightingTypes = ["Direct lighting", "Photon mapping", "Pathtracing", "Bidirectional (EXPERIMENTAL)"]
		self.LightingTypes += ["Debug"]
		self.DebugTypes = ["N", "dPdU", "dPdV", "NU", "NV", "dSdU", "dSdV"]
		self.CausticTypes = ["None", "Path", "Photon", "Path+Photon"]
		self.RenderSets = ["Set 1", "Set 2", "Set 3", "Set 4", "Set 5"]
		self.TilesOrderTypes = ["Linear", "Random"]
		# properties
		self.Renderer = {}
		self.Settings = {}

		self.scene = Scene.Get()[0]
		#self.scene = Scene.GetCurrent()
		if not self.scene.properties.has_key("YafRay"): self.scene.properties['YafRay']={}

		# Initialize Global Settings if not present into blend file
		if not self.scene.properties['YafRay'].has_key("Settings"):
			self.scene.properties['YafRay']['Settings'] = {}

		if not self.scene.properties['YafRay'].has_key("Renderer"):
			self.scene.properties['YafRay']['Renderer'] = {}

		# Initialize Render sets
		for r in self.RenderSets:
			if not self.scene.properties['YafRay']['Renderer'].has_key(r):
				self.scene.properties['YafRay']['Renderer'][r] = {}
				self.Renderer = self.scene.properties['YafRay']['Renderer'][r]
			else:
				self.Renderer = self.scene.properties['YafRay']['Renderer'][r]


		# gui elements
		self.guiRenderSet = Draw.Create(0) # menu
		self.guiRenderSetName = Draw.Create("") # menu

		self.guiRenderAASamples = Draw.Create(1) # numberbox
		self.guiRenderAAIncSamples = Draw.Create(1) # numberbox
		self.guiRenderAAPasses = Draw.Create(1) # numberbox
		self.guiRenderAAThreshold = Draw.Create(0.0) # numberbox
		self.guiRenderThreads = Draw.Create(1) # numberbox
		self.guiRenderAutoThreads = Draw.Create(1) # toggle
		self.guiRenderGamma = Draw.Create(1.0) # slider
		self.guiRenderGammaInput = Draw.Create(1.0) # slider
		self.guiRenderAAPixelWidth = Draw.Create(1.5) # numberbox
		self.guiRenderFilterType = Draw.Create(0) # menu
		self.guiRenderTranspShadow = Draw.Create(0) # toggle
		self.guiRenderClampRGB = Draw.Create(0) # toggle
		self.guiRenderShowSampleMask = Draw.Create(0) # toggle
		self.guiRenderTileSize = Draw.Create(0) # umberbox
		self.guiRenderTileOrder = Draw.Create(1) # dropdown
		self.guiRenderClayRender = Draw.Create(0) # toggle
		self.guiRenderDrawParams = Draw.Create(0) # toggle
		self.guiRenderCustomString = Draw.Create("None") # string
		self.guiRenderXML = Draw.Create(0) # toggle
		self.guiRenderAutoSave = Draw.Create(0) # toggle
		self.guiRenderToBlender = Draw.Create(0) # toggle
		self.guiRenderAlpha = Draw.Create(0) # toggle

		self.guiRenderLightType = Draw.Create(0) # menu
		self.guiRenderCausticType = Draw.Create(0) # menu
		self.guiRenderRaydepth = Draw.Create(2) # numberbox
		self.guiRenderShadowDepth = Draw.Create(2) # numberbox

		self.guiRenderDirCaustics = Draw.Create(0) # toggle
		self.guiRenderDirPhotons = Draw.Create(0) # numberbox
		self.guiRenderDirCausticMix = Draw.Create(0) # numberbox
		self.guiRenderDirCausticDepth = Draw.Create(0) # numberbox
		self.guiRenderDirCausticRadius = Draw.Create(0.0) # numberbox
		self.guiRenderDirAO = Draw.Create(0) # Toggle
		self.guiRenderDirAOSamples = Draw.Create(0) # numberbox
		self.guiRenderDirAODist = Draw.Create(0.0) # numberbox
		self.guiRenderDirAOColor = Draw.Create(1.0, 1.0, 1.0) # color

		self.guiRenderUseBG = Draw.Create(0) # Toggle
		self.guiRenderGIQuality = Draw.Create(0) # menu
		self.guiRenderNoRecursive = Draw.Create(0) # Toggle
		self.guiRenderGIDepth = Draw.Create(2) # numberbox

		self.guiRenderPhPhotons = Draw.Create(0) # numberbox
		self.guiRenderPhCausPhotons = Draw.Create(0) # numberbox
		self.guiRenderPhDiffuseRad = Draw.Create(1.0) # numberbox
		self.guiRenderPhCausticRad = Draw.Create(0.1) # numberbox
		self.guiRenderPhSearch = Draw.Create(0) # numberbox
		self.guiRenderPhCaustixMix = Draw.Create(0) # numberbox
		self.guiRenderPhFG = Draw.Create(0) # toggle
		self.guiRenderPhFGSamples = Draw.Create(0) # numberbox
		self.guiRenderPhFGBounces = Draw.Create(0) # numberbox
		self.guiRenderPhShowMap = Draw.Create(0) # toggle

		self.guiRenderDebugType = Draw.Create(0) # menu
		self.guiRenderDebugMaps = Draw.Create(0) #toggle

		self.Settings = self.scene.properties['YafRay']['Settings']

		# Select scene renderset if present otherwise use default one
		if not self.scene.properties['YafRay']['Settings'].has_key("renderset"):
			self.Renderer = self.scene.properties['YafRay']['Renderer']['Set 1']
		else:
			self.Renderer = self.scene.properties['YafRay']['Renderer'][self.scene.properties['YafRay']['Settings']['renderset']]
		if not self.Renderer.has_key('setname'):
			self.Renderer['setname'] = "Set 1"

		self.setPropertyList()

		for r in self.RenderSets:
			if not self.scene.properties['YafRay']['Renderer'][r].has_key('setname'):
				self.scene.properties['YafRay']['Renderer'][r]['setname'] = r
			copyParams(self.Renderer, self.scene.properties['YafRay']['Renderer'][r])

		copyParamsOverwrite(self.Renderer, self.scene.properties['YafRay']['Renderer'])



	# call once before and once after drawing and once in __init__
	def setPropertyList(self):

		if not self.Renderer.has_key('setname'):
			self.Renderer['setname'] = ""
			self.guiRenderSetName.val = self.Renderer['setname']
		else:
			self.guiRenderSetName.val = self.Renderer['setname']


		# connect gui elements with id properties
		# <gui element>, <property name>, <default value or type list>, <property group>
		self.connector = [
			# Scene Settings
			(self.guiRenderSet, "renderset", self.RenderSets, self.Settings),
			# Integrator settings
			(self.guiRenderLightType, "lightType", self.LightingTypes, self.Renderer),
			(self.guiRenderCausticType, "caustic_type", self.CausticTypes, self.Renderer),
			(self.guiRenderDirCaustics, "caustics", 0, self.Renderer),
			(self.guiRenderDirCausticDepth, "caustic_depth", 10, self.Renderer),
			(self.guiRenderDirCausticRadius, "caustic_radius", 0.25, self.Renderer),
			(self.guiRenderDirAO, "do_AO", 0, self.Renderer),
			(self.guiRenderDirAOSamples, "AO_samples", 32, self.Renderer),
			(self.guiRenderDirAODist, "AO_distance", 1.0, self.Renderer),
			(self.guiRenderDirAOColor, "AO_color", (1.0, 1.0, 1.0), self.Renderer),
			(self.guiRenderGIQuality, "path_samples", 32, self.Renderer),
			(self.guiRenderNoRecursive, "no_recursive", 0, self.Renderer),
			(self.guiRenderGIDepth, "bounces", 5, self.Renderer),
			(self.guiRenderUseBG, "use_background", 0, self.Renderer),
			# General settings
			(self.guiRenderRaydepth, "raydepth", 2, self.Renderer),
			(self.guiRenderShadowDepth, "shadowDepth", 2, self.Renderer),
			(self.guiRenderThreads, "threads", 1, self.Renderer),
			(self.guiRenderAutoThreads, "auto_threads", True, self.Renderer),
			(self.guiRenderClayRender, "clayRender", 0, self.Renderer),
			(self.guiRenderDrawParams, "drawParams", 0, self.Renderer),
			(self.guiRenderXML, "xml", 0, self.Renderer),
			(self.guiRenderAutoSave, "autoSave", 0, self.Renderer),
			(self.guiRenderToBlender, "imageToBlender", 0, self.Renderer),
			(self.guiRenderAlpha, "autoalpha", 0, self.Renderer),
			(self.guiRenderGamma, "gamma", 1.8, self.Renderer),
			(self.guiRenderGammaInput, "gammaInput", 1.8, self.Renderer),
			(self.guiRenderCustomString, "customString", "", self.Renderer),
			(self.guiRenderTranspShadow, "transpShad", 0, self.Renderer),
			(self.guiRenderClampRGB, "clamp_rgb", 0, self.Renderer),
			(self.guiRenderShowSampleMask, "show_sam_pix", 0, self.Renderer),
			(self.guiRenderTileSize, "tile_size", 32, self.Renderer),
			(self.guiRenderTileOrder, "tiles_order", self.TilesOrderTypes, self.Renderer),
			# AA
			(self.guiRenderAASamples, "AA_minsamples", 1, self.Renderer),
			(self.guiRenderAAIncSamples, "AA_inc_samples", 1, self.Renderer),
			(self.guiRenderAAPasses, "AA_passes", 1, self.Renderer),
			(self.guiRenderAAThreshold, "AA_threshold", 0.05, self.Renderer),
			(self.guiRenderAAPixelWidth, "AA_pixelwidth", 1.5, self.Renderer),
			(self.guiRenderFilterType, "filter_type", self.AATypes, self.Renderer),
			# photon settings
			(self.guiRenderPhPhotons, "photons", 500000, self.Renderer),
			(self.guiRenderPhCausPhotons, "cPhotons", 500000, self.Renderer),
			(self.guiRenderPhDiffuseRad, "diffuseRadius", 1.0, self.Renderer),
			(self.guiRenderPhCausticRad, "causticRadius", 0.1, self.Renderer),
			(self.guiRenderPhSearch, "search", 100, self.Renderer),
			(self.guiRenderPhCaustixMix, "caustic_mix", 100, self.Renderer),
			(self.guiRenderPhFG, "finalGather", 1, self.Renderer),
			(self.guiRenderPhFGBounces, "fg_bounces", 3, self.Renderer),
			(self.guiRenderPhFGSamples, "fg_samples", 16, self.Renderer),
			(self.guiRenderPhShowMap, "show_map", 0, self.Renderer),
			# debug integrator
			(self.guiRenderDebugType, "debugType", self.DebugTypes, self.Renderer),
			(self.guiRenderDebugMaps, "show_perturbed_normals", 0, self.Renderer)]


		for el in self.connector:
			checkParam(el[0], el[1], el[2], el[3]) # adds missing params as property ID

		# after updating all values in the current render set, copy all
		# values also to the main render settings
		copyParamsOverwrite(self.Renderer, self.scene.properties['YafRay']['Renderer'])
		self.updateAllScenes()


	def updateAllScenes(self):
		# ugly ass hack, copy the render settings from the first scene
		# into all others, since the export only accesses the current
		# scene

		for s in Scene.Get():
			if not s == self.scene:
				#print "copying properties"
				if s.properties.has_key('YafRay'):
					del s.properties['YafRay']
				s.properties['YafRay'] = {}
				# seemingly the easiest way to copy a prop group with
				# all its subgroups
				s.properties['YafRay'] = self.scene.properties['YafRay'].convert_to_pyobject()


	def drawGeneralSettings(self, height):
		height = drawSepLineText(10, height, 320, "General settings")

		self.guiRenderRaydepth = Draw.Number("Raydepth: ", self.evEdit, 10,
			height, 150, guiWidgetHeight, self.guiRenderRaydepth.val, 0, 64, "Maximum depth for recursive raytracing")
		self.guiRenderShadowDepth = Draw.Number("Shadow depth: ", self.evEdit, 180,
			height, 150, guiWidgetHeight, self.guiRenderShadowDepth.val, 0, 64, "Max. depth for transparent shadows calculation (if enabled)")

		height += guiHeightOffset
		self.guiRenderGamma = Draw.Slider("Gamma: ", self.evEdit, 10,
			height, 150, guiWidgetHeight, self.guiRenderGamma.val, 0.0, 5.0, 0, "Gamma correction applied to final output, inverse correction of textures and colors is performed")
		self.guiRenderGammaInput = Draw.Slider("G. In: ", self.evEdit, 180,
			height, 150, guiWidgetHeight, self.guiRenderGammaInput.val, 0.0, 5.0, 0, "Gamma correction applied to input")

		height += guiHeightOffset
		self.guiRenderClampRGB = Draw.Toggle("Clamp RGB", self.evEdit, 10,
			height, 150, guiWidgetHeight, self.guiRenderClampRGB.val, "Reduce the colors' brightness to a low dynamic.")
		self.guiRenderTranspShadow = Draw.Toggle("Transparent Shadows", self.evEdit, 180,
			height, 150, guiWidgetHeight, self.guiRenderTranspShadow.val, "Pass light through transparent objects, allow semi-transparent shadows")
		
		height += guiHeightOffset
		self.guiRenderClayRender = Draw.Toggle("Clay render", self.evEdit, 10,
			height, 150, guiWidgetHeight, self.guiRenderClayRender.val, "Override all materials with a white diffuse material")
		self.guiRenderShowSampleMask = Draw.Toggle("Resample mask", self.evEdit, 180,
			height, 150, guiWidgetHeight, self.guiRenderShowSampleMask.val, "Masks pixels marked for resampling during adaptive passes")

		height += guiHeightOffset
		self.guiRenderToBlender = Draw.Toggle("Result to Blender", self.evEdit, 10,
			height, 150, guiWidgetHeight, self.guiRenderToBlender.val, "Save the rendering result into the Blender Image Viewer (slow)")
		self.guiRenderAutoSave = Draw.Toggle("Auto save", self.evEdit, 180,
			height, 150, guiWidgetHeight, self.guiRenderAutoSave.val, "Save each rendering result automatically (use with GUI)")

		height += guiHeightOffset
		self.guiRenderAlpha = Draw.Toggle("Alpha on autosave/anim.",
				self.evEdit, 10, height, 150, guiWidgetHeight, self.guiRenderAlpha.val, "Save alpha channel when rendering to autosave or doing animation")
		self.guiRenderTileSize = Draw.Number("Tile Size: ", self.evEdit, 180,
			height, 150, guiWidgetHeight, self.guiRenderTileSize.val, 0, 1024, "Size of ther render buckets (tiles)")

		height += guiHeightOffset
		self.guiRenderTileOrder = Draw.Menu(makeMenu("Tiles Order", self.TilesOrderTypes),
                                self.evEdit, 180, height, 150, guiWidgetHeight, self.guiRenderTileOrder.val, "")
		height += guiHeightOffset
		self.guiRenderAutoThreads = Draw.Toggle("Auto-threads", self.evEdit,
			10, height, 150, guiWidgetHeight, self.guiRenderAutoThreads.val, "Activate thread number auto detection")
		if self.guiRenderAutoThreads.val == 0:
			self.guiRenderThreads = Draw.Number("Threads: ", self.evEdit, 
				180, height, 150, guiWidgetHeight, self.guiRenderThreads.val, 0, 20, "Number of threads to use for rendering" )

		height += guiHeightOffset
		self.guiRenderDrawParams = Draw.Toggle("Draw render params", self.evEdit, 10,
			height, 150, guiWidgetHeight, self.guiRenderDrawParams.val, "Write the render parameters below the image")
		self.guiRenderXML = Draw.Toggle("Output to XML", self.evEdit, 180,
			height, 150, guiWidgetHeight, self.guiRenderXML.val, "Create XML output in the YFExport dir")

		if self.guiRenderDrawParams.val == 1:
			height += guiHeightOffset
			self.guiRenderCustomString = Draw.String("Custom string: ", self.evEdit, 10, height, 320,
				guiWidgetHeight, self.guiRenderCustomString.val, 50, "Custom string will be added to the info bar, use it for CPU, RAM etc.")

		return height;


	def drawAASettings(self, height):
		# AA settings
		height = drawSepLineText(10, height, 320, "AA settings")

		self.guiRenderAAPasses = Draw.Number("AA passes: ", self.evEdit, 10,
			height, 150, guiWidgetHeight, self.guiRenderAAPasses.val, 0, 100, "Number of anti-aliasing passes. Adaptive sampling (passes > 1) uses different pattern")
		self.guiRenderAAPixelWidth = Draw.Number("AA Pixelwidth: ", self.evEdit,
			180, height, 150, guiWidgetHeight, self.guiRenderAAPixelWidth.val, 0, 20, "AA filter size",
			dummyfunc, 10.0, 3.0)

		height += guiHeightOffset
		self.guiRenderAASamples = Draw.Number("AA samples: ", self.evEdit,
			10, height, 150, guiWidgetHeight, self.guiRenderAASamples.val, 1, 256, "Number of samples for first AA pass")
		self.guiRenderAAIncSamples = Draw.Number("AA inc. samples: ", self.evEdit,
			180, height, 150, guiWidgetHeight, self.guiRenderAAIncSamples.val, 1, 64, "Number of samples for additional AA passes")

		height += guiHeightOffset
		self.guiRenderFilterType = Draw.Menu(makeMenu("Filter type ", self.AATypes), self.evEdit,
			10, height, 150, guiWidgetHeight, self.guiRenderFilterType.val, "Filter type for anti-aliasing")
		self.guiRenderAAThreshold = Draw.Number("AA Threshold: ", self.evEdit,
			180, height, 150, guiWidgetHeight, self.guiRenderAAThreshold.val, 0, 1, "Color threshold for additional AA samples in next pass",
			dummyfunc, 0.1, 4.0)

		return height;

	def drawIntegratorSettings(self, height):
		height = drawSepLineText(10, height, 320, "Method of lighting")

		self.guiRenderLightType = Draw.Menu(makeMenu("Lighting method", self.LightingTypes),
			self.evEdit, 10, height, 320, guiWidgetHeight, self.guiRenderLightType.val, "Choose light integration method")


		if self.LightingTypes[self.guiRenderLightType.val] == "Direct lighting":
			height = drawSepLineText(10, height, 320, "Direct lighting settings")

			self.guiRenderDirCaustics = Draw.Toggle("Use Caustics", self.evEdit, 10, height, 150,
				guiWidgetHeight, self.guiRenderDirCaustics.val, "Enable photon map for caustics only")
			if self.guiRenderDirCaustics.val == 1: # do caustics
				height += guiHeightOffset
				self.guiRenderPhPhotons = Draw.Number("Photons: ", self.evEdit, 10,
					height, 150, guiWidgetHeight, self.guiRenderPhPhotons.val, 1, 100000000, "Number of photons to be shot",
					dummyfunc, 10000)
				self.guiRenderPhCaustixMix = Draw.Number("Caustic mix: ", self.evEdit, 180,
					height, 150, guiWidgetHeight, self.guiRenderPhCaustixMix.val, 1, 10000, "Max. number of photons to mix (blur)")

				height += guiHeightOffset
				self.guiRenderDirCausticDepth = Draw.Number("Caustic depth: ", self.evEdit, 10, height,
					150, guiWidgetHeight, self.guiRenderDirCausticDepth.val, 0, 50, "Max. number of scatter events for photons")
				self.guiRenderDirCausticRadius = Draw.Number("Caustic radius: ", self.evEdit, 180, height,
					150, guiWidgetHeight, self.guiRenderDirCausticRadius.val, 0.0, 100.0, "Max. radius to search for photons",
					dummyfunc, 10.0, 2.0)

			height += guiHeightOffset
			self.guiRenderDirAO = Draw.Toggle("Use AO", self.evEdit, 10, height, 150,
				guiWidgetHeight, self.guiRenderDirAO.val, "Enable ambient occlusion")
			if self.guiRenderDirAO.val == 1: # do Ambient occlusion
				height += guiHeightOffset
				self.guiRenderDirAOSamples = Draw.Number("AO samples", self.evEdit, 10, height,
					150, guiWidgetHeight, self.guiRenderDirAOSamples.val, 1, 1000, "Number of samples for ambient occlusion")
				self.guiRenderDirAODist = Draw.Number("AO distance", self.evEdit, 180, height,
					150, guiWidgetHeight, self.guiRenderDirAODist.val, 0.0, 10000.0, "Max. occlusion distance. Surfaces further away do not occlude ambient light",
					dummyfunc, 10.0, 1.0)

				height += guiHeightOffset
				drawText(10, height + 4, "AO color:")
				self.guiRenderDirAOColor = Draw.ColorPicker(self.evEdit, 120, height, 210, guiWidgetHeight,
					self.guiRenderDirAOColor.val, "AO color")


		elif self.LightingTypes[self.guiRenderLightType.val] == "Pathtracing":
			height = drawSepLineText(10, height, 320, "Pathtracer settings")
			self.guiRenderCausticType = Draw.Menu(makeMenu("Caustic method", self.CausticTypes),
				self.evEdit, 10, height, 150, guiWidgetHeight, self.guiRenderCausticType.val, "Choose caustic rendering method")

			if self.guiRenderCausticType.val == 2 or self.guiRenderCausticType.val == 3: # do photon caustics
				height += guiHeightOffset
				self.guiRenderPhPhotons = Draw.Number("Photons", self.evEdit, 10,
					height, 150, guiWidgetHeight, self.guiRenderPhPhotons.val, 1, 100000000, "Number of photons to be shot")
				self.guiRenderPhCaustixMix = Draw.Number("Caustic mix", self.evEdit, 180,
					height, 150, guiWidgetHeight, self.guiRenderPhCaustixMix.val, 1, 10000, "Max. number of photons to mix (blur)")

				height += guiHeightOffset
				self.guiRenderDirCausticDepth = Draw.Number("Caustic depth", self.evEdit, 10, height,
					150, guiWidgetHeight, self.guiRenderDirCausticDepth.val, 0, 50, "Max. number of scatter events for photons")
				self.guiRenderDirCausticRadius = Draw.Number("Caustic radius", self.evEdit, 180, height,
					150, guiWidgetHeight, self.guiRenderDirCausticRadius.val, 0.0, 100.0, "Max. radius to search for photons",
					dummyfunc, 10.0, 2.0)

			height += guiHeightOffset
			self.guiRenderGIDepth = Draw.Number("Depth", self.evEdit, 10, height,
				150, guiWidgetHeight, self.guiRenderGIDepth.val, 0, 50, "Number of light bounces(path length)")
			#self.guiRenderUseBG = Draw.Toggle("Use background", self.evEdit, 180, height, 150,
			#	guiWidgetHeight, self.guiRenderUseBG.val, "Include background when calculating indirect light")

			height += guiHeightOffset
			self.guiRenderGIQuality = Draw.Number("Path samples", self.evEdit, 10, height, 150,
				guiWidgetHeight, self.guiRenderGIQuality.val, 0, 5000, "Number of path samples per pixel sample" )
			self.guiRenderNoRecursive = Draw.Toggle("No Recursion", self.evEdit, 180, height, 150,
				guiWidgetHeight, self.guiRenderNoRecursive.val, "No recursive raytracing, only pure path tracing" )

		elif self.LightingTypes[self.guiRenderLightType.val] == "Photon mapping":
			height = drawSepLineText(10, height, 320, "Photon settings")

			self.guiRenderGIDepth = Draw.Number("Depth", self.evEdit, 10, height,
				150, guiWidgetHeight, self.guiRenderGIDepth.val, 0, 50, "Maximum number of scattering events for photons")
			#self.guiRenderUseBG = Draw.Toggle("Use background", self.evEdit, 180, height, 150,
			#	guiWidgetHeight, self.guiRenderUseBG.val, "Include background when calculating indirect light")

			height += guiHeightOffset 
			self.guiRenderPhPhotons = Draw.Number("Diff. Photons", self.evEdit, 10,
				height, 150, guiWidgetHeight, self.guiRenderPhPhotons.val, 1, 100000000, "Number of diffuse photons to be shot")
			self.guiRenderPhCausPhotons = Draw.Number("Caus. Photons", self.evEdit, 180,
				height, 150, guiWidgetHeight, self.guiRenderPhCausPhotons.val, 1, 100000000, "Number of caustic photons to be shot")
				
			height += guiHeightOffset
			self.guiRenderPhDiffuseRad = Draw.Number("Diff. radius", self.evEdit, 10,
				height, 150, guiWidgetHeight, self.guiRenderPhDiffuseRad.val, 0.01, 100.0, "Radius to search for diffuse photons",
				dummyfunc, 10.0, 3.0)
			self.guiRenderPhCausticRad = Draw.Number("Caus. radius", self.evEdit, 180,
				height, 150, guiWidgetHeight, self.guiRenderPhCausticRad.val, 0.001, 100.0, "Radius to search for caustic photons",
				dummyfunc, 10.0, 3.0)

			height += guiHeightOffset
			self.guiRenderPhSearch = Draw.Number("Search", self.evEdit, 10,
				height, 150, guiWidgetHeight, self.guiRenderPhSearch.val, 1, 10000, "Maximum number of diffuse photons to be filtered")
			self.guiRenderPhCaustixMix = Draw.Number("Caustic Mix", self.evEdit, 180,
				height, 150, guiWidgetHeight, self.guiRenderPhCaustixMix.val, 1, 10000, "Max. number of photons to mix (caustics blur)")

			height += guiHeightOffset
			self.guiRenderPhFG = Draw.Toggle("Final gather", self.evEdit, 10,
				height, 150, guiWidgetHeight, self.guiRenderPhFG.val, "Use final gathering (recommended)")
			self.guiRenderPhFGBounces = Draw.Number("FG bounces", self.evEdit, 180,
				height, 150, guiWidgetHeight, self.guiRenderPhFGBounces.val, 1, 20, "Allow gather rays to extend to paths of this length")

			height += guiHeightOffset
			self.guiRenderPhFGSamples = Draw.Number("FG samples", self.evEdit, 10,
				height, 150, guiWidgetHeight, self.guiRenderPhFGSamples.val, 1, 4096, "Number of samples for final gathering")
			self.guiRenderPhShowMap = Draw.Toggle("Show map", self.evEdit, 180,
				height, 150, guiWidgetHeight, self.guiRenderPhShowMap.val, "Directly show radiance map (disables final gathering step)")

		elif self.LightingTypes[self.guiRenderLightType.val] == "Debug":

			height = drawSepLineText(10, height, 320, "Debug settings")

			self.guiRenderDebugType = Draw.Menu(makeMenu("Debug types", self.DebugTypes),
				self.evEdit, 10, height, 150, guiWidgetHeight, self.guiRenderDebugType.val, "")
			self.guiRenderDebugMaps = Draw.Toggle("Perturbed Normals", self.evEdit, 180,
				height, 150, guiWidgetHeight, self.guiRenderDebugMaps.val, "Show the normals perturbed by bump and normal maps")


		return height;


	def draw(self, height):
		global PanelHeight

		for el in self.connector:
			setGUIVals(el[0], el[1], el[2], el[3]) # adds missing params as property ID

		drawText(10, height, "Render settings", "large")

		height = drawSepLineText(10, height, 320, "Render set")

		i = 0
		renderSetMenu = "Render set %t|"
		for s in self.RenderSets:
			renderSetMenu += self.scene.properties['YafRay']['Renderer'][s]['setname'] + " %x" + str(i) + "|"
			i = i + 1

		self.guiRenderSet = Draw.Menu(renderSetMenu,
			self.evChangeRenderset, 10, height, 150, guiWidgetHeight, self.guiRenderSet.val, "Selects a render set")
		self.guiRenderSetName = Draw.String("Name: ", self.evChangeSetName, 180, height, 150,
			guiWidgetHeight, self.guiRenderSetName.val, 10, "Name of the current render set")

		height = self.drawIntegratorSettings(height)

		height = self.drawGeneralSettings(height)

		height = self.drawAASettings(height)

		PanelHeight = height




	def event(self):
		self.setPropertyList()

		for el in self.connector:
			setParam(el[0],el[1],el[2],el[3])

		copyParamsOverwrite(self.Renderer, self.scene.properties['YafRay']['Renderer'])
		Draw.Redraw(1)
		# self.updateAllScenes()


	def changeSet(self):
		# Save current RenderSet in scene settings
		self.setPropertyList()
		for el in self.connector:
			setParam(el[0],el[1],el[2],el[3])
		# Switch Render settings to selected set
		self.Renderer = self.scene.properties['YafRay']['Renderer'][self.RenderSets[self.guiRenderSet.val]]
		copyParamsOverwrite(self.Renderer, self.scene.properties['YafRay']['Renderer'])
		self.setPropertyList()
		Draw.Redraw(1)
		# self.updateAllScenes()

	def changeSetName(self):
		self.Renderer['setname'] = self.guiRenderSetName.val
		self.scene.properties['YafRay']['Renderer']['setname'] = self.guiRenderSetName.val
		Draw.Redraw(1)
		self.updateAllScenes()


# ### end classTabRender ### #




# ### tab object ### #

class clTabObject:
	def __init__(self):
		# events
		self.evShow = getUniqueValue()
		self.evObjEdit = getUniqueValue()
		self.evDOFObj = getUniqueValue()
		self.evGetIESFile = getUniqueValue()
		self.evToggleMeshlight = getUniqueValue()
		self.evToggleVolume = getUniqueValue()

		self.tabNum = getUniqueValue()

		# lists
		self.connector = []

		# class-specific types
		self.cameraTypes = ["perspective", "orthographic", "angular", "architect"]
		self.bokehTypes = ["disk1", "disk2", "triangle", "square", "pentagon", "hexagon", "ring"]
		self.bokehBiasTypes = ["uniform", "edge", "center"]
		self.LightTypes = ["Point", "Sphere", "Spot", "IES Light", "Sun", "Directional", "Area"]
		self.VolumeRegionTypes = ["ExpDensityVolume", "UniformVolume", "NoiseVolume"]
		# self.VolumeRegionTypes += ["GridVolume", "SkyVolume"]


		# gui elements

		# light settings
		self.guiLightType = Draw.Create(0) # menu
		self.guiLightSamples = Draw.Create(1) # slider
		self.guiLightRadius = Draw.Create(1.0) # slider
		self.guiLightAngle = Draw.Create(0.0) # slider
		self.guiLightPower = Draw.Create(1.0) # numberbox
		self.guiLightColor = Draw.Create(1.0,1.0,1.0) # color picker
		self.guiLightCreateGeom = Draw.Create(0) # toggle
		self.guiLightInfinite = Draw.Create(0) # toggle
		self.guiLightIESFile = Draw.Create("") # text
		self.guiLightIESSamples = Draw.Create(8) # numberbox
		self.guiLightIESSoftShadows = Draw.Create(0) # toggle
		self.guiLightSpotSoftShadows = Draw.Create(0) # toggle
		self.guiLightSpotShadowFuzzyness = Draw.Create(1.0) # numberbox
		self.guiLightSpotSamples = Draw.Create(8) # numberbox
		self.guiLightSpotPhotonOnly = Draw.Create(0) # toggle

		# camera settings
		self.guiCamType = Draw.Create(1) # menu
		self.guiCamDOFDist = Draw.Create(0.0) # numberbox
		self.guiCamDistObj = Draw.Create("") # string
		self.guiCamDOFAperture = Draw.Create(0.0) # numberbox
		self.guiCamBokehType = Draw.Create(0) # menu
		self.guiCamBokehRotation = Draw.Create(0.0) # slider
		self.guiCamBokehBias = Draw.Create(0) # menu
		self.guiCamScale = Draw.Create(1.0) # slider
		self.guiCamMirrored = Draw.Create(0) # toggle
		self.guiCamCircular = Draw.Create(0) # toggle
		self.guiCamAngle = Draw.Create(90.0) # slider
		self.guiCamMaxAngle = Draw.Create(90.0) # slider
		self.guiCamObjectFocus = Draw.Create(0) # toggle

		# mesh settings
		self.guiMeshLightEnable = Draw.Create(0) # toggle
		self.guiMeshLightColor = Draw.Create(1.0,1.0,1.0) # color picker
		self.guiMeshLightDoubleSided = Draw.Create(0) # toggle
		self.guiMeshLightPower = Draw.Create(0.0) # numberbox
		self.guiMeshLightSamples = Draw.Create(0) # slider

		# mesh as volume
		self.guiMeshVolumeEnable = Draw.Create(0) # toggle
		self.guiMeshVolumeRegionType = Draw.Create(0) # menu
		self.guiMeshVIss = Draw.Create(0.0) # numberbox
		self.guiMeshVIsa = Draw.Create(0.0) # numberbox
		self.guiMeshVIg = Draw.Create(0.0) # numberbox
		self.guiMeshVIle = Draw.Create(0.0) # numberbox
		self.guiMeshVIDensity = Draw.Create(0.0) # numberbox
		self.guiMeshVIexpa = Draw.Create(0.0) # numberbox
		self.guiMeshVIexpb = Draw.Create(0.0) # numberbox
		self.guiMeshVINoiseCover = Draw.Create(0.0) # numberbox
		self.guiMeshVINoiseSharpness = Draw.Create(0.0) # numberbox

		self.setPropertyList()


	# call once before and once after drawing and once in __init__
	def setPropertyList(self, obj = None):

		if obj == None:
			try:
				obj = Object.GetSelected()[0]
			except:
				return

		if not obj.properties.has_key("YafRay"): obj.properties['YafRay']={}

		obType = obj.getType();
		self.isCamera = False
		self.isLight = False

		# connect gui elements with id properties
		# <gui element>, <property name>, <default value or type list>, <property group>

		if obType == 'Camera':
			self.isCamera = True
			self.cam = obj.data
			self.connector = [(self.guiCamType, "type", self.cameraTypes, obj.properties['YafRay']),
				(self.guiCamObjectFocus, "dof_object_focus", 0.0, obj.properties['YafRay']),
				(self.guiCamDOFDist, "dof_distance", 0.0, obj.properties['YafRay']),
				(self.guiCamDistObj, "dof_object", "", obj.properties['YafRay']),
				(self.guiCamDOFAperture, "aperture", 0.0, obj.properties['YafRay']),
				(self.guiCamBokehType, "bokeh_type", self.bokehTypes, obj.properties['YafRay']),
				(self.guiCamBokehRotation, "bokeh_rotation", 0.0, obj.properties['YafRay']),
				(self.guiCamBokehBias, "bokeh_bias", self.bokehBiasTypes, obj.properties['YafRay']),
				(self.guiCamScale, "scale", 1.0, obj.properties['YafRay']),
				(self.guiCamCircular, "circular", 1, obj.properties['YafRay']),
				(self.guiCamMirrored, "mirrored", 0, obj.properties['YafRay']),
				(self.guiCamAngle, "angle", 90, obj.properties['YafRay']),
				(self.guiCamMaxAngle, "max_angle", 90, obj.properties['YafRay'])]
		elif obType == 'Lamp':
			self.isLight = True
			self.light = obj.data
			self.connector = [(self.guiLightType, "type", self.LightTypes, obj.properties['YafRay']),
				(self.guiLightSamples, "samples", 8, obj.properties['YafRay']),
				(self.guiLightRadius, "radius", 1.0, obj.properties['YafRay']),
				(self.guiLightAngle, "angle", 0.5, obj.properties['YafRay']),
				(self.guiLightPower, "power", 1.0, obj.properties['YafRay']),
				(self.guiLightColor, "color", (1.0, 1.0, 1.0), obj.properties['YafRay']),
				(self.guiLightCreateGeom, "createGeometry", False, obj.properties['YafRay']),
				(self.guiLightInfinite, "infinite", True, obj.properties['YafRay']),
				(self.guiLightIESFile, "iesfile", "", obj.properties['YafRay']),
				(self.guiLightIESSamples, "iesSamples",16, obj.properties['YafRay']),
				(self.guiLightIESSoftShadows, "iesSoftShadows", False, obj.properties['YafRay']),
				(self.guiLightSpotSoftShadows, "SpotSoftShadows", False, obj.properties['YafRay']),
				(self.guiLightSpotShadowFuzzyness, "SpotShadowFuzzyness", 1.0, obj.properties['YafRay']),
				(self.guiLightSpotSamples, "SpotSamples",16, obj.properties['YafRay']),
				(self.guiLightSpotPhotonOnly, "SpotPhotonOnly", False, obj.properties['YafRay'])]
		else:
			self.connector = [(self.guiMeshLightEnable, "meshlight", False, obj.properties['YafRay']),
				(self.guiMeshLightColor, "color", (1.0, 1.0, 1.0), obj.properties['YafRay']),
				(self.guiMeshLightDoubleSided, "double_sided", False, obj.properties['YafRay']),
				(self.guiMeshLightPower, "power", 1.0, obj.properties['YafRay']),
				(self.guiMeshLightSamples, "samples", 16, obj.properties['YafRay']),
				(self.guiMeshVolumeEnable, "volume", False, obj.properties['YafRay']),
				(self.guiMeshVolumeRegionType, "volregionType", self.VolumeRegionTypes, obj.properties['YafRay']),
				(self.guiMeshVIss, "sigma_s", .1, obj.properties['YafRay']),
				(self.guiMeshVIsa, "sigma_a", .1, obj.properties['YafRay']),
				(self.guiMeshVIDensity, "density", 1.0, obj.properties['YafRay']),
				(self.guiMeshVIg, "g", 0, obj.properties['YafRay']),
				(self.guiMeshVIle, "l_e", .0, obj.properties['YafRay']),
				(self.guiMeshVIexpa, "a", 1.0, obj.properties['YafRay']),
				(self.guiMeshVIexpb, "b", 1.0, obj.properties['YafRay']),
				(self.guiMeshVINoiseSharpness, "sharpness", 1.0, obj.properties['YafRay']),
				(self.guiMeshVINoiseCover, "cover", 1.0, obj.properties['YafRay'])]

		for el in self.connector:
			checkParam(el[0], el[1], el[2], el[3]) # adds missing params as property ID

	def setIesFilePath(self, path):
		self.guiLightIESFile.val = path
		self.event()

	def getIesFile(self):
		Blender.Window.FileSelector (self.setIesFilePath, 'Select IES file')
	
	def dofObj(self):
		# check if the object exists or unset it
		if self.guiCamDistObj.val not in [obj.name for obj in Blender.Scene.GetCurrent().objects]:
			self.guiCamDistObj.val = ""
		self.event()
		
	def toggleMeshOption(self, option):
		if option == 0 and self.guiMeshLightEnable.val == 1:
			self.guiMeshVolumeEnable.val = 0
		elif option == 1 and self.guiMeshVolumeEnable == 1:
			self.guiMeshLightEnable.val = 0
		self.event()

	def draw(self, height):
		global PanelHeight
		
		try:
			obj = Object.GetSelected()[0]
		except:
			drawText(10, height, "Nothing selected", "large")
			return

		self.setPropertyList()
		for el in self.connector:
			setGUIVals(el[0], el[1], el[2], el[3])

		if self.isCamera: # settings for camera objects
			drawText(10, height, "Camera settings", "large")

			height += guiHeightOffset
			drawText(10, height, "Camera: " + obj.name)

			height = drawSepLineText(10, height, 320, "Camera type")

			self.guiCamType = Draw.Menu(makeMenu("Camera type", self.cameraTypes),
				self.evObjEdit, 10, height, 150, guiWidgetHeight, self.guiCamType.val, "Camera type")

			if self.guiCamType.val == 0: # perspective camera

				height = drawSepLineText(10, height, 320, "Depth of field")

				self.guiCamBokehType = Draw.Menu(makeMenu("Bokeh type", self.bokehTypes), self.evObjEdit, 10, height, 150, guiWidgetHeight, self.guiCamBokehType.val, "Selects a shape for the blur disk")
				self.guiCamBokehRotation = Draw.Slider("Rot: ",
					self.evObjEdit, 180, height, 150, guiWidgetHeight, self.guiCamBokehRotation.val, 0, 180, 0, "Sets rotation for the blur disk")

				height += guiHeightOffset
				self.guiCamDOFAperture = Draw.Number("Aperture Size: ",
					self.evObjEdit, 10, height, 150, guiWidgetHeight, self.guiCamDOFAperture.val, 0, 20, "Lens aperture size, the larger the more blur (0 disables DOF)",
					dummyfunc, 10.0, 3.0)
				self.guiCamBokehBias = Draw.Menu(makeMenu("Bokeh bias", self.bokehBiasTypes),
					self.evObjEdit, 180, height, 150, guiWidgetHeight, self.guiCamBokehBias.val, "Sets a bokeh bias")

				height += guiHeightOffset
				self.guiCamObjectFocus = Draw.Toggle("Object Focus", self.evObjEdit, 10, height, 150, guiWidgetHeight, self.guiCamObjectFocus.val,
					"Automatically set DOF Distance to be the position of an object in the scene")
					
				if self.guiCamObjectFocus.val == 1:
					self.guiCamDistObj = Draw.String("Dof Ob: ", self.evDOFObj, 180, height, 150, guiWidgetHeight,
						self.guiCamDistObj.val, 50, "Enter the name of the object that should be in focus.")
				else:
					self.guiCamDOFDist = Draw.Number("Dof Dist: ",
						self.evObjEdit, 180, height, 150, guiWidgetHeight, self.guiCamDOFDist.val, 0.0, 1000.0,
						"Object to focus on", dummyfunc, 10.0, 1.0)
					
			elif self.guiCamType.val == 1: # orthographic camera
				height = drawSepLineText(10, height, 320, "Orthographic settings")
				self.guiCamScale = Draw.Number("Scale: ",
					self.evObjEdit, 10, height, 150, guiWidgetHeight, self.guiCamScale.val, 0, 10000, "specify the ortho scaling")

			elif self.guiCamType.val == 2: # angular camera
				height = drawSepLineText(10, height, 320, "Angular settings")

				self.guiCamMirrored = Draw.Toggle("Mirrored",
					self.evObjEdit, 10, height, 150, guiWidgetHeight, self.guiCamMirrored.val, "Mirror x-direction (light probe images)")
				self.guiCamCircular = Draw.Toggle("Circular",
					self.evObjEdit, 180, height, 150, guiWidgetHeight, self.guiCamCircular.val, "Blend out areas outside max_angle (circular iris)")

				height += guiHeightOffset
				self.guiCamAngle = Draw.Slider("Angle: ",
					self.evObjEdit, 10, height, 150, guiWidgetHeight, self.guiCamAngle.val, 0, 180, 0, "Horizontal opening angle of the camera")
				self.guiCamMaxAngle = Draw.Slider("Max. Angle: ",
					self.evObjEdit, 180, height, 150, guiWidgetHeight, self.guiCamMaxAngle.val, 0, 180, 0, "Horizontal opening angle of the camera")

			elif self.guiCamType.val == 3: # architect
				height = drawSepLineText(10, height, 320, "Depth of field")

				self.guiCamBokehType = Draw.Menu(makeMenu("Bokeh type", self.bokehTypes), self.evObjEdit, 10, height, 150, guiWidgetHeight, self.guiCamBokehType.val, "Selects a shape for the blur disk")
				self.guiCamBokehRotation = Draw.Slider("Bokeh Rotation: ",
					self.evObjEdit, 180, height, 150, guiWidgetHeight, self.guiCamBokehRotation.val, 0, 180, 0, "Sets rotation for the blur disk")

				height += guiHeightOffset
				self.guiCamDOFAperture = Draw.Number("Aperture Size: ",
					self.evObjEdit, 10, height, 150, guiWidgetHeight, self.guiCamDOFAperture.val, 0, 20, "Lens aperture size, the larger the more blur (0 disables DOF)")
				self.guiCamBokehBias = Draw.Menu(makeMenu("Bokeh bias", self.bokehBiasTypes),
					self.evObjEdit, 180, height, 150, guiWidgetHeight, self.guiCamBokehBias.val, "Sets a bokeh bias")

				height += guiHeightOffset
				self.guiCamObjectFocus = Draw.Toggle("Object Focus", self.evObjEdit, 10, height, 150, guiWidgetHeight, self.guiCamObjectFocus.val,
					"Automatically set DOF Distance to be the position of an object in the scene")
					
				if self.guiCamObjectFocus.val == 1:
					self.guiCamDistObj = Draw.String("Dof Ob: ", self.evDOFObj, 180, height, 150, guiWidgetHeight,
						self.guiCamDistObj.val, 50, "Enter the name of the object that should be in focus.")
				else:
					self.guiCamDOFDist = Draw.Number("DOF Distance: ",
						self.evObjEdit, 180, height, 150, guiWidgetHeight, self.guiCamDOFDist.val, 0.0, 1000.0)
				
		elif self.isLight: # settings for light objects
			drawText(10, height, "Light settings", "large")

			height += guiHeightOffset
			height = drawTextLine(10, height, "Light: " + obj.name)

			#The lamp types. (from python docs)
			# 'Lamp': 0
			# 'Sun' : 1
			# 'Spot': 2
			# 'Hemi': 3
			# 'Area': 4
			# 'Photon': 5

			lightTypeMenu = "Light type %t|"

			if (self.light.type == 0):
				lightTypeMenu += "Point %x" + str(self.LightTypes.index("Point")) + "|"
				lightTypeMenu += "Sphere %x" + str(self.LightTypes.index("Sphere")) + "|"
			elif (self.light.type == 1):
				lightTypeMenu += "Sun %x" + str(self.LightTypes.index("Sun")) + "|"
				lightTypeMenu += "Directional %x" + str(self.LightTypes.index("Directional")) + "|"
			elif (self.light.type == 2):
				lightTypeMenu += "Spot %x" + str(self.LightTypes.index("Spot")) + "|"
				lightTypeMenu += "IES Light %x" + str(self.LightTypes.index("IES Light")) + "|"
			elif (self.light.type == 4):
				lightTypeMenu += "Area %x" + str(self.LightTypes.index("Area")) + "|"


			height += guiHeightOffset
			self.guiLightType = Draw.Menu(lightTypeMenu, self.evObjEdit,
				10, height, 150, guiWidgetHeight, self.guiLightType.val, "Assign light type to the selected light")

			height += guiHeightOffset
			drawText(10, height + 4, "Light color:")
			self.guiLightColor = Draw.ColorPicker(self.evObjEdit, 80,
				height, 80, guiWidgetHeight, self.guiLightColor.val, "Light color")
				
			self.guiLightPower = Draw.Number("Power: ", self.evObjEdit,
				180, height, 150, guiWidgetHeight, self.guiLightPower.val, 0.0, 10000.0, "Intensity multiplier for color",
					dummyfunc, 10.0, 1.0)
			
			height += guiHeightOffset
			if obj.properties['YafRay']['type'] == "Area":
				self.guiLightSamples = Draw.Number("Samples: ", self.evObjEdit,
					180, height, 150, guiWidgetHeight, self.guiLightSamples.val, 0, 512, "Number of samples to be taken for direct lighting")
				self.guiLightCreateGeom = Draw.Toggle("Make light visible", self.evObjEdit, 10, height, 150,
					guiWidgetHeight, self.guiLightCreateGeom.val, "Creates a visible plane in the dimensions of the area light during the render.")

			elif obj.properties['YafRay']['type'] == "Sphere":
				self.guiLightRadius = Draw.Number("Radius: ", self.evObjEdit,
					10, height, 150, guiWidgetHeight, self.guiLightRadius.val, 0, 100.0, "Radius of sphere light",
						dummyfunc, 10.0, 2.0)
				self.guiLightSamples = Draw.Number("Samples: ", self.evObjEdit,
					180, height, 150, guiWidgetHeight, self.guiLightSamples.val, 0, 512, "Number of samples to be taken for direct lighting")
				height += guiHeightOffset
				self.guiLightCreateGeom = Draw.Toggle("Make light visible", self.evObjEdit, 10, height, 150,
					guiWidgetHeight, self.guiLightCreateGeom.val, "Creates a visible plane in the dimensions of the area light during the render.")

			elif obj.properties['YafRay']['type'] == "IES Light":
				self.guiLightIESFile = Draw.String("IES file: ", self.evObjEdit,
					10, height, 320, guiWidgetHeight, self.guiLightIESFile.val, 256, "File to be used as the light projection")
				height += guiHeightOffset
				Draw.PushButton("Browse", self.evGetIESFile,
					180, height, 150, guiWidgetHeight, "Select the file to be used as the light projection")
	
				height += guiHeightOffset
				self.guiLightIESSoftShadows = Draw.Toggle("Soft shadows", self.evObjEdit,
					10, height, 150, guiWidgetHeight, self.guiLightIESSoftShadows.val, "Use soft shadows")
				if self.guiLightIESSoftShadows.val:
					self.guiLightIESSamples = Draw.Number("Samples: ", self.evObjEdit,
						180, height, 150, guiWidgetHeight, self.guiLightIESSamples.val, 0, 512, "Sample number for soft shadows")

			elif obj.properties['YafRay']['type'] == "Spot":
				self.guiLightSpotPhotonOnly = Draw.Toggle("Photon Only", self.evObjEdit,
					10, height, 150, guiWidgetHeight, self.guiLightSpotPhotonOnly.val, "This spot will only throw photons not direct light")
				self.guiLightSpotSoftShadows = Draw.Toggle("Soft shadows", self.evObjEdit,
					180, height, 150, guiWidgetHeight, self.guiLightSpotSoftShadows.val, "Use soft shadows")
				if self.guiLightSpotSoftShadows.val:
					height += guiHeightOffset 
					self.guiLightSpotShadowFuzzyness = Draw.Number("Shadow Fuzzyness: ", self.evObjEdit,
						10, height, 150, guiWidgetHeight, self.guiLightSpotShadowFuzzyness.val, 0.0, 1.0, "Fuzzyness of the soft shadows (0 - hard shadow, 1 - fuzzy shadow)")
					self.guiLightSpotSamples = Draw.Number("Samples: ", self.evObjEdit,
						180, height, 150, guiWidgetHeight, self.guiLightSpotSamples.val, 0, 512, "Sample number for soft shadows")

			elif obj.properties['YafRay']['type'] == "Sun":
				self.guiLightAngle = Draw.Number("Angle: ", self.evObjEdit,
					10, height, 150, guiWidgetHeight, self.guiLightAngle.val, 0, 80.0,"Angle of the cone in degrees (shadow softness)")
				self.guiLightSamples = Draw.Number("Samples: ", self.evObjEdit,
						180, height, 150, guiWidgetHeight, self.guiLightSamples.val, 0, 512, "Number of samples to be taken for direct lighting")

			elif obj.properties['YafRay']['type'] == "Directional":
				self.guiLightInfinite = Draw.Toggle("Infinite", self.evObjEdit,
					10, height, 150, guiWidgetHeight, self.guiLightInfinite.val, "Determines if light is infinite or filling a semi-infinite cylinder")
				if not self.guiLightInfinite.val:
					self.guiLightRadius = Draw.Number("Radius: ", self.evObjEdit,
						180, height, 150, guiWidgetHeight, self.guiLightRadius.val, 0, 10000.0, "Radius of semi-infinit cylinder (only applies if infinite=false)",
						dummyfunc, 10.0, 1.0)

		else: # settings for mesh objects
			drawText(10, height, "Meshobject settings", "large")

			height += guiHeightOffset
			
			height = drawTextLine(10, height, "Object: " + obj.name)
			
			height += guiHeightOffset
			
			self.guiMeshLightEnable = Draw.Toggle("Enable meshlight ", self.evToggleMeshlight, 10,
				height, 150, guiWidgetHeight, self.guiMeshLightEnable.val, "Makes the mesh emit light.")
			self.guiMeshVolumeEnable = Draw.Toggle("Enable volume", self.evToggleVolume, 180,
				height, 150, guiWidgetHeight, self.guiMeshVolumeEnable.val, "Makes the mesh a volume at its bounding box.")

			if self.guiMeshLightEnable.val:
				height = drawSepLineText(10, height, 320, "Meshlight settings")
				drawText(10, height + 4, "Meshlight color:")
				self.guiMeshLightColor = Draw.ColorPicker(self.evObjEdit, 100,
					height, 60, guiWidgetHeight, self.guiMeshLightColor.val, "Meshlight color")
				self.guiMeshLightPower = Draw.Number("Power: ", self.evObjEdit, 180, height,
					150, guiWidgetHeight, self.guiMeshLightPower.val, 0.0, 10000.0, "Intensity multiplier for color",
					dummyfunc, 10.0, 1.0)
					
				height += guiHeightOffset
				
				self.guiMeshLightDoubleSided = Draw.Toggle("Double Sided", self.evObjEdit, 10,
					height, 150, guiWidgetHeight, self.guiMeshLightDoubleSided.val, "Emit light at both sides of every face.")
				self.guiMeshLightSamples = Draw.Number("Samples: ", self.evObjEdit, 180,
					height, 150, guiWidgetHeight, self.guiMeshLightSamples.val, 0, 512, "Number of samples to be taken for direct lighting")
						
			if self.guiMeshVolumeEnable.val:
				height = drawSepLineText(10, height, 320, "Volume settings")
				self.guiMeshVolumeRegionType = Draw.Menu(makeMenu("Volume Region ", self.VolumeRegionTypes), self.evObjEdit,
					10, height, 150, guiWidgetHeight, self.guiMeshVolumeRegionType.val, "Set the volume region")
				height += guiHeightOffset
				self.guiMeshVIsa = Draw.Number("Absorption: ", self.evObjEdit, 10,
					height, 150, guiWidgetHeight, self.guiMeshVIsa.val, 0.0, 1.0, "Absorption coefficient")
				self.guiMeshVIss = Draw.Number("Scatter: ", self.evObjEdit, 180,
					height, 150, guiWidgetHeight, self.guiMeshVIss.val, 0.0, 1.0, "Scattering coefficient")
				height += guiHeightOffset

				#height += guiHeightOffset
				#self.guiMeshVIle = Draw.Number("L e", self.evObjEdit, 10,
				#	height, 150, guiWidgetHeight, self.guiMeshVIle.val, 0.0, 1.0, "Emitted light")
				#height += guiHeightOffset
				#self.guiMeshVIg = Draw.Number("g", self.evObjEdit, 10,
				#	height, 150, guiWidgetHeight, self.guiMeshVIg.val, -1.0, 1.0, "Phase coefficient")

				if self.guiMeshVolumeRegionType.val == self.VolumeRegionTypes.index("ExpDensityVolume"):
					self.guiMeshVIexpa = Draw.Number("Height: ", self.evObjEdit, 10,
						height, 150, guiWidgetHeight, self.guiMeshVIexpa.val, 0.0, 1000.0, "",
						dummyfunc, 10.0, 1.0)
					self.guiMeshVIexpb = Draw.Number("Steepness: ", self.evObjEdit, 180,
						height, 150, guiWidgetHeight, self.guiMeshVIexpb.val, 0.0, 10.0, "",
						dummyfunc, 10.0, 3.0)

				elif self.guiMeshVolumeRegionType.val == self.VolumeRegionTypes.index("NoiseVolume"):
					self.guiMeshVINoiseSharpness = Draw.Number("Sharpness: ", self.evObjEdit, 10,
						height, 150, guiWidgetHeight, self.guiMeshVINoiseSharpness.val, 1, 100.0, "",
						dummyfunc, 10.0, 3.0)
					self.guiMeshVINoiseCover = Draw.Number("Cover: ", self.evObjEdit, 180,
						height, 150, guiWidgetHeight, self.guiMeshVINoiseCover.val, 0.0, 1.0, "")
					height += guiHeightOffset
					self.guiMeshVIDensity = Draw.Number("Density: ", self.evObjEdit, 10,
						height, 150, guiWidgetHeight, self.guiMeshVIDensity.val, 0.1, 100.0, "Overall density multiplier",
						dummyfunc, 10.0, 3.0)

		PanelHeight = height
		
	def event(self):
		self.setPropertyList()
		for el in self.connector:
			setParam(el[0],el[1],el[2],el[3])

# ### end classTabObject ### #



def event(evt, val):	# the function to handle input events
	global lastMousePosX, lastMousePosY, guiDrawOffset, middlePressed, currentSelection, PanelHeight

	mouseX, mouseY = Window.GetMouseCoords()

	if middlePressed:
		if Window.GetMouseButtons() & Window.MButs['M']: # still pressed = dragging
			mouseDeltaY = lastMousePosY - mouseY
			guiDrawOffset -= mouseDeltaY
			lastMousePosX = mouseX
			lastMousePosY = mouseY
			Draw.Draw()
		else: # not pressed any more
			middlePressed = False
	elif not middlePressed and Window.GetMouseButtons() & Window.MButs['M']: # not yet pressed, start dragging
		lastMousePosX = mouseX
		lastMousePosY = mouseY
		middlePressed = True
	
	if evt == Draw.WHEELDOWNMOUSE:
		if (PanelHeight < 0):
			guiDrawOffset += 50
		Draw.Draw()
	elif evt == Draw.WHEELUPMOUSE:
		if (guiDrawOffset > 0):
			guiDrawOffset -= 50
		Draw.Draw()

	# exit when user presses Q
	if evt == Draw.QKEY:
		Draw.Exit()
		return
	elif evt == Draw.RKEY:
		# execute all init methods to ensure all properties are
		# initialized.  only on objects and materials, render settings
		# seem to be pointless, since they should be set by the user at
		# least once in any case
		for obj in Blender.Scene.GetCurrent().objects:
			TabObject.setPropertyList(obj)
		for mat in Blender.Material.Get():
			TabMaterial.setPropertyList(mat)
		yRender = yafrayRender()
		yRender.render()

	# redraw the UI if the selection changed from last event
	try:
		selection = Object.GetSelected()[0]
	except:
		selection = None
	if currentSelection != selection:
		currentSelection = selection
		Draw.Redraw(0)


def button_event(evt):  # the function to handle Draw Button events
	global Tab,libmat

	if evt:
		Draw.Redraw(0)

	if evt == evShowHelp:
		Tab = helpTab
	elif evt == evRender or evt == evRenderAnim or evt == evRenderView:
		# execute all init methods to ensure all properties are
		# initialized.  only on objects and materials, render settings
		# seem to be pointless, since they should be set by the user at
		# least once in any case
		TabRenderer.setPropertyList()
		for obj in Blender.Scene.GetCurrent().objects:
			TabObject.setPropertyList(obj)

		tmpMat = TabMaterial.curMat
		for mat in Blender.Material.Get():
			TabMaterial.setPropertyList(mat)
		TabMaterial.curMat = tmpMat

		yRender = yafrayRender()

		if evt == evRender:
			yRender.render()
		elif evt == evRenderView:
			yRender.render(True)
		elif evt == evRenderAnim:
			popupMsg = "Render animation (can be stopped with ESC in the GUI or Ctrl+C on the console), continue?%t|Yes%x0|No%x1"
			result = Draw.PupMenu(popupMsg)
			if result == 0:
				yRender.renderAnim()
	elif evt == TabObject.evShow:
		Tab = TabObject.tabNum
	elif evt == TabObject.evObjEdit:
		TabObject.event()
	elif evt == TabObject.evToggleMeshlight:
		TabObject.toggleMeshOption(0)
	elif evt == TabObject.evToggleVolume:
		TabObject.toggleMeshOption(1)
	elif evt == TabMaterial.evShow:
		Tab = TabMaterial.tabNum
		TabMaterial.changeMat()
	elif evt == TabMaterial.evEdit:
		if libmat:
			Draw.PupMenu("Error %t | Can't edit external libdata.")
			TabMaterial.changeMat()
		else:
			TabMaterial.event()
	elif evt == TabMaterial.evChangeMat:
		TabMaterial.changeMat()
	elif evt == TabMaterial.evMatFromObj:
		TabMaterial.event(evt)
	elif evt == TabMaterial.evRefreshPreview:
		TabMaterial.refreshPreview()

	elif evt == TabWorld.evShow:
		Tab = TabWorld.tabNum
	elif evt == TabWorld.evEdit:
		TabWorld.event()

	elif evt == TabRenderer.evShow:
		Tab = TabRenderer.tabNum
	elif evt == TabRenderer.evEdit:
		TabRenderer.event()
	elif evt == TabRenderer.evChangeRenderset:
		TabRenderer.changeSet()
	elif evt == TabRenderer.evChangeSetName:
		TabRenderer.changeSetName()

	# Sanne: sunsky
	elif evt == TabWorld.evGetSunAngle:
		TabWorld.sunPosAngle("get", "angle")
	elif evt == TabWorld.evGetSunPos:
		TabWorld.sunPosAngle("get", "position")
	elif evt == TabWorld.evUpdateSun:
		TabWorld.sunPosAngle("update")
	elif evt == TabWorld.evSunNormalToNumber:
		TabWorld.sunNormalToNumber()
	elif evt == TabWorld.evSunNumberToNormal:
		TabWorld.sunNumberToNormal()
		
	#DarkTide IES Lights
	elif evt == TabObject.evGetIESFile:
		TabObject.getIesFile()

	elif evt == TabObject.evDOFObj:
		TabObject.dofObj()
	Draw.Redraw(1)

# end button_event()



# Help menu

def drawHelp(height):
	y = height

	drawText(10, height, "Help", "large")
	#y = drawTextLine(20, y, "Object/Light/Camera:", "large")
	y = drawSepLineText(10, y, 320, "Object/Light/Camera")
	y = drawTextParagraph(20, y, 300, "Objects can act as light sources, settable here. \n\
 \n\
 The light type must be set in the blender UI and afterwards *also* in the\
 script. Yafray light types are \"mapped\" onto blender lights, like so: \n\
 Blender: Sun\t\tYafray: Sun, Directional \n\
 Blender: Lamp\t\tYafray: Point, Sphere \n\
 Blender: Area\t\tYafray: Area \n\
 Blender: Spot\t\tYafray: Spot \n\
 All other parameters are set in the script, blender's settings won't have\
 any effect. \n\
 \n\
 Camera settings for DOF and type of camera (check out the angular\
 camera for real 360 deg. lightprobes/angular maps ;-))")

	y = drawSepLineText(10, y, 320, "Materials")
	y = drawTextParagraph(20, y, 300, "First off, you need to have a blender material\
 i.e., \"Add New\" at Blender's \"Material Button\".  Materials are still assigned in the\
 Blender-way. \n\
 But: The material's color etc. are solely set in this script.\
 Only the textures are set in the blender UI (Texture, Map Input, Map to tabs)\
 Of course, not all texture slots are supported by all materials,\
 see the material itself to see, which slots are supported.")

	y = drawSepLineText(10, y, 320, "Render settings")
	y = drawTextParagraph(20, y, 300, "Pretty straight forward. If you use >Texture< as background,\
 the blender world texture will be used. The texture type (i.e.\
 angular, spherical, tube) is still set in the blender UI, low and high\
 range maps are possible as backgrounds, but if you want to use IBL,\
 you should use a HDRI map.")





def gui():				# the function to draw the screen
	size = Window.GetAreaSize()
	BGL.glClearColor(.7,.7,.7,1)
	BGL.glClear(BGL.GL_COLOR_BUFFER_BIT)
	BGL.glColor3f(1,1,1)

	largeButtonHeight = int(guiWidgetHeight * 1.5)
	height = size[1] - 25 + guiDrawOffset
	height -= 10
	Draw.PushButton("R E N D E R", evRender, 10, height, 130, largeButtonHeight, "Render image")
	Draw.PushButton("Render anim", evRenderAnim, 150, height, 85, largeButtonHeight, "Render animation into Blender output dir")
	Draw.PushButton("Render view", evRenderView, 245, height, 85, largeButtonHeight, "Render current 3D view")

	BGL.glColor3f(0, 0, 0)
	height = drawSepLineText(10, height, 320, "YafaRay Settings")
	height -= 10
	Draw.PushButton("Objects", TabObject.evShow, 10, height, 74, largeButtonHeight, "Edit object properties")
	Draw.PushButton("Material", TabMaterial.evShow, 92, height, 74, largeButtonHeight, "Edit materials")
	Draw.PushButton("World", TabWorld.evShow, 174, height, 74, largeButtonHeight, "Edit world settings")
	Draw.PushButton("Settings", TabRenderer.evShow, 256, height, 74, largeButtonHeight, "Edit the render settings")

	#height += guiHeightOffset
	#Draw.PushButton("Help", evShowHelp, 240, height, 90, guiWidgetHeight, "Short help")

	height -= 10
	drawHLine(10, height, 320)
	height -= 20

	if Tab == TabObject.tabNum: # settings for objects
		TabObject.draw(height)
	elif Tab == TabMaterial.tabNum: # settings for materials
		TabMaterial.draw(height)
	elif Tab == TabWorld.tabNum: # settings for materials
		TabWorld.draw(height)
	elif Tab == TabRenderer.tabNum: # settings for renderer
		TabRenderer.draw(height)
	elif Tab == helpTab:
		drawHelp(height)
	else:
		drawText(10, height, "Select a tab from above.", "large")


# "main" program

def main():
	[verCheck, intfVer] = checkVersion(__version__)
	if not verCheck:
		print "ERROR: Aborting YafaRay UI script, version number "\
		+ __version__ + " is not the same as interface " + intfVer + "."
		return

	expVer = yaf_export.getVersion()
	[verCheck, intfVer] = checkVersion(expVer)
	if not verCheck:
		print "ERROR: Aborting: yaf_export.py script, version number "\
		+ expVer + " is not the same as interface " + intfVer + "."
		return

	global guiHeightOffset, guiWidgetHeight, guiDrawOffset, lastMousePosX,\
	lastMousePosY, middlePressed, currentSelection,\
	Tab, noTab, helpTab, evShowHelp, evRenderView, evRender, evRenderAnim,\
	TabMaterial, TabWorld, TabRenderer, TabObject, uniqueCounter, libmat, PanelHeight

	PanelHeight = 100
	libmat = False
	guiHeightOffset = -20
	guiWidgetHeight = 15
	guiDrawOffset = 0
	lastMousePosX = 0
	lastMousePosY = 0
	middlePressed = False
	currentSelection = None

	Tab = getUniqueValue()
	noTab = getUniqueValue()
	helpTab = getUniqueValue()

	# events
	evShowHelp = getUniqueValue()
	evRenderView = getUniqueValue()
	evRender = getUniqueValue()
	evRenderAnim = getUniqueValue()

	TabMaterial = clTabMaterial()
	TabWorld = clTabWorld()
	TabRenderer = clTabRender()
	TabObject = clTabObject()
	Draw.Register(gui, event, button_event)  # registering the 3 callbacks

if __name__ == "__main__":
    main()
