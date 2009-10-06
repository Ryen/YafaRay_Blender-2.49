import yafrayinterface

import Blender
from Blender import *
from Blender import Mathutils
from Blender.Mathutils import *

def getProperty(property, name):
	print "INFO: getting ", name, " out of ", property
	if name in property:
		return property[name]

def getBBCorners(mesh):
	bb = mesh.getBoundBox(0)
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
		print "INFO: Exporting Camera"

		renderData = scene.getRenderingContext()

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

		camProp = camObj.properties["YafRay"]

		if useView:
			yi.paramsSetString("type", "perspective");
		else:
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
				
				# dof params, only valid for real camera
				yi.paramsSetFloat("dof_distance", camProp["dof_distance"])
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
		print "INFO: Exporting Object: " + obj.getName()
		yi.paramsClearAll()

		objProp = obj.properties["YafRay"]

		scene = Scene.GetCurrent()
		renderer = scene.properties["YafRay"]["Renderer"]
		worldProp = scene.world.properties["YafRay"]

		mesh = Mesh.New()
		mesh.getFromObject(obj, 0, 1)

		# CHECK if the object has an orco mapped texture
		hasOrco = False
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
			bbMin, bbMax = getBBCorners(obj)
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

		if matrix == None:
			mesh.transform(obj.getMatrix())
		else:
			mesh.transform(matrix)

		hasUV = mesh.faceUV

		ID = yafrayinterface.new_uintp()
		ID_val = yafrayinterface.uintp_value(ID)

		smooth = False

		meshlight = objProp["meshlight"]
		if meshlight:
			# add mesh light material
			yi.paramsClearAll();
			yi.paramsSetString("type", "light_mat");
			yi.paramsSetBool("double_sided", objProp["double_sided"])
			c = objProp["color"];
			yi.paramsSetColor("color", c[0], c[1], c[2])
			yi.paramsSetFloat("power", objProp["power"])
			ml_matname = "ML_"
			ml_matname += obj.name
			ml_mat = yi.createMaterial(ml_matname);
			yi.paramsClearAll()


		isVolume = objProp["volume"]
		if isVolume:
			yi.paramsClearAll();

			volregion_type = objProp["volregionType"]
			if "ExpDensityVolume" == volregion_type:
				yi.paramsSetString("type", "ExpDensityVolume");
				yi.paramsSetFloat("a", objProp["a"])
				yi.paramsSetFloat("b", objProp["b"])
			elif "UniformVolume" == volregion_type:
				yi.paramsSetString("type", "UniformVolume");
			elif "NoiseVolume" == volregion_type:
				yi.paramsSetString("type", "NoiseVolume");
				yi.paramsSetFloat("sharpness", objProp["sharpness"])
				yi.paramsSetFloat("cover", objProp["cover"])
				yi.paramsSetFloat("density", objProp["density"])
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
			yi.createVolumeRegion(obj.name)
			yi.paramsClearAll()
			return;

		yi.startGeometry()
		yi.startTriMeshPtr(ID, len(mesh.verts), len(mesh.faces), hasOrco, hasUV, 0)
		ind = 0
		for v in mesh.verts:
			if hasOrco:
				yi.addVertex(v.co[0], v.co[1], v.co[2],ov[ind][0], ov[ind][1], ov[ind][2] )
				ind += 1
			else:
				yi.addVertex(v.co[0], v.co[1], v.co[2])

		for f in mesh.faces:
			if f.smooth == True:
				smooth = True

			if meshlight: ymat = ml_mat
			else:
				if renderer["clayRender"] == True:
					ymat = self.materialMap["default"]
				elif obj.getType() == 'Curve':
					curve = obj.getData()
					smooth = True
					if len(curve.getMaterials()) != 0:
						mat = curve.getMaterials()[0]
						if mat in self.materialMap:
							ymat = self.materialMap[mat]
					else:
						ymat = self.materialMap["default"]
				elif len(mesh.materials) != 0:
					mat = mesh.materials[f.mat]
					if mat in self.materialMap:
						ymat = self.materialMap[mat]
					else:
						ymat = self.materialMap["default"]
				else:
					ymat = self.materialMap["default"]

			if hasUV == True:
				uv0 = yi.addUV(f.uv[0][0], f.uv[0][1])
				uv1 = yi.addUV(f.uv[1][0], f.uv[1][1])
				uv2 = yi.addUV(f.uv[2][0], f.uv[2][1])
				yi.addTriangle(f.v[0].index, f.v[1].index, f.v[2].index, uv0, uv1, uv2, ymat)
			else:
				yi.addTriangle(f.v[0].index, f.v[1].index, f.v[2].index, ymat)

			if len(f) == 4:
				if hasUV == True:
					uv3 = yi.addUV(f.uv[3][0], f.uv[3][1])
					yi.addTriangle(f.v[2].index, f.v[3].index, f.v[0].index, uv2, uv3, uv0, ymat)
				else:
					yi.addTriangle(f.v[2].index, f.v[3].index, f.v[0].index, ymat)

		yi.endTriMesh()

		if smooth == True:
			if mesh.mode & Blender.Mesh.Modes.AUTOSMOOTH:
				yi.smoothMesh(0, mesh.degr)
			else:
				yi.smoothMesh(0, 181)

		yi.endGeometry()

		if meshlight:
			# add mesh light
			yi.paramsClearAll()
			yi.paramsSetString("type", "meshlight")
			yi.paramsSetBool("double_sided", objProp["double_sided"])
			c = objProp["color"]
			yi.paramsSetColor("color", c[0], c[1], c[2])
			yi.paramsSetFloat("power", objProp["power"])
			yi.paramsSetInt("samples", objProp["samples"])
			yi.paramsSetInt("object", yafrayinterface.uintp_value(ID))
			yi.createLight(obj.name)
			yi.paramsClearAll()

