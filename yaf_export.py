#!BPY

__author__ = ['Bert Buchholz']
__version__ = '0.1.1'
__url__ = ['http://yafaray.org']
__bpydoc__ = ""

import platform
import os
import sys

dllPath = ""
haveQt = False

import tempfile

import yafrayinterface
from yaf_material import yafMaterial
from yaf_texture import yafTexture
from yaf_light import yafLight
from yaf_object import yafObject

import Blender
from Blender import *
from Blender.Scene import *
from Blender import Mathutils
from Blender.Mathutils import * 

def getVersion():
	return __version__


def paramsSetFloat(props, name, key):
	if key in props.keys():
		yi.paramsSetFloat(name, props[key])

def paramsSetPoint(props, name, key):
	if name in props.keys():
		p = props[key]
		yi.paramsSetPoint(name, p[0], p[1], p[2])

def namehash(obj):
	# TODO: Better hashing using mat.__str__() ?
	nh = obj.name + "." + str(obj.__hash__())
	return nh


class yafrayRender:
	def __init__(self, isPreview = False):
		self.haveQt = haveQt

		self.scene = Scene.GetCurrent()
		self.viewRender = False # rendering the 3D view (no borders, persp cam)

		# chose between normal renderer into image/GUI and writing to XML
		try:
			self.useXML = self.scene.properties["YafRay"]["Renderer"]["xml"]
		except:
			self.useXML = False

		if self.useXML and not isPreview:
			self.yi = yafrayinterface.xmlInterface_t()
			outputFile = self.getOutputFilename(None, False)
			outputFile += '.xml'
			self.yi.setOutfile(outputFile)
		else:
			self.yi = yafrayinterface.yafrayInterface_t()

		# print "dllPath: " + dllPath
		self.yi.loadPlugins(dllPath)

		self.textures = set()
		self.materials = set()
		self.materialMap = dict()

		#self.collectObjects()
		self.yTexture = yafTexture(self.yi)
		self.yMaterial = yafMaterial(self.yi, self.materialMap)
		self.yLight = yafLight(self.yi)
		self.yObject = yafObject(self.yi, self.materialMap)
		self.inputGamma = 1.0


	def collectObjects(self):
		self.objects = set()    # Real objects
		self.instanced = set()  # Instanced object (to not render)
		self.instances = []     # Instances object
		self.oduplis = set()    # Dupli object

		#print "==============COLLECT=================="
		for o in self.scene.objects:
			if ((o.Layers & self.scene.Layers) > 0):
				self.collectObject(o, o.getMatrix())
		#print "---------------------------------------"
		#print "REAL OBJECTS:"
		#for o in self.objects:
		#	print o,o.getType()
		#print "---------------------------------------"
		#print "INSTANCED OBJECTS:"
		#for o in self.instanced:
		#	print o,o.getType()
		#print "----------------------------------------"
		#print "INSTANCES OBJECTS:"
		#for o,m in self.instances:
		#	print o,o.getType()
		#print "----------------------------------------"
		#print "DUPLIS OBJECTS:"
		#for o in self.oduplis:
		#	print o,o.getType()
		#print "_______________________________________"


	def collectObject(self, obj, matrix, isOriginal=True, isDupli=False, iobj=None):
		if (obj.users > 0):
			#TODO: check dupframes
			if (obj.enableDupFrames and isOriginal):
				for o, m in obj.DupObjects:
					self.collectObject(o, m, False)
			if (obj.getParticleSystems()):
				# Particles object
				for pSys in obj.getParticleSystems():
					if (pSys.drawAs == Blender.Particle.DRAWAS.OBJECT):
						# Add the object linked as instanced if exists
						if (pSys.duplicateObject):
							self.instanced.add(pSys.duplicateObject)
						for o, m in obj.DupObjects:
							self.collectObject(o, m, True, True)
			if (obj.enableDupGroup):
				self.oduplis.add(obj)
				for o, m in obj.DupObjects:
					self.collectObject(o, m, True, False)
			elif (obj.enableDupVerts or obj.enableDupFaces):
				self.oduplis.add(obj)
				for o, m in obj.DupObjects:
					self.collectObject(o, m, True, True)
			else:
				if (isDupli):
					self.instances.append([obj,matrix])
				else:
					if (obj.getMatrix()==matrix and obj.getParent() in self.oduplis):
						# This object is instanced by other objects
						self.instanced.add(obj)
					elif (obj.getParent() in self.oduplis):
						# This is an instance object
						self.instances.append([obj,matrix])
					else:
						# Single linked grouped
						if (obj.getMatrix()==matrix):
							# This object is a real object in a group
							# Check first if it's already an instanced one
							if (not obj in self.instanced):
								self.objects.add(obj)
						else:
							self.instanced.add(obj)
							self.instances.append([obj,matrix])


	def startScene(self):
		self.inputGamma = self.scene.properties["YafRay"]["Renderer"]["gammaInput"]
		self.yi.setInputGamma(self.inputGamma, True)
		self.yi.startScene()

	def processMaterialTextures(self, mat):
		if mat:
			if mat.properties['YafRay']['type'] == 'blend':
				# recursive
				try:
					mat1 = Blender.Material.Get(mat.properties['YafRay']['material1'])
					mat2 = Blender.Material.Get(mat.properties['YafRay']['material2'])
				except:
        	                	print "WARNING: Problem with blend material", mat.name, "Could not find one of the two blended materials."
					return
				for material in [mat1, mat2]:
					self.processMaterialTextures(material)
				self.exportMaterialTextures(mat)
			else:
				self.exportMaterialTextures(mat)


	def exportMaterialTextures(self, mat):
		mtextures = mat.getTextures()
		tname = "";
		if hasattr(mat, 'enabledTextures'):
			used = mat.enabledTextures
			for m in used:
				mtex = mtextures[m]
				tex = mtex.tex
				tname = namehash(tex)
				
				if (tex in self.textures) or tex.type == Blender.Texture.Types.NONE: continue
				self.yTexture.writeTexture(tex, tname, mat.lib, self.inputGamma)
				self.textures.add(tex)
		else:
			for mtex in mtextures:
				if mtex == None: continue
				tex = mtex.tex
				if tex == None: continue
				tname = namehash(tex)
				if tex in self.textures: continue

				self.yTexture.writeTexture(tex, tname, mat.lib, self.inputGamma)
				self.textures.add(tex)
		return tname
		

	def processObjectTextures(self, mesh_object):
		isVolume = False
		try:
			objProp = mesh_object.properties["YafRay"]
			isVolume = objProp["volume"]
		except:
			objProp = None

		for mat in mesh_object.getData().getMaterials():
			if isVolume:
				objProp["noise_tex"] = self.exportMaterialTextures(mat)
			else:
				self.processMaterialTextures(mat)

	def isMesh(self,object):
		# Check if an object can be rendered
		if object.getType() == "Mesh":
			return True
		elif object.getType() == "Curve":
			#curve = object.getData()
			#if (curve.bevob or curve.taperob):
			#	return True
			return True
		elif object.getType() == "Surf":
			return True
		#elif object.getType() == "MBall":
		#	return True
		#elif object.getType() == "Text":
		#	return True
		return False

	def exportTextures(self):
		print "INFO: Exporting Textures"
		self.textures = set()
		for o in self.objects:
			if self.isMesh(o):
				self.processObjectTextures(o)
		for o in self.instanced:
			if self.isMesh(o):
				self.processObjectTextures(o)

	def exportObjects(self):
		print "INFO: Exporting Objects"
		scene = self.scene

		self.yObject.createCamera(self.yi, scene, self.viewRender)
		
		# Export real objects
		for o in self.objects:
			if self.isMesh(o):
				self.yObject.writeObject(self.yi, o)

		# Export instances
		for o,m in self.instances:
			if self.isMesh(o):
				self.yObject.writeObject(self.yi, o, m)

	def exportLightMaterial(self, object):
		lamp_mat = None
		props = object.properties["YafRay"]
		if ((props["type"]=="Sphere" or props["type"]=="Area") and props["createGeometry"] == True):
			self.yi.paramsSetString("type", "light_mat")
			self.yi.paramsSetFloat("power", props["power"])
			color = props["color"]
			self.yi.paramsSetColor("color", color[0], color[1], color[2])
			lamp_mat = self.yi.createMaterial(object.name)
		return lamp_mat


	def exportLights(self):
		print "INFO: Exporting Lights"
		# Export real lamps
		for o in self.objects:
			if o.getType() == 'Lamp':
				lmat = self.exportLightMaterial(o)
				self.yLight.createLight(self.yi, o, None, lmat)

		# Export instanced lamps
		# As it is now we make instances real
		for i in self.instanced:
			if i.getType() == 'Lamp':
				lmat = self.exportLightMaterial(i)
				idx=0
				for o,m in self.instances:
					if (o==i):
						self.yLight.createLight(self.yi, o, m, lmat, idx)
						idx += 1

	def exportMaterial(self,material):
		if material:
			if material.properties['YafRay']['type'] == 'blend':
				# must make sure all materials used by a blend mat
				# are written before the blend mat itself
				self.handleBlendMat(material)
			else:
				self.materials.add(material)
				self.yMaterial.writeMaterial(material)

	def processObjectMaterials(self, object):
		# Export materials attached to a mesh
		mesh = object.getData()
		for mat in mesh.materials:
			if mat in self.materials: continue
			self.exportMaterial(mat)

	def exportMaterials(self):
		print "INFO: Exporting Materials"
		self.materials = set()
		self.yi.paramsClearAll()
		self.yi.paramsSetString("type", "shinydiffusemat")
		print "INFO: Exporting Material: defaultMat"
		ymat = self.yi.createMaterial("defaultMat")
		self.materialMap["default"] = ymat
		
		for object in self.objects:
			if self.isMesh(object):
				self.processObjectMaterials(object)
		for object in self.instanced:
			if self.isMesh(object):
				self.processObjectMaterials(object)


	def handleBlendMat(self, mat):
		try:
			mat1 = Blender.Material.Get(mat.properties['YafRay']['material1'])
			mat2 = Blender.Material.Get(mat.properties['YafRay']['material2'])
		except:
			print "WARNING: Problem with blend material", mat.name, ". Could not find one of the two blended materials."
			return

		if mat1.properties['YafRay']['type'] == 'blend':
			self.handleBlendMat(mat1)
		elif not mat1 in self.materials:
			self.materials.add(mat1)
			self.yMaterial.writeMaterial(mat1)

		if mat2.properties['YafRay']['type'] == 'blend':
			self.handleBlendMat(mat2)
		elif not mat2 in self.materials:
			self.materials.add(mat2)
			self.yMaterial.writeMaterial(mat2)

		if not mat in self.materials:
			self.materials.add(mat)
			self.yMaterial.writeMaterial(mat)


	def exportIntegrator(self):
		yi = self.yi
		yi.paramsClearAll()

		renderer = self.scene.properties["YafRay"]["Renderer"]

		ss = "   Raydepth: " + str(renderer["raydepth"])
		ss += " Shadowdepth: " + str(renderer["shadowDepth"]) + '\n'
		ss += "Lighting: "

		yi.paramsSetInt("raydepth", renderer["raydepth"])
		yi.paramsSetInt("shadowDepth", renderer["shadowDepth"])
		yi.paramsSetBool("transpShad", renderer["transpShad"])

		light_type = renderer["lightType"]
		print "INFO: Exporting Integrator:",light_type

		if "Direct lighting" == light_type:
			yi.paramsSetString("type", "directlighting");
			ss += " direct lighting"
			yi.paramsSetBool("caustics", renderer["caustics"])

			if renderer["caustics"]:
				yi.paramsSetInt("photons", renderer["photons"])
				yi.paramsSetInt("caustic_mix", renderer["caustic_mix"])
				yi.paramsSetInt("caustic_depth", renderer["caustic_depth"])
				yi.paramsSetFloat("caustic_radius", renderer["caustic_radius"])
				ss += ", caustics (photons: " + str(renderer["photons"]) + ")"

			if renderer["do_AO"]:
				yi.paramsSetBool("do_AO", renderer["do_AO"])
				yi.paramsSetInt("AO_samples", renderer["AO_samples"])
				yi.paramsSetFloat("AO_distance", renderer["AO_distance"])
				c = renderer["AO_color"];
				yi.paramsSetColor("AO_color", c[0], c[1], c[2])
				ss += ", AO (samples: " + str(renderer["AO_samples"]) + ")";
		elif "Photon mapping" == light_type:
			# photon integrator
			yi.paramsSetString("type", "photonmapping")
			yi.paramsSetInt("fg_samples", renderer["fg_samples"])
			yi.paramsSetInt("photons", renderer["photons"])
			yi.paramsSetInt("cPhotons", renderer["cPhotons"])
			yi.paramsSetFloat("diffuseRadius", renderer["diffuseRadius"])
			yi.paramsSetFloat("causticRadius", renderer["causticRadius"])
			yi.paramsSetInt("search", renderer["search"])
			yi.paramsSetBool("show_map", renderer["show_map"])
			yi.paramsSetInt("fg_bounces", renderer["fg_bounces"])
			yi.paramsSetInt("caustic_mix", renderer["caustic_mix"])
			yi.paramsSetBool("finalGather", renderer["finalGather"])
			yi.paramsSetInt("bounces", renderer["bounces"])
			yi.paramsSetBool("use_background", renderer["use_background"])

			ss += " GI: photons (" + str(renderer["photons"]) + "), bounces: " + str(renderer["bounces"])
			if "use_background" in renderer:
				ss += " with background"
			else:
				ss += " without background"

		elif "Pathtracing" == light_type:
			yi.paramsSetString("type", "pathtracing");
			yi.paramsSetInt("path_samples", renderer["path_samples"])
			yi.paramsSetInt("bounces", renderer["bounces"])
			yi.paramsSetBool("no_recursive", renderer["no_recursive"])
			
			caus_type = renderer["caustic_type"]
			photons = False;
			if caus_type == "None":
				yi.paramsSetString("caustic_type", "none");
			elif caus_type == "Path":
				yi.paramsSetString("caustic_type", "path");
			elif caus_type == "Photon":
				yi.paramsSetString("caustic_type", "photon")
				photons = True
			elif caus_type == "Path+Photon":
				yi.paramsSetString("caustic_type", "both")
				photons = True

			if photons:
				yi.paramsSetInt("photons", renderer["photons"])
				yi.paramsSetInt("caustic_mix", renderer["caustic_mix"])
				yi.paramsSetInt("caustic_depth", renderer["caustic_depth"])
				yi.paramsSetFloat("caustic_radius", renderer["caustic_radius"])

			ss += " GI: pathtracer, samples: " + str(renderer["path_samples"])
			yi.paramsSetBool("use_background", renderer["use_background"])
			ss += ", bounces: " + str(renderer["bounces"])
			if "use_background" in renderer:
				ss += " with background"
			else:
				ss += " without background"
		elif "Bidir. Pathtr." == light_type or "Bidirectional" == light_type or "Bidirectional (EXPERIMENTAL)" == light_type:
			yi.paramsSetString("type", "bidirectional")
		elif "Debug" == light_type:
			yi.paramsSetString("type", "DebugIntegrator")
			debugTypeStr = renderer["debugType"]
			#std::cout << "export: " << debugTypeStr << std::endl;
			if "N" == debugTypeStr:
				yi.paramsSetInt("debugType", 1);
			elif "dPdU" == debugTypeStr:
				yi.paramsSetInt("debugType", 2);
			elif "dPdV" == debugTypeStr:
				yi.paramsSetInt("debugType", 3);
			elif "NU" == debugTypeStr:
				yi.paramsSetInt("debugType", 4);
			elif "NV" == debugTypeStr:
				yi.paramsSetInt("debugType", 5);
			elif "dSdU" == debugTypeStr:
				yi.paramsSetInt("debugType", 6);
			elif "dSdV" == debugTypeStr:
				yi.paramsSetInt("debugType", 7);

			yi.paramsSetBool("showPN",renderer["show_perturbed_normals"]);
		yi.createIntegrator("default")
		yi.addToParamsString(ss);

		return True;


	def exportWorld(self):
		yi = self.yi
		renderprops = self.scene.properties["YafRay"]["Renderer"]
		world = self.scene.world
	
		# preset a default background
		worldProp = {	"bg_type":	"Single Color",
				"color":	[0,0,0],
				"ibl":		0,
				"ibl_samples":	16,
				"power":	1.0
				}

		if world:
			if world.properties.has_key('YafRay'):
				worldProp = world.properties["YafRay"]

		bg_type = worldProp["bg_type"]
		print "INFO: Exporting World, type:",bg_type
		yi.paramsClearAll();

		if "Texture" == bg_type:
			if hasattr(world, 'textures'):
				mtex = world.textures[0]
				if mtex != None:
					worldTex = mtex.tex
			else:
				for tex in Texture.Get():
					if tex.name == "World":
						worldTex = tex
						break

			try:
				worldTex
			except:
				print "WARNING: No or incorrectly defined world tex! If you are using Blender 2.47 official release or earlier, you must rename your world texture to: World"
				return False;

			#print "INFO: World texture:", worldTex.name
			img = worldTex.getImage()
			print "INFO: Exporting World Texture:", worldTex.name, img.getFilename()
			# now always exports if image used as world texture (and 'Hori' mapping enabled)
			# duplicated code, ideally export texture like any other
			if worldTex.type == Blender.Texture.Types.IMAGE and img != None:
				yi.paramsSetString("type", "image")
				yi.paramsSetString("filename", Blender.sys.expandpath(img.getFilename()) )
				# exposure_adjust not restricted to integer range anymore
				yi.paramsSetFloat("exposure_adjust", worldTex.brightness-1);
				if worldTex.interpol == Blender.Texture.ImageFlags.INTERPOL:
					yi.paramsSetString("interpolate", "bilinear");
				else:
					yi.paramsSetString("interpolate", "none");
				yi.createTexture("world_texture");

				# Export the actual background
				yi.paramsClearAll();
				if mtex.texco == Blender.Texture.TexCo.ANGMAP:
					yi.paramsSetString("mapping", "probe");
				else: # elif mtex.texco == Blender.Texture.TexCo.HSPHERE:
					yi.paramsSetString("mapping", "sphere");
				
				yi.paramsSetString("type", "textureback");
				yi.paramsSetString("texture", "world_texture");
				# right now you are "forced" to use IBL...
				yi.paramsSetBool("ibl", worldProp["ibl"])
				yi.paramsSetInt("ibl_samples", worldProp["ibl_samples"])
				yi.paramsSetFloat("power", worldProp["power"]);
				yi.paramsSetFloat("rotation", worldProp["rotation"])

		elif "Gradient" == bg_type:
			c = worldProp["horizon_color"]
			yi.paramsSetColor("horizon_color", c[0], c[1], c[2])
			c = worldProp["zenith_color"]
			yi.paramsSetColor("zenith_color", c[0], c[1], c[2])
			c = worldProp["horizon_ground_color"]
			yi.paramsSetColor("horizon_ground_color", c[0], c[1], c[2])
			c = worldProp["zenith_ground_color"]
			yi.paramsSetColor("zenith_ground_color", c[0], c[1], c[2])
			yi.paramsSetFloat("power", worldProp["power"])
			yi.paramsSetBool("ibl", worldProp["ibl"])
			yi.paramsSetInt("ibl_samples", worldProp["ibl_samples"])
			yi.paramsSetString("type", "gradientback")
		elif "Sunsky" == bg_type:
			f = worldProp["from"]
			yi.paramsSetPoint("from", f[0], f[1], f[2])
			yi.paramsSetFloat("turbidity", worldProp["turbidity"])
			yi.paramsSetFloat("a_var", worldProp["a_var"])
			yi.paramsSetFloat("b_var", worldProp["b_var"])
			yi.paramsSetFloat("c_var", worldProp["c_var"])
			yi.paramsSetFloat("d_var", worldProp["d_var"])
			yi.paramsSetFloat("e_var", worldProp["e_var"])
			yi.paramsSetBool("add_sun", worldProp["add_sun"])
			yi.paramsSetFloat("sun_power", worldProp["sun_power"])
			yi.paramsSetBool("background_light", worldProp["background_light"])
			yi.paramsSetInt("light_samples", worldProp["light_samples"])
			yi.paramsSetFloat("power", worldProp["power"])
			yi.paramsSetString("type", "sunsky")
		elif "DarkTide's SunSky" == bg_type:
			f = worldProp["from"]
			yi.paramsSetPoint("from", f[0], f[1], f[2])
			yi.paramsSetFloat("turbidity", worldProp["dsturbidity"])
			yi.paramsSetFloat("altitude", worldProp["dsaltitude"])
			yi.paramsSetFloat("a_var", worldProp["dsa"])
			yi.paramsSetFloat("b_var", worldProp["dsb"])
			yi.paramsSetFloat("c_var", worldProp["dsc"])
			yi.paramsSetFloat("d_var", worldProp["dsd"])
			yi.paramsSetFloat("e_var", worldProp["dse"])
			yi.paramsSetBool("clamp_rgb", renderprops["clamp_rgb"])
			yi.paramsSetBool("add_sun", worldProp["dsadd_sun"])
			yi.paramsSetFloat("sun_power", worldProp["dssun_power"])
			yi.paramsSetBool("background_light", worldProp["dsbackground_light"])
			yi.paramsSetInt("light_samples", worldProp["dslight_samples"])
			yi.paramsSetFloat("power", worldProp["power"])
			yi.paramsSetFloat("bright", worldProp["dsbright"])
			yi.paramsSetBool("night", worldProp["dsnight"])
			yi.paramsSetString("type", "darksky")
		else:
			c = worldProp["color"]
			yi.paramsSetColor("color", c[0], c[1], c[2])
			yi.paramsSetBool("ibl", worldProp["ibl"])
			yi.paramsSetInt("ibl_samples", worldProp["ibl_samples"])
			yi.paramsSetFloat("power", worldProp["power"])
			yi.paramsSetString("type", "constant");

		yi.createBackground("world_background")
		return True;

	def exportVolumeIntegrator(self):
		yi = self.yi
		yi.paramsClearAll();

		renderer = self.scene.properties["YafRay"]["Renderer"]
		world = self.scene.world
		
		# preset default volume integrator
		worldProp = {"volType": "None"}
	
		if world:
			if world.properties.has_key('YafRay'):
				worldProp = world.properties["YafRay"]
		
		vint_type = worldProp["volType"]
		print "INFO: Exporting Volume Integrator:",vint_type

		if "Single Scatter" == vint_type:
			yi.paramsSetString("type", "SingleScatterIntegrator");
			yi.paramsSetFloat("stepSize", worldProp["stepSize"])
			yi.paramsSetBool("adaptive", worldProp["adaptive"])
			yi.paramsSetBool("optimize", worldProp["optimize"])
		elif "Sky" == vint_type:
			yi.paramsSetString("type", "SkyIntegrator")
			yi.paramsSetFloat("turbidity", worldProp["dsturbidity"])
			yi.paramsSetFloat("stepSize", renderer["stepSize"])
			yi.paramsSetFloat("alpha", renderer["alpha"])
			yi.paramsSetFloat("sigma_t", renderer["sigma_t"])
		else:
			yi.paramsSetString("type", "none");

		yi.createIntegrator("volintegr");

		return True;

	def getOutputFilename(self, frameNumber, useDate = True):
		scene = self.scene
		render = scene.getRenderingContext()
		if frameNumber == None:
			outDir = Blender.Get("renderdir")
			if outDir == None: outDir = tempfile.gettempdir()
			if useDate:
				from datetime import datetime
				dt = datetime.now()
				outputFile = os.path.join(outDir,'yafaray-' + dt.strftime("%Y-%m-%d_%H%M%S"))
			else:
				outputFile = os.path.join(outDir,'yafarayRender')
		# animation, need to determine path + filename
		else:
			outPath = render.renderPath
			if len(outPath) > 0:
				padCount = outPath.count('#')

				if padCount > 0:
					formatStr = "%0" + str(padCount) + "d"
					formatStr =  formatStr % ( frameNumber )
					outPath = outPath.replace('#', formatStr, 1)
					outPath = outPath.replace('#','')
				else:
					formatStr = "%05d" % ( frameNumber )
					outPath += formatStr
				outputFile = outPath % {'fn' : frameNumber}
			else:
				outDir = Blender.Get("renderdir")
				if outDir == None: outDir = tempfile.gettempdir()
				outputFile = os.path.join(outDir,'yafaray-%(fn)05d' % {'fn' : frameNumber})
		outputFile = os.path.abspath(outputFile)
		return outputFile


	def writeRender(self):
		yi = self.yi
		scene = self.scene
		print "INFO: Exporting Render"
		render = scene.getRenderingContext()

		renderprops = scene.properties["YafRay"]["Renderer"]

		yi.setDrawParams(renderprops["drawParams"])

		yi.clearParamsString()
		yi.addToParamsString("YafaRay ($REVISION)    $TIME")
		paramsStr = "    " + renderprops["customString"] + "\n"
		paramsStr += "AA passes: " + str(renderprops["AA_passes"]) + ", AA samples: " + \
			str(renderprops["AA_minsamples"]) + "/" + str(renderprops["AA_inc_samples"]) + \
			" (" + renderprops["filter_type"] + ")"
		yi.addToParamsString(paramsStr)

		self.exportIntegrator()
		self.exportVolumeIntegrator()

		yi.paramsClearAll()
		yi.paramsSetString("camera_name", "cam")
		yi.paramsSetString("integrator_name", "default")
		yi.paramsSetString("volintegrator_name", "volintegr")

		yi.paramsSetFloat("gamma", renderprops["gamma"])
		yi.paramsSetInt("AA_passes", renderprops["AA_passes"])
		yi.paramsSetInt("AA_minsamples", renderprops["AA_minsamples"])
		yi.paramsSetInt("AA_inc_samples", renderprops["AA_inc_samples"])
		yi.paramsSetFloat("AA_pixelwidth", renderprops["AA_pixelwidth"])
		yi.paramsSetFloat("AA_threshold", renderprops["AA_threshold"])
		yi.paramsSetString("filter_type", renderprops["filter_type"])

		renderData = scene.getRenderingContext()
		sizeX = int(renderData.sizeX * renderData.renderwinSize / 100.0)
		sizeY = int(renderData.sizeY * renderData.renderwinSize / 100.0)

		bStartX = 0
		bStartY = 0
		bsizeX = 0
		bsizeY = 0

		# Shift only available if camera is selected
		if self.viewRender:
			shiftX = 0
			shiftY = 0
		else:
			# Sanne: get lens shift
			camera = scene.objects.camera.getData()
			maxsize = max(sizeX, sizeY)
			shiftX = int(camera.shiftX * maxsize)
			shiftY = int(camera.shiftY * maxsize)
		
		# no border when rendering to view
		if render.borderRender and not self.viewRender:
			minX = render.border[0] * sizeX
			minY = render.border[1] * sizeY
			maxX = render.border[2] * sizeX
			maxY = render.border[3] * sizeY
			bStartX = int(minX)
			bStartY = int(sizeY - maxY)
			# Sanne: add lens shift
			yi.paramsSetInt("xstart", bStartX + shiftX)
			yi.paramsSetInt("ystart", bStartY - shiftY)
			bsizeX = int(maxX - minX)
			bsizeY = int(maxY - minY)
			yi.paramsSetInt("width", bsizeX)
			yi.paramsSetInt("height", bsizeY)
		else:
			# Sanne: add lens shift
			yi.paramsSetInt("xstart", shiftX)
			yi.paramsSetInt("ystart", -shiftY)
			yi.paramsSetInt("width", sizeX)
			yi.paramsSetInt("height", sizeY)
		
		yi.paramsSetBool("clamp_rgb", renderprops["clamp_rgb"])
		yi.paramsSetBool("show_sam_pix", renderprops["show_sam_pix"])
		yi.paramsSetInt("tile_size", renderprops["tile_size"])
		if (renderprops["tiles_order"]=="Linear"):
			yi.paramsSetString("tiles_order", "linear")
		elif (renderprops["tiles_order"]=="Random"):
			yi.paramsSetString("tiles_order", "random")
		yi.paramsSetBool("z_channel", True)
		
		if renderprops["auto_threads"]:
			yi.paramsSetInt("threads", -1)
		else:
			yi.paramsSetInt("threads", renderprops["threads"])

		yi.paramsSetString("background_name", "world_background")

		return [sizeX, sizeY, bStartX, bStartY, bsizeX, bsizeY]

	def startRender(self, renderCoords, frameNumber = None):
		yi = self.yi
		scene = self.scene
		render = scene.getRenderingContext()
		renderprops = scene.properties["YafRay"]["Renderer"]
		# sizeX/Y is the actual size of the image, b* is bordered stuff
		[sizeX, sizeY, bStartX, bStartY, bsizeX, bsizeY] = renderCoords

		autoSave = renderprops["autoSave"]

		doAnimation = (frameNumber != None)


		saveToMem = renderprops["imageToBlender"]
		closeAfterFinish = False
		ret = 0

		if self.useXML:
			saveToMem = False
			co = yafrayinterface.outTga_t(0, 0, "")
			outputFile = self.getOutputFilename(None, False)
			outputFile += '.xml'
			print "INFO: Writing XML:", outputFile
			yi.render(co)
		# single frame output without GUI
		elif not self.haveQt:
			outputFile = self.getOutputFilename(frameNumber)
			outputFile += '.tga'
			print "INFO: Rendering to file:", outputFile;
			co = yafrayinterface.outTga_t(sizeX, sizeY, outputFile)
			yi.render(co)
		else:
			import yafqt
			outputFile = self.getOutputFilename(frameNumber)
			outputFile += '.png'
			print "Rendering to",outputFile
			yafqt.initGui()
			guiSettings = yafqt.Settings()
			guiSettings.autoSave = autoSave
			guiSettings.closeAfterFinish = closeAfterFinish
			guiSettings.mem = None
			guiSettings.fileName = outputFile
			guiSettings.autoSaveAlpha = renderprops["autoalpha"]

			if doAnimation:
				guiSettings.autoSave = True
				guiSettings.closeAfterFinish = True

			# will return > 0 if user canceled the rendering using ESC
			ret = yafqt.createRenderWidget(self.yi, sizeX, sizeY, bStartX, bStartY, guiSettings)

		if saveToMem and not doAnimation:
			imageMem = yafrayinterface.new_floatArray(sizeX * sizeY * 4)
			memIO = yafrayinterface.memoryIO_t(sizeX, sizeY, imageMem)
			yi.getRenderedImage(memIO)
			self.memoryioToImage(imageMem, "yafRender", sizeX, sizeY, bStartX, bStartY, bsizeX, bsizeY)
			yafrayinterface.delete_floatArray(imageMem)

		return ret

	def memoryioToImage(self, mem, name, sizeX, sizeY, bStartX, bStartY, bsizeX, bsizeY):
			realSizeX = sizeX
			realSizeY = sizeY
			if bsizeX > 0 and bsizeY > 0:
				realSizeX = bsizeX
				realSizeY = bsizeY
			img = Image.New(name, realSizeX, realSizeY, 128)
			Window.DrawProgressBar(0.0, "Image -> Buffer")

			for x in range(realSizeX):
				if (x % 20 == 0):
					progress = x / float(sizeX)
					Window.DrawProgressBar(progress, "Image -> Buffer")
				for y in range(realSizeY):
					# first row is on the bottom, therefore the idx must be reversed
					yafY = realSizeY - y - 1
					idx = x + yafY * sizeX
					idx *= 4
					colR = yafrayinterface.floatArray_getitem(mem, idx + 0)
					colG = yafrayinterface.floatArray_getitem(mem, idx + 1)
					colB = yafrayinterface.floatArray_getitem(mem, idx + 2)
					colA = yafrayinterface.floatArray_getitem(mem, idx + 3)
					img.setPixelHDR(x, y, (colR, colG, colB, colA))

			Window.DrawProgressBar(1.0, "Image -> Buffer")
			import bpy
			bpy.data.images.active = img
			Window.Redraw(Window.Types.IMAGE)

	def render(self, viewRender = False):
		self.viewRender = viewRender
		if not self.viewRender:
			if not self.scene.objects.camera:
				print "WARNING: No camera, using renderview"
				self.viewRender = True
		self.startScene()
		Window.DrawProgressBar(0.0, "YafaRay collecting ...")
		self.collectObjects()
		Window.DrawProgressBar(0.1, "YafaRay textures ...")
		self.exportTextures()
		Window.DrawProgressBar(0.2, "YafaRay materials ...")
		self.exportMaterials()
		Window.DrawProgressBar(0.4, "YafaRay lights ...")
		self.exportLights()
		# TODO: Check if we have at least one light (lamp, background, etc..)?
		#if not self.exportLights():
		#	Window.DrawProgressBar(1.0, "YafaRay rendering ...")
		#	return
		Window.DrawProgressBar(0.5, "YafaRay objects ...")
		self.exportObjects()
		Window.DrawProgressBar(0.9, "YafaRay world ...")
		self.exportWorld()
		renderCoords = self.writeRender()
		Window.DrawProgressBar(0.0, "YafaRay rendering ...")
		self.startRender(renderCoords)
		Window.DrawProgressBar(1.0, "YafaRay rendering ...")

	# render an animation, renders the frames as defined in the blender
	# UI, render to the output dir on F10 unless the string is empty
	def renderAnim(self):
		render = self.scene.getRenderingContext()
		startFrame = render.sFrame
		endFrame = render.eFrame
		# no rendering of animations using XML
		self.useXML = False
		self.viewRender = False

		for i in range(startFrame, endFrame + 1):
			print "INFO: Rendering frame", i
			render.currentFrame(i)
			self.yi.clearAll()
			self.startScene()
			self.collectObjects()
			self.exportTextures()
			self.exportMaterials()
			self.exportWorld()
			self.exportLights()
			#if not self.exportLights():
			#	return
			self.exportObjects()
			renderCoords = self.writeRender()
			userBreak = self.startRender(renderCoords, i)
			if userBreak > 0:
				break
				
	def renderCL(self):
		self.startScene()
		self.collectObjects()
		self.exportTextures()
		self.exportMaterials()
		self.exportLights()
		self.exportObjects()
		self.exportWorld()
		renderCoords = self.writeRender()
		self.startRender(renderCoords)
