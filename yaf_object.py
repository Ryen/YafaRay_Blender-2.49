import yafrayinterface

import Blender
from Blender import *
from Blender import Mathutils
from Blender.Mathutils import *
import math
import time
def getProperty(property, name):
	yi.printInfo("Exporter: Getting " + name + " out of " + property)
	if name in property:
		return property[name]

def getBBCorners(object):
	bb = object.getBoundBox(0)
	min = [1e10, 1e10, 1e10]
	max = [-1e10, -1e10, -1e10]

	for corner in bb:
		for i in range(3):
			if corner[i] < min[i]:
				min[i] = corner[i]
			if corner[i] > max[i]:
				max[i] = corner[i]
	
	return min, max

class yafObject:
	def __init__(self, interface, mMap):
		self.yi = interface
		self.materialMap = mMap
	
	def createCamera(self, yi, scene, useView = False):
		yi.printInfo("Exporter: Creating Camera...")

		renderData = scene.getRenderingContext()

		if not useView:
			camObj = scene.objects.camera
			camera = camObj.getData()

		if useView:
			# use the view matrix to calculate the inverted transformed
			# points cam pos (0,0,0), front (0,0,1) and up (0,1,0)
			# view matrix works like the opengl view part of the
			# projection matrix, i.e. transforms everything so camera is
			# at 0,0,0 looking towards 0,0,1 (y axis being up)

			m = Window.GetViewMatrix().__copy__()
			m.transpose()
			inv = m.invert()
			pos = inv * Vector(0, 0, 0, 1)
			aboveCam = inv * Vector(0, 1, 0, 1)
			frontCam = inv * Vector(0, 0, 1, 1)
			dir = frontCam - pos
			up = aboveCam - pos

		else:
			matrix = camObj.getMatrix()
			pos = matrix[3]
			dir = matrix[2]
			up = matrix[1]

		to = [pos[0] - dir[0], pos[1] - dir[1], pos[2] - dir[2]]

		yi.paramsClearAll()

		if useView:
			yi.paramsSetString("type", "perspective");
		else:
			camProp = camObj.properties["YafRay"]
			fdist = 1 # only changes for ortho


			camType = camProp["type"]

			if camType == "orthographic":
				yi.paramsSetString("type", "orthographic");
				yi.paramsSetFloat("scale", camProp["scale"])
			elif camType == "perspective" or camType == "architect":
				yi.paramsSetString("type", camType);
				f_aspect = 1.0;
				if renderData.sizeX * renderData.aspectX <= renderData.sizeY * renderData.aspectY:
					f_aspect = (renderData.sizeX * renderData.aspectX) / (renderData.sizeY * renderData.aspectY)

				#print "f_aspect: ", f_aspect
				yi.paramsSetFloat("focal", camera.lens/(f_aspect*32.0))
				
				# DOF params, only valid for real camera
				# use DOF object distance if present or fixed DOF
				if (camProp["dof_object_focus"] and camProp["dof_object"]):
					# use DOF object distance
					DOFobj = Object.Get(camProp["dof_object"])
					dof_distance = math.sqrt(math.pow(DOFobj.mat[3][0]-camObj.mat[3][0],2) +
							math.pow(DOFobj.mat[3][1]-camObj.mat[3][1],2) +
							math.pow(DOFobj.mat[3][2]-camObj.mat[3][2],2))
				else:
					# use fixed DOF distance
					dof_distance = camProp["dof_distance"]

				yi.paramsSetFloat("dof_distance", dof_distance)
				yi.paramsSetFloat("aperture", camProp["aperture"])
				# bokeh params
				yi.paramsSetString("bokeh_type", camProp["bokeh_type"])
				yi.paramsSetFloat("bokeh_rotation", camProp["bokeh_rotation"])
			elif camType == "angular":
				yi.paramsSetString("type", "angular");
				yi.paramsSetBool("circular", camProp["circular"])
				yi.paramsSetBool("mirrored", camProp["mirrored"])
				yi.paramsSetFloat("max_angle", camProp["max_angle"])
				yi.paramsSetFloat("angle", camProp["angle"])
		
		yi.paramsSetInt("resx", int(renderData.sizeX * renderData.renderwinSize / 100.0))
		yi.paramsSetInt("resy", int(renderData.sizeY * renderData.renderwinSize / 100.0))
		#yi.paramsSetFloat("aspect_ratio", re->ycor);

		yi.paramsSetPoint("from", pos[0], pos[1], pos[2])
		yi.paramsSetPoint("up", pos[0] + up[0], pos[1] + up[1], pos[2] + up[2])
		yi.paramsSetPoint("to", to[0], to[1], to[2])
		yi.createCamera("cam")


	# write the object using the given transformation matrix (for duplis)
	# if no matrix is given (usual case) use the object's matrix
	def writeObject(self, yi, obj, matrix = None):
		yi.printInfo("Exporter: Creatind Object: \"" + obj.getName() + "\"")

		# Generate unique object ID
		ID = yi.getNextFreeID()

		scene = Scene.GetCurrent()
		renderer = scene.properties["YafRay"]["Renderer"]

		isMeshlight = False
		isVolume = False
		isBGPL = False
		
		# Check if object has YafaRay properties
		try:
			objProp = obj.properties["YafRay"]
			isMeshlight = objProp["meshlight"]
			isVolume = objProp["volume"]
			isBGPL = objProp["bgPortalLight"]
		except:
			objProp = None

		# Export MeshLight material first if needed # TODO: move on yaf_export?
		if isMeshlight:
			ml_matname = "ML_"
			ml_matname += obj.name + "." + str(obj.__hash__())

			yi.paramsClearAll();
			yi.paramsSetString("type", "light_mat");
			yi.paramsSetBool("double_sided", objProp["double_sided"])
			c = objProp["color"];
			yi.paramsSetColor("color", c[0], c[1], c[2])
			yi.paramsSetFloat("power", objProp["power"])
			ml_mat = yi.createMaterial(ml_matname);

			self.materialMap[ml_matname] = ml_mat

			# Export mesh light
			yi.paramsClearAll()
			yi.paramsSetString("type", "meshlight")
			yi.paramsSetBool("double_sided", objProp["double_sided"])
			c = objProp["color"]
			yi.paramsSetColor("color", c[0], c[1], c[2])
			yi.paramsSetFloat("power", objProp["power"])
			yi.paramsSetInt("samples", objProp["samples"])
			yi.paramsSetInt("object", ID)
			yi.createLight(obj.name + "." + str(obj.__hash__()) + "." + str(ID))

		# Export BGPortalLight DT
		if isBGPL:
			yi.paramsClearAll()
			yi.paramsSetString("type", "bgPortalLight")
			yi.paramsSetFloat("power", objProp["bgp_power"])
			yi.paramsSetInt("samples", objProp["bgp_samples"])
			yi.paramsSetInt("object", ID)
			yi.paramsSetBool("with_caustic", objProp["with_caustic"])
			yi.paramsSetBool("with_diffuse", objProp["with_diffuse"])
			yi.paramsSetBool("photon_only", objProp["photon_only"])
			yi.createLight(obj.name + "." + str(obj.__hash__()) + "." + str(ID))

		# Object Material
		if isMeshlight:
			ymaterial = ml_mat
		else:
			if renderer["clayRender"] == True:
				ymaterial = self.materialMap["default"]
			elif obj.getType() == 'Curve':
				curve = obj.getData()
				if len(curve.getMaterials()) != 0:
					mat = curve.getMaterials()[0]
					ymaterial = self.materialMap[mat]
				else:
					ymaterial = self.materialMap["default"]
			else:
				if obj.getData().getMaterials():
					ymaterial = None
				else:
					ymaterial = self.materialMap["default"]


		# Check if the object has particles
		if (obj.getParticleSystems()):
			self.writeParticlesObject(yi, ID, obj, matrix, ymaterial)
		elif isVolume:
			self.writeVolumeObject(yi, ID, 0, obj, matrix, ymaterial, objProp)
		elif isBGPL:
			self.writeMeshObject(yi, ID, 0, obj, matrix, ymaterial, True)
		else:
			self.writeMeshObject(yi, ID, 0, obj, matrix, ymaterial)

	def writeParticlesObject(self, yi, ID, object, matrix = None, ymaterial = None):
		renderEmitter = False
		for pSys in object.getParticleSystems():
			if (pSys.drawAs == Blender.Particle.DRAWAS.PATH):
				# Export particles
				yi.printInfo("Exporter: Creating Particle System \"" + pSys.getName() + "\"")
				tstart = time.time()
				# get particles material (keeps particles thikness too)
				# TODO: clay particles uses at least materials thikness?
				if pSys.getMat():
					pmaterial = pSys.getMat()
					if pmaterial.strandBlendUnit:
						strandStart = pmaterial.strandStart
						strandEnd = pmaterial.strandEnd
						strandShape = pmaterial.strandShape
					else:
						# Blender unit conversion
						strandStart = pmaterial.strandStart/100
						strandEnd = pmaterial.strandEnd/100
						strandShape = pmaterial.strandShape
				else:
					# No material assigned in blender, use default one
					pmaterial = "default"
					strandStart = 0.01
					strandEnd = 0.01
					strandShape = 0.0
				# Workaround to API bug, getLoc() is empty for particles system > 1
				# (object has more than one particle system assigned)
				pSys.getLoc()
				# Workaround end
				for path in pSys.getLoc():
					CID = yi.getNextFreeID()
					yi.paramsClearAll()
					yi.startGeometry()
					yi.startCurveMesh(CID, len(path))
					for vertex in path:
						yi.addVertex(vertex[0], vertex[1], vertex[2])
					yi.endCurveMesh(self.materialMap[pmaterial], strandStart, strandEnd, strandShape)
					# TODO: keep object smooth
					#yi.smoothMesh(0, 60.0)
					yi.endGeometry()
				yi.printInfo("Exporter: Particle creation time: " + str(time.time()-tstart))
			if (pSys.renderEmitter):
				renderEmitter = True
		# We only need to render emitter object once
		if renderEmitter:
			#ID = yi.getNextFreeID()
			self.writeMeshObject(yi, ID, 1, object, matrix, ymaterial)


	def writeMeshObject(self, yi, ID, cage, object, matrix = None, ymaterial = None, invisible = False): #the last parameter makes the mesh invisible to the raytracer

		mesh = Mesh.New()
		mesh.getFromObject(object, cage, 1)

		isSmooth = False
		hasUV = mesh.faceUV
		hasOrco = False

		# Check if the object has an orco mapped texture
		for mat in mesh.materials:
			if mat == None: continue
			mtextures = mat.getTextures()
			if hasattr(mat, 'enabledTextures'):
				for m in mat.enabledTextures:
					if mtextures[m].texco == Blender.Texture.TexCo.ORCO:
						hasOrco = True
						break

		if hasOrco:
			# Keep a copy of the untransformed vertex and bring them
			# into a (-1 -1 -1) (1 1 1) bounding box
			ov = []
			bbMin, bbMax = getBBCorners(object)
			# print bbMin, bbMax
			delta = []
			for i in range(3):
				delta.append(bbMax[i] - bbMin[i])
				if delta[i] < 0.0001: delta[i] = 1
			# print "delta", delta
			for v in mesh.verts:
				normCo = []
				for i in range(3):
					normCo.append(2 * (v.co[i] - bbMin[i]) / delta[i] - 1)
				ov.append([normCo[0], normCo[1], normCo[2]])
		
		# Apply transformation matrix
		if matrix == None:
			mesh.transform(object.getMatrix())
		else:
			mesh.transform(matrix)

		# Export mesh
		yi.paramsClearAll()
		yi.startGeometry()
		
		obType = 0
		
		if invisible:
			obType = 256
		
		yi.startTriMesh(ID, len(mesh.verts), len(mesh.faces), hasOrco, hasUV, obType)
		
		ind = 0
		for v in mesh.verts:
			if hasOrco:
				yi.addVertex(v.co[0], v.co[1], v.co[2],ov[ind][0], ov[ind][1], ov[ind][2] )
				ind += 1
			else:
				yi.addVertex(v.co[0], v.co[1], v.co[2])

		for f in mesh.faces:
			if f.smooth == True:
				isSmooth = True

			# get the face material if none is provided to override
			if ymaterial == None:
				mat = mesh.materials[f.mat]
				if self.materialMap.has_key(mat):
					fmat = self.materialMap[mat]
				else:
					fmat = self.materialMap["default"]
			else:
				fmat = ymaterial

			if hasUV == True:
				uv0 = yi.addUV(f.uv[0][0], f.uv[0][1])
				uv1 = yi.addUV(f.uv[1][0], f.uv[1][1])
				uv2 = yi.addUV(f.uv[2][0], f.uv[2][1])
				yi.addTriangle(f.v[0].index, f.v[1].index, f.v[2].index, uv0, uv1, uv2, fmat)
			else:
				yi.addTriangle(f.v[0].index, f.v[1].index, f.v[2].index, fmat)

			if len(f) == 4:
				if hasUV == True:
					uv3 = yi.addUV(f.uv[3][0], f.uv[3][1])
					yi.addTriangle(f.v[2].index, f.v[3].index, f.v[0].index, uv2, uv3, uv0, fmat)
				else:
					yi.addTriangle(f.v[2].index, f.v[3].index, f.v[0].index, fmat)

		yi.endTriMesh()

		if isSmooth == True:
			if mesh.mode & Blender.Mesh.Modes.AUTOSMOOTH:
				yi.smoothMesh(0, mesh.degr)
			else:
				yi.smoothMesh(0, 181)

		yi.endGeometry()


	def writeVolumeObject(self, yi, ID, cage, object, matrix = None, ymaterial = None, objProp = None):
		scene = Scene.GetCurrent()

		# preset a default volume
		worldProp = {"attgridScale":    1}

		if scene.world:
			if scene.world.properties.has_key('YafRay'):
				worldProp = scene.world.properties["YafRay"]
		else:
			yi.printWarning("Exporter: No Volume Integrator defined, using default")
		
		mesh = Mesh.New()
		mesh.getFromObject(object, 0, 1)
		# Apply transformation matrix
		if matrix == None:
			mesh.transform(object.getMatrix())
		else:
			mesh.transform(matrix)
		
		yi.paramsClearAll()
		volregion_type = objProp["volregionType"]
		if "ExpDensityVolume" == volregion_type:
			yi.paramsSetString("type", "ExpDensityVolume");
			yi.paramsSetFloat("a", objProp["a"])
			yi.paramsSetFloat("b", objProp["b"])
		elif "UniformVolume" == volregion_type:
			yi.paramsSetString("type", "UniformVolume");
		elif "NoiseVolume" == volregion_type:
			if objProp["noise_tex"] == "":
				yi.printWarning("Exporter: No noise texture set on the object, NoiseVolume won't be created")
				return
			yi.paramsSetString("type", "NoiseVolume");
			yi.paramsSetFloat("sharpness", objProp["sharpness"])
			yi.paramsSetFloat("cover", objProp["cover"])
			yi.paramsSetFloat("density", objProp["density"])
			yi.paramsSetString("texture", objProp["noise_tex"])
		elif "GridVolume" == volregion_type:
			yi.paramsSetString("type", "GridVolume");
		elif "SkyVolume" == volregion_type:
			yi.paramsSetString("type", "SkyVolume");
		
		yi.paramsSetFloat("sigma_a", objProp["sigma_a"])
		yi.paramsSetFloat("sigma_s", objProp["sigma_s"])
		yi.paramsSetFloat("l_e", objProp["l_e"])
		yi.paramsSetFloat("g", objProp["g"])
		yi.paramsSetInt("attgridScale", worldProp["attgridScale"])
		# derive the AABB from the supplied mesh, find the max and
		# min of the mesh's geometry and use that for the AABB
		min = [1e10, 1e10, 1e10]
		max = [-1e10, -1e10, -1e10]
		for v in mesh.verts:
			vertLoc = v.co
			if vertLoc[0] < min[0]: min[0] = vertLoc[0]
			if vertLoc[1] < min[1]: min[1] = vertLoc[1]
			if vertLoc[2] < min[2]: min[2] = vertLoc[2]
			if vertLoc[0] > max[0]: max[0] = vertLoc[0]
			if vertLoc[1] > max[1]: max[1] = vertLoc[1]
			if vertLoc[2] > max[2]: max[2] = vertLoc[2]
		yi.paramsSetFloat("minX", min[0])
		yi.paramsSetFloat("minY", min[1])
		yi.paramsSetFloat("minZ", min[2])
		yi.paramsSetFloat("maxX", max[0])
		yi.paramsSetFloat("maxY", max[1])
		yi.paramsSetFloat("maxZ", max[2])
		yi.createVolumeRegion(object.name + "." + str(object.__hash__()) + "." + str(ID))
		return

