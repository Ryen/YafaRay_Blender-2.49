import Blender.Texture

# ------------------------------------------------------------------------
#
# Textures
#
# ------------------------------------------------------------------------

def noise2string(ntype):
	if ntype == Blender.Texture.Noise.BLENDER:			return "blender"
	elif ntype == Blender.Texture.Noise.PERLIN:			return "stdperlin"
	elif ntype == Blender.Texture.Noise.IMPROVEDPERLIN: return "newperlin"
	elif ntype == Blender.Texture.Noise.VORONOIF1:		return "voronoi_f1"
	elif ntype == Blender.Texture.Noise.VORONOIF2:		return "voronoi_f2"
	elif ntype == Blender.Texture.Noise.VORONOIF3:		return "voronoi_f3"
	elif ntype == Blender.Texture.Noise.VORONOIF4:		return "voronoi_f4"
	elif ntype == Blender.Texture.Noise.VORONOIF2F1:	return "voronoi_f2f1"
	elif ntype == Blender.Texture.Noise.VORONOICRACKLE:	return "voronoi_crackle"
	elif ntype == Blender.Texture.Noise.CELLNOISE:		return "cellnoise"
	return "newperlin"

class yafTexture:
	def __init__(self, interface):
		self.yi = interface
		
	def writeTexture(self, tex, name, gamma=1.8):
		yi = self.yi
		yi.paramsClearAll()
		
		nsz = tex.noiseSize
		if nsz > 0: nsz = 1.0/nsz
		hard = False
		if tex.noiseType == "hard": hard = True
		
		if tex.type == Blender.Texture.Types.CLOUDS:
			print "INFO: Adding Texture:",name,"type CLOUDS"
			yi.paramsSetString("type", "clouds")
			yi.paramsSetFloat("size", nsz)
			yi.paramsSetBool("hard", hard)
			yi.paramsSetInt("depth", tex.noiseDepth)
			#yi.paramsSetInt("color_type", tex->stype); # unused?
			yi.paramsSetString("noise_type", noise2string(tex.noiseBasis))
		elif tex.type == Blender.Texture.Types.WOOD:
			print "INFO: Adding Texture:",name,"type WOOD"
			yi.paramsSetString("type", "wood")
			# blender does not use depth value for wood, always 0
			yi.paramsSetInt("depth", 0)
			turb = 0.0
			if tex.stype >= 2: turb = tex.turbulence
			yi.paramsSetFloat("turbulence", turb)
			yi.paramsSetFloat("size", nsz)
			yi.paramsSetBool("hard", hard )
			ts = "bands"
			if tex.stype == Blender.Texture.STypes.WOD_RINGS or tex.stype == Blender.Texture.STypes.WOD_RINGNOISE:
				ts = "rings"
			yi.paramsSetString("wood_type", ts )
			yi.paramsSetString("noise_type", noise2string(tex.noiseBasis))
			# shape parameter, for some reason noisebasis2 is used...
			ts = "sin"
			if tex.noiseBasis2==1: ts="saw"
			elif tex.noiseBasis2==2: ts="tri"
			yi.paramsSetString("shape", ts )
		elif tex.type == Blender.Texture.Types.MARBLE:
			print "INFO: Adding Texture:",name,"type MARBLE"
			yi.paramsSetString("type", "marble")
			yi.paramsSetInt("depth", tex.noiseDepth)
			yi.paramsSetFloat("turbulence", tex.turbulence)
			yi.paramsSetFloat("size", nsz)
			yi.paramsSetBool("hard", hard )
			yi.paramsSetFloat("sharpness", float(1<<tex.stype))
			yi.paramsSetString("noise_type", noise2string(tex.noiseBasis))
			ts = "sin"
			if tex.noiseBasis2==1: ts="saw"
			elif tex.noiseBasis2==2: ts="tri"
			yi.paramsSetString("shape", ts)
		elif tex.type == Blender.Texture.Types.VORONOI:
			print "INFO: Adding Texture:",name,"type VORONOI"
			yi.paramsSetString("type", "voronoi")
			ts = "int"
			# vn_coltype not available in python, but types are listed for STypes, so it's a guess!
			if tex.stype == Blender.Texture.STypes.VN_COL1:		ts = "col1" 
			elif tex.stype == Blender.Texture.STypes.VN_COL2:	ts = "col2"
			elif tex.stype == Blender.Texture.STypes.VN_COL3:	ts = "col3"
			yi.paramsSetString("color_type", ts)
			yi.paramsSetFloat("weight1", tex.weight1)
			yi.paramsSetFloat("weight2", tex.weight2)
			yi.paramsSetFloat("weight3", tex.weight3)
			yi.paramsSetFloat("weight4", tex.weight4)
			yi.paramsSetFloat("mk_exponent", tex.exp)
			yi.paramsSetFloat("intensity", tex.iScale)
			yi.paramsSetFloat("size", nsz)
			ts = "actual"
			if tex.distMetric == 1: 	ts = "squared"
			elif tex.distMetric == 2:	ts = "manhattan"
			elif tex.distMetric == 3:	ts = "chebychev"
			elif tex.distMetric == 4:	ts = "minkovsky_half"
			elif tex.distMetric == 5:	ts = "minkovsky_four"
			elif tex.distMetric == 6:	ts = "minkovsky"
			yi.paramsSetString("distance_metric", ts)
		elif tex.type == Blender.Texture.Types.MUSGRAVE:
			print "INFO: Adding Texture:",name,"type MUSGRAVE"
			yi.paramsSetString("type", "musgrave")
			ts = "fBm"
			if tex.stype == Blender.Texture.STypes.MUS_MFRACTAL:
				ts = "multifractal"
			elif tex.stype == Blender.Texture.STypes.MUS_RIDGEDMF:
				ts = "ridgedmf"
			elif tex.stype == Blender.Texture.STypes.MUS_HYBRIDMF:
				ts = "hybridmf"
			elif tex.stype == Blender.Texture.STypes.MUS_HYBRIDMF:
				ts = "heteroterrain"
			yi.paramsSetString("musgrave_type", ts)
			yi.paramsSetString("noise_type", noise2string(tex.noiseBasis))
			yi.paramsSetFloat("H", tex.hFracDim)
			yi.paramsSetFloat("lacunarity", tex.lacunarity)
			yi.paramsSetFloat("octaves", tex.octs)
		# can't find these values in Python API docs...
		#	if ((tex->stype==TEX_HTERRAIN) || (tex->stype==TEX_RIDGEDMF) || (tex->stype==TEX_HYBRIDMF)) {
		#		yG->paramsSetFloat("offset", tex->mg_offset);
		#		if ((tex->stype==TEX_RIDGEDMF) || (tex->stype==TEX_HYBRIDMF))
		#			yG->paramsSetFloat("gain", tex->mg_gain);
		#	}
			yi.paramsSetFloat("size", nsz)
			yi.paramsSetFloat("intensity", tex.iScale)
		elif tex.type == Blender.Texture.Types.DISTNOISE:
			print "INFO: Adding Texture:",name,"type DISTORTED NOISE"
			yi.paramsSetString("type", "distorted_noise")
			yi.paramsSetFloat("distort", tex.distAmnt)
			yi.paramsSetFloat("size", nsz)
			yi.paramsSetString("noise_type1", noise2string(tex.noiseBasis))
			yi.paramsSetString("noise_type2", noise2string(tex.noiseBasis2))
		elif tex.type == Blender.Texture.Types.IMAGE:
			ima = tex.getImage()
			if ima != None:
				print "INFO: Adding Texture:",name,"type IMAGE:",ima.getFilename()
				# remember image to avoid duplicates later if also in imagetex
				# (formerly done by removing from imagetex, but need image/material link)
				#	dupimg.insert(ima);
				yi.paramsSetString("type", "image")
				yi.paramsSetString("filename", Blender.sys.expandpath(ima.getFilename()) )
			#	yG->paramsSetString("interpolate", (tex->imaflag & TEX_INTERPOL) ? "bilinear" : "none");
				yi.paramsSetFloat("gamma", gamma)
				yi.paramsSetBool("use_alpha", tex.useAlpha > 0)
				yi.paramsSetBool("calc_alpha", tex.calcAlpha > 0)
				yi.paramsSetBool("normalmap", tex.normalMap > 0)
						
				# repeat
				yi.paramsSetInt("xrepeat", tex.repeat[0])
				yi.paramsSetInt("yrepeat", tex.repeat[1])
						
				# clipping
				ext = tex.extend
				
				#print tex.getExtend()
				if ext == Blender.Texture.ExtendModes.EXTEND: yi.paramsSetString("clipping", "extend")
				elif ext == Blender.Texture.ExtendModes.CLIP:	yi.paramsSetString("clipping", "clip")
				elif ext == Blender.Texture.ExtendModes.CLIPCUBE:	yi.paramsSetString("clipping", "clipcube")
				elif tex.getExtend() == "Checker": #Blender.Texture.ExtendModes.CHECKER:
					yi.paramsSetString("clipping", "checker")
					yi.paramsSetBool("even_tiles", tex.flags & Blender.Texture.Flags.CHECKER_EVEN)
					yi.paramsSetBool("odd_tiles", tex.flags & Blender.Texture.Flags.CHECKER_ODD)
				else: yi.paramsSetString("clipping", "repeat")
				
				# crop min/max
				yi.paramsSetFloat("cropmin_x", tex.crop[0])
				yi.paramsSetFloat("cropmin_y", tex.crop[1]) # no idea of order in tupel :(
				yi.paramsSetFloat("cropmax_x", tex.crop[2])
				yi.paramsSetFloat("cropmax_y", tex.crop[3])
				
				# rot90 flag
				if tex.rot90 != 0:
					yi.paramsSetBool("rot90", True)
		
		yi.createTexture(name)
	
