#!BPY

import yafrayinterface

import math
from math import *

import Blender
from Blender import *
from Blender.Mathutils import *
import time



class yafLight:
	def __init__(self, interface, iesPath):
		self.yi = interface
		self.iesPath = iesPath

	def makeSphere(self, nu, nv, x, y, z, rad, mat):
		yi = self.yi

		ID = yafrayinterface.new_uintp()

		yi.startGeometry();

		if not yi.startTriMeshPtr(ID, 2+(nu-1)*nv, 2*(nu-1)*nv, False, False):
			print "error on starting trimesh!\n"

		yi.addVertex(x, y, z+rad);
		yi.addVertex(x, y, z-rad);
		for v in range(0, nv):
			t = v/float(nv)
			sin_v = sin(2.0*pi*t)
			cos_v = cos(2.0*pi*t)
			for u in range(1, nu):
				s = u/float(nu);
				sin_u = sin(pi*s)
				cos_u = cos(pi*s)
				yi.addVertex(x + cos_v*sin_u*rad, y + sin_v*sin_u*rad, z + cos_u*rad)

		for v in range(0, nv):
			yi.addTriangle( 0, 2+v*(nu-1), 2+((v+1)%nv)*(nu-1), mat );
			yi.addTriangle( 1, ((v+1)%nv)*(nu-1)+nu, v*(nu-1)+nu, mat );
			for u in range(0, nu-2):
				yi.addTriangle( 2+v*(nu-1)+u, 2+v*(nu-1)+u+1, 2+((v+1)%nv)*(nu-1)+u, mat );
				yi.addTriangle( 2+v*(nu-1)+u+1, 2+((v+1)%nv)*(nu-1)+u+1, 2+((v+1)%nv)*(nu-1)+u, mat );

		yi.endTriMesh();
		yi.endGeometry();
		return yafrayinterface.uintp_value(ID)


	def createLight(self, yi, obj, matrix = None, lamp_mat = None,  dupliNum = None):
		name = obj.name
		if dupliNum != None:
			name += str(dupliNum)
		if matrix == None:
			matrix = obj.getMatrix()
		pos = matrix[3]
		dir = matrix[2]
		up = matrix[1]
		to = [pos[0] - dir[0], pos[1] - dir[1], pos[2] - dir[2]]

		yi.paramsClearAll()
		props = obj.properties["YafRay"]
		lampType = props["type"]
		power = props["power"]
		color = props["color"]

		print "INFO: Adding Lamp:", name, " type: ", lampType
		if lampType == "Point":
			yi.paramsSetString("type", "pointlight")
			power = 0.5 * power * power

		elif lampType == "Sphere":
			radius = props["radius"]
			power = 0.5*power*power/(radius * radius)
			if props["createGeometry"] == True:
				ID = self.makeSphere(24, 48, pos[0], pos[1], pos[2], radius, lamp_mat)
				yi.paramsSetInt("object", ID)

			yi.paramsSetString("type", "spherelight")
			yi.paramsSetInt("samples", props["samples"])
			yi.paramsSetFloat("radius", radius)

		elif lampType == "Spot":
			light = obj.getData()
			yi.paramsSetString("type", "spotlight")
			#print "spot ", light.getSpotSize()
			yi.paramsSetFloat("cone_angle", light.getSpotSize() / 2)
			yi.paramsSetFloat("blend", light.getSpotBlend())
			yi.paramsSetPoint("to", to[0], to[1], to[2])
			yi.paramsSetBool("soft_shadows", props["SpotSoftShadows"])
			yi.paramsSetBool("photon_only", props["SpotPhotonOnly"])
			yi.paramsSetInt("samples", props["SpotSamples"])
			power = 0.5*power*power

		elif lampType == "IES Light":
			light = obj.getData()
			yi.paramsSetString("type", "ieslight")
			yi.paramsSetPoint("to", to[0], to[1], to[2])
			file = self.iesPath + props["iesfile"] + ".IES";
			import os;
			if not os.path.exists(file):
				file = self.iesPath + props["iesfile"] + ".ies";
			yi.paramsSetString("file", file)
			yi.paramsSetFloat("blurStrength", props["iesBlurStrength"])
			yi.paramsSetInt("resolution", props["iesBlurResolution"])
			yi.paramsSetInt("samples", props["iesSamples"])
			yi.paramsSetBool("soft_shadows", props["iesSoftShadows"])
			yi.paramsSetFloat("cone_angle", light.getSpotSize() / 2)
			power = 0.5*power*power

		elif lampType == "Sun":
			yi.paramsSetString("type", "sunlight")
			yi.paramsSetInt("samples", props["samples"])
			yi.paramsSetFloat("angle", props["angle"])
			yi.paramsSetPoint("direction", dir[0], dir[1], dir[2])

		elif lampType == "Directional":
			yi.paramsSetString("type", "directional")
			#if props["infinite"] == True:
			yi.paramsSetBool("infinite", props["infinite"])
			yi.paramsSetFloat("radius", props["radius"])
			yi.paramsSetPoint("direction", dir[0], dir[1], dir[2])

		elif lampType == "Area":
			yi.paramsSetString("type", "arealight")
			areaLight = obj.getData()
			sizeX = areaLight.getAreaSizeX()
			#sizeY = areaLight.getAreaSizeY()
			sizeY = sizeX

			matrix = matrix.__copy__()
			matrix.transpose()

			# generate an untransformed rectangle in the XY plane with
			# the light's position as the centerpoint and transform it
			# using its transformation matrix

			point = Vector(-sizeX/2, -sizeY/2, 0, 1)
			corner1 = Vector(-sizeX/2, sizeY/2, 0, 1)
			corner2 = Vector(sizeX/2, sizeY/2, 0, 1)
			corner3 = Vector(sizeX/2, -sizeY/2, 0, 1)
			point = matrix * point
			corner1 = matrix * corner1
			corner2 = matrix * corner2
			corner3 = matrix * corner3
			#print "point: ", point, corner1, corner2, corner3

			if props["createGeometry"] == True:
				ID = yafrayinterface.new_uintp()
				yi.startGeometry();
				yi.startTriMesh(ID, 4, 2, False, False);

				idx1 = yi.addVertex(point[0], point[1], point[2]);
				idx2 = yi.addVertex(corner1[0], corner1[1], corner1[2]);
				idx3 = yi.addVertex(corner2[0], corner2[1], corner2[2]);
				idx4 = yi.addVertex(corner3[0], corner3[1], corner3[2]);
				yi.addTriangle(idx1, idx2, idx3, lamp_mat);
				yi.addTriangle(idx1, idx3, idx4, lamp_mat);
				yi.endTriMesh();
				yi.endGeometry();
				yi.paramsSetInt("object", yafrayinterface.uintp_value(ID));

			yi.paramsClearAll();
			yi.paramsSetString("type", "arealight");
			yi.paramsSetInt("samples", props["samples"])
			
			yi.paramsSetPoint("corner", point[0], point[1], point[2]);
			yi.paramsSetPoint("point1", corner1[0], corner1[1], corner1[2]);
			yi.paramsSetPoint("point2", corner3[0], corner3[1], corner3[2]);


		yi.paramsSetPoint("from", pos[0], pos[1], pos[2])
		yi.paramsSetColor("color", color[0], color[1], color[2])
		yi.paramsSetFloat("power", power)

		
		yi.createLight(name)