# ------------------------------------------------------------------------
#
# Material Preview Rendering
#
# ------------------------------------------------------------------------

	def createPreview(self, mat, size, imageMem):
		
		yi = self.yi
		yi.startScene(1)
		gammaIn = self.scene.properties["YafRay"]["Renderer"]["gammaInput"]
		yi.setInputGamma(gammaIn, True)

		self.textures = set()
		self.materials = set()

		# Textures
		self.processMaterialTextures(mat)
		
		# Material
		self.exportMaterial(mat)
		
		# Mesh
		yi.paramsClearAll()
		yi.paramsSetString("type", "sphere")
		yi.paramsSetPoint("center", 0, 0, 0)
		yi.paramsSetFloat("radius", 2)
		yi.paramsSetString("material", namehash(mat))
		yi.createObject("Sphere1")
		
		
		# Lights
		yi.paramsClearAll()
		yi.paramsSetColor("color", 1, 1, 1, 1)
		yi.paramsSetPoint("from", 11, 3, 8)
		yi.paramsSetFloat("power", 160)
		yi.paramsSetString("type", "pointlight")
		yi.createLight("LAMP1")

		yi.paramsClearAll()
		yi.paramsSetColor("color", 1, 1, 1, 1)
		yi.paramsSetPoint("from", -2, -10, 2)
		yi.paramsSetFloat("power", 18)
		yi.paramsSetString("type", "pointlight")
		yi.createLight("LAMP2")
		
		# Background
		yi.paramsClearAll()
		yi.paramsSetString("type", "sunsky")
		yi.paramsSetPoint("from", 1, 1, 1)
		yi.paramsSetFloat("turbidity", 3)
		yi.createBackground("world_background")
		
		# Camera
		yi.paramsClearAll()
		yi.paramsSetString("type", "perspective")
		yi.paramsSetFloat("focal", 2.4)
		yi.paramsSetPoint("from", 7, -7, 4.15)
		yi.paramsSetPoint("up", 6.12392, -6.11394, 7.20305)
		yi.paramsSetPoint("to", 4.89145, -4.88147, 2.90031)
		yi.paramsSetInt("resx", size)
		yi.paramsSetInt("resy", size)
		yi.createCamera("cam")
		
		# Integrators
		yi.paramsClearAll()
		yi.paramsSetString("type", "directlighting")
		yi.createIntegrator("default")
		
		yi.paramsClearAll()
		yi.paramsSetString("type", "none")
		yi.createIntegrator("volintegr")
		
		# Render
		yi.paramsClearAll()
		yi.paramsSetString("camera_name", "cam")
		yi.paramsSetString("integrator_name", "default")
		yi.paramsSetString("volintegrator_name", "volintegr")

		yi.paramsSetFloat("gamma", 1.8)
		yi.paramsSetInt("AA_passes", 1)
		yi.paramsSetInt("AA_minsamples", 1)
		yi.paramsSetFloat("AA_pixelwidth", 1.5)
		yi.paramsSetString("filter_type", "Mitchell")

		co = yafrayinterface.memoryIO_t(size, size, imageMem)

		yi.paramsSetInt("width", size)
		yi.paramsSetInt("height", size)

		yi.paramsSetBool("z_channel", False)
		yi.setDrawParams(False)
		#yi.paramsSetBool("threads", renderprops["threads"])

		yi.paramsSetString("background_name", "world_background")

		yi.render(co)
		yi.clearAll()
		
		self.yMaterial.materialMap.clear()

