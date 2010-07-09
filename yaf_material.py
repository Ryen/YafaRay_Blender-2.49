import Blender.Texture
import yafrayinterface
# ------------------------------------------------------------------------
#
# Materials
#
# ------------------------------------------------------------------------

def proj2int(val):
	if val == Blender.Texture.Proj.NONE: return 0
	elif val == Blender.Texture.Proj.X: return 1
	elif val == Blender.Texture.Proj.Y: return 2
	elif val == Blender.Texture.Proj.Z: return 3

class yafMaterial:
	def __init__(self, interface, mMap):
		self.yi = interface
		self.materialMap = mMap

	def namehash(self,obj):
		# TODO: Better hashing using mat.__str__() ?
		nh = obj.name + "." + str(obj.__hash__())
		return nh
	
	def writeTexLayer(self, name, tex_in, ulayer, mtex, chanflag, dcol):
		if chanflag == 0:
			return False
		yi = self.yi
		yi.paramsPushList()
		yi.paramsSetString("element", "shader_node")
		yi.paramsSetString("type", "layer")
		yi.paramsSetString("name", name)
		
		yi.paramsSetString("input", tex_in)
		# enum mix_modes{ MN_MIX=0, MN_ADD, MN_MULT, MN_SUB, MN_SCREEN, MN_DIV, MN_DIFF, MN_DARK, MN_LIGHT, MN_OVERLAY };
		# better solution would be to access this enum directly, in case
		# it is ever changed
		mode = 0
		if mtex.blendmode == Blender.Texture.BlendModes.MIX:
			mode = 0
		elif mtex.blendmode == Blender.Texture.BlendModes.ADD:
			mode = 1
		elif mtex.blendmode == Blender.Texture.BlendModes.MULTIPLY:
			mode = 2
		elif mtex.blendmode == Blender.Texture.BlendModes.SUBTRACT:
			mode = 3
		elif mtex.blendmode == Blender.Texture.BlendModes.SCREEN:
			mode = 4
		elif mtex.blendmode == Blender.Texture.BlendModes.DIVIDE:
			mode = 5
		elif mtex.blendmode == Blender.Texture.BlendModes.DIFFERENCE:
			mode = 6
		elif mtex.blendmode == Blender.Texture.BlendModes.DARKEN:
			mode = 7
		elif mtex.blendmode == Blender.Texture.BlendModes.LIGHTEN:
			mode = 8
		yi.paramsSetInt("mode", mode)
		yi.paramsSetBool("stencil", mtex.stencil)
		negative = chanflag < 0
		if mtex.neg: negative = not negative
		yi.paramsSetBool("negative", negative)
		yi.paramsSetBool("noRGB", mtex.noRGB)
		
		yi.paramsSetColor("def_col", mtex.col[0], mtex.col[1], mtex.col[2])
		yi.paramsSetFloat("def_val", mtex.dvar)
		yi.paramsSetFloat("colfac", mtex.colfac)
		yi.paramsSetFloat("valfac", mtex.varfac)
		
		tex = mtex.tex
		# lots to do...
		isImage = (tex.type == Blender.Texture.Types.IMAGE)
		if (isImage or (tex.type == Blender.Texture.Types.VORONOI and tex.stype != Blender.Texture.STypes.VN_INT)):
			isColored=True
		else:
			isColored=False
		useAlpha = False
		yi.paramsSetBool("color_input", isColored)
		if isImage: useAlpha = (tex.imageFlags & Blender.Texture.ImageFlags.USEALPHA) and not(tex.imageFlags & Blender.Texture.ImageFlags.CALCALPHA)
		yi.paramsSetBool("use_alpha", useAlpha)
		
		doCol = len(dcol) >= 3
		if ulayer == "":
			if doCol:
				yi.paramsSetColor("upper_color", dcol[0],dcol[1],dcol[2])
				yi.paramsSetFloat("upper_value", 0)
			else:
				yi.paramsSetColor("upper_color", 0,0,0)
				yi.paramsSetFloat("upper_value", dcol[0])
		else:
			yi.paramsSetString("upper_layer", ulayer)
		
		yi.paramsSetBool("do_color", doCol)
		yi.paramsSetBool("do_scalar", not doCol)
		
		return True



	def writeMappingNode(self, name, texname, mtex):
		yi = self.yi
		yi.paramsPushList()
		
		yi.paramsSetString("element", "shader_node")
		yi.paramsSetString("type", "texture_mapper")
		yi.paramsSetString("name", name)
		yi.paramsSetString("texture", self.namehash(mtex.tex))
		
		# texture coordinates, have to disable 'sticky' in Blender
		if mtex.texco == Blender.Texture.TexCo.UV:		yi.paramsSetString("texco", "uv")
		elif mtex.texco == Blender.Texture.TexCo.GLOB:		yi.paramsSetString("texco", "global")
		elif mtex.texco == Blender.Texture.TexCo.ORCO:  	yi.paramsSetString("texco", "orco")
		elif mtex.texco == Blender.Texture.TexCo.WIN:		yi.paramsSetString("texco", "window")
		elif mtex.texco == Blender.Texture.TexCo.NOR:		yi.paramsSetString("texco", "normal")
		elif mtex.texco == Blender.Texture.TexCo.REFL:		yi.paramsSetString("texco", "reflect")
		elif mtex.texco == Blender.Texture.TexCo.STICK:		yi.paramsSetString("texco", "stick")
		elif mtex.texco == Blender.Texture.TexCo.STRESS:	yi.paramsSetString("texco", "stress")
		elif mtex.texco == Blender.Texture.TexCo.TANGENT:	yi.paramsSetString("texco", "tangent")
		elif mtex.texco == Blender.Texture.TexCo.OBJECT:
			yi.paramsSetString("texco", "transformed")
			if mtex.object != None:
				texmat = mtex.object.getInverseMatrix()
				rtmatrix = yafrayinterface.new_floatArray(4*4)
				for x in range(4):
					for y in range(4):
						idx = (y + x * 4)
						yafrayinterface.floatArray_setitem(rtmatrix, idx, texmat[x][y])		
				yi.paramsSetMemMatrix("transform", rtmatrix, True)
				yafrayinterface.delete_floatArray(rtmatrix)
		
		yi.paramsSetInt("proj_x", proj2int(mtex.xproj))
		yi.paramsSetInt("proj_y", proj2int(mtex.yproj))
		yi.paramsSetInt("proj_z", proj2int(mtex.zproj))
		# allow mapping with procedurals too, i don't see why i shouldn't...
		if   mtex.mapping == Blender.Texture.Mappings.FLAT: yi.paramsSetString("mapping", "plain")
		elif mtex.mapping == Blender.Texture.Mappings.CUBE: yi.paramsSetString("mapping", "cube")
		elif mtex.mapping == Blender.Texture.Mappings.TUBE: yi.paramsSetString("mapping", "tube")
		elif mtex.mapping == Blender.Texture.Mappings.SPHERE: yi.paramsSetString("mapping", "sphere")
		
		yi.paramsSetPoint("offset", mtex.ofs[0], mtex.ofs[1], mtex.ofs[2])
		yi.paramsSetPoint("scale", mtex.size[0], mtex.size[1], mtex.size[2])
		
		if mtex.mapto == Blender.Texture.MapTo.NOR: #|| mtex->maptoneg & MAP_NORM )
			nf = mtex.norfac
			yi.paramsSetFloat("bump_strength", nf)


	def writeGlassShader(self, mat, rough):
		yi = self.yi
		yi.paramsClearAll()
		props = mat.properties["YafRay"]
		
		if rough:
			yi.paramsSetString("type", "rough_glass")
			yi.paramsSetFloat("exponent", props["exponent"])
			yi.paramsSetFloat("alpha", props["alpha"])
		else:
			yi.paramsSetString("type", "glass")
			
		yi.paramsSetFloat("IOR", props["IOR"])
		filt_col = props["filter_color"]
		mir_col = props["mirror_color"]
		tfilt = props["transmit_filter"]
		
		yi.paramsSetColor("filter_color", filt_col[0], filt_col[1], filt_col[2])
		yi.paramsSetColor("mirror_color", mir_col[0], mir_col[1], mir_col[2])
		yi.paramsSetFloat("transmit_filter", tfilt)
		yi.paramsSetColor("absorption", props["absorption"][0],
			 props["absorption"][1],
			 props["absorption"][2])
		yi.paramsSetFloat("absorption_dist", props["absorption_dist"])
		yi.paramsSetFloat("dispersion_power", props["dispersion_power"])
		yi.paramsSetBool("fake_shadows", props["fake_shadows"])
		
		mcolRoot = ''
		fcolRoot = ''
		bumpRoot = ''
		
		i=0
		mtextures = mat.getTextures()

		if hasattr(mat, 'enabledTextures'):
			used_mtextures = []
			used_idx = mat.enabledTextures
			for m in used_idx:
				mtex = mtextures[m]
				used_mtextures.append(mtex)
		else:
			used_mtextures = mtextures

		for mtex in used_mtextures:
			if mtex == None: continue
			if mtex.tex == None: continue
			
			used = False
			mappername = "map%x" %i
			
			lname = "mircol_layer%x" % i
			if self.writeTexLayer(lname, mappername, mcolRoot, mtex, mtex.mtCmir, mir_col):
				used = True
				mcolRoot = lname
			lname = "filtcol_layer%x" % i
			if self.writeTexLayer(lname, mappername, fcolRoot, mtex, mtex.mtCol, filt_col):
				used = True
				fcolRoot = lname
			lname = "bump_layer%x" % i
			if self.writeTexLayer(lname, mappername, bumpRoot, mtex, mtex.mtNor, [0]):
				used = True
				bumpRoot = lname
			if used:
				self.writeMappingNode(mappername, self.namehash(mtex.tex), mtex)
			i +=1
		
		yi.paramsEndList()
		if len(mcolRoot) > 0:	yi.paramsSetString("mirror_color_shader", mcolRoot)
		if len(fcolRoot) > 0:	yi.paramsSetString("filter_color_shader", fcolRoot)
		if len(bumpRoot) > 0:	yi.paramsSetString("bump_shader", bumpRoot)
		
		
		ymat = yi.createMaterial(self.namehash(mat))
		self.materialMap[mat] = ymat

	def writeGlossyShader(self, mat, coated):
		yi = self.yi
		yi.paramsClearAll()
		props = mat.properties["YafRay"]
		if coated:
			yi.paramsSetString("type", "coated_glossy")
			yi.paramsSetFloat("IOR", props["IOR"])
		else:
			yi.paramsSetString("type", "glossy")
		
		diffuse_color = props["diffuse_color"]
		color = props["color"]
		#glossy_reflect = props["glossy_reflect"]

		# TODO: textures

		
		yi.paramsSetColor("diffuse_color", diffuse_color[0], diffuse_color[1], diffuse_color[2])
		yi.paramsSetColor("color", color[0],color[1], color[2])
		yi.paramsSetFloat("glossy_reflect", props["glossy_reflect"])
		yi.paramsSetFloat("exponent", props["exponent"])
		yi.paramsSetFloat("diffuse_reflect", props["diffuse_reflect"])
		yi.paramsSetBool("as_diffuse", props["as_diffuse"])

		yi.paramsSetBool("anisotropic", props["anisotropic"])
		yi.paramsSetFloat("exp_u", props["exp_u"])
		yi.paramsSetFloat("exp_v", props["exp_v"])
		
		diffRoot = ''
		mcolRoot = ''
		glossRoot = ''
		glRefRoot = ''
		bumpRoot = ''
		
		i=0
		mtextures = mat.getTextures()

		if hasattr(mat, 'enabledTextures'):
			used_mtextures = []
			used_idx = mat.enabledTextures
			for m in used_idx:
				mtex = mtextures[m]
				used_mtextures.append(mtex)
		else:
			used_mtextures = mtextures

		for mtex in used_mtextures:
			if mtex == None: continue
			if mtex.tex == None: continue
			
			used = False
			mappername = "map%x" %i
			
			lname = "diff_layer%x" % i
			if self.writeTexLayer(lname, mappername, diffRoot, mtex, mtex.mtCol, diffuse_color):
				used = True
				diffRoot = lname
			lname = "gloss_layer%x" % i
			if self.writeTexLayer(lname, mappername, glossRoot, mtex, mtex.mtCsp, color):
				used = True
				glossRoot = lname
			lname = "glossref_layer%x" % i
			if self.writeTexLayer(lname, mappername, glRefRoot, mtex, mtex.mtSpec, [props["glossy_reflect"]]):
				used = True
				glRefRoot = lname
			lname = "bump_layer%x" % i
			if self.writeTexLayer(lname, mappername, bumpRoot, mtex, mtex.mtNor, [0]):
				used = True
				bumpRoot = lname
			if used:
				self.writeMappingNode(mappername, self.namehash(mtex.tex), mtex)
			i +=1
		
		yi.paramsEndList()
		if len(diffRoot) > 0:	yi.paramsSetString("diffuse_shader", diffRoot)
		if len(glossRoot) > 0:	yi.paramsSetString("glossy_shader", glossRoot)
		if len(glRefRoot) > 0:	yi.paramsSetString("glossy_reflect_shader", glRefRoot)
		if len(bumpRoot) > 0:	yi.paramsSetString("bump_shader", bumpRoot)

		yi.paramsSetString("diffuse_brdf", props["brdfType"])
		yi.paramsSetFloat("sigma", props["sigma"])
		
		ymat = yi.createMaterial(self.namehash(mat))
		self.materialMap[mat] = ymat

	def writeShinyDiffuseShader(self, mat):
		yi = self.yi
		yi.paramsClearAll()
		props = mat.properties["YafRay"]
		yi.paramsSetString("type", "shinydiffusemat")

		bCol = props["color"]
		mirCol = props["mirror_color"]
		bSpecr = props["specular_reflect"]
		bTransp = props["transparency"]
		bTransl = props["translucency"]
		bTransmit = props["transmit_filter"]

		# TODO: all

		i=0
		
		diffRoot = ''
		mcolRoot = ''
		transpRoot = ''
		translRoot = ''
		mirrorRoot = ''
		bumpRoot = ''

		mtextures = mat.getTextures()

		if hasattr(mat, 'enabledTextures'):
			used_mtextures = []
			used_idx = mat.enabledTextures
			for m in used_idx:
				mtex = mtextures[m]
				used_mtextures.append(mtex)
		else:
			used_mtextures = mtextures

		for mtex in used_mtextures:
			if mtex == None: continue
			if mtex.tex == None: continue
			if mtex.tex.type == Blender.Texture.Types.NONE: continue
			used = False
			mappername = "map%x" %i
			
			lname = "diff_layer%x" % i
			if self.writeTexLayer(lname, mappername, diffRoot, mtex, mtex.mtCol, bCol):
				used = True
				diffRoot = lname
			lname = "mircol_layer%x" % i
			if self.writeTexLayer(lname, mappername, mcolRoot, mtex, mtex.mtCmir, mirCol):
				used = True
				mcolRoot = lname
			lname = "transp_layer%x" % i
			if self.writeTexLayer(lname, mappername, transpRoot, mtex, mtex.mtAlpha, [bTransp]):
				used = True
				transpRoot = lname
			lname = "translu_layer%x" % i
			if self.writeTexLayer(lname, mappername, translRoot, mtex, mtex.mtTranslu, [bTransl]):
				used = True
				translRoot = lname
			lname = "mirr_layer%x" % i
			if self.writeTexLayer(lname, mappername, mirrorRoot, mtex, mtex.mtRayMir, [bSpecr]):
				used = True
				mirrorRoot = lname
			lname = "bump_layer%x" % i
			if self.writeTexLayer(lname, mappername, bumpRoot, mtex, mtex.mtNor, [0]):
				used = True
				bumpRoot = lname
			if used:
				self.writeMappingNode(mappername, self.namehash(mtex.tex), mtex)
			i +=1
		
		yi.paramsEndList()
		if len(diffRoot) > 0:	yi.paramsSetString("diffuse_shader", diffRoot)
		if len(mcolRoot) > 0:	yi.paramsSetString("mirror_color_shader", mcolRoot)
		if len(transpRoot) > 0:	yi.paramsSetString("transparency_shader", transpRoot)
		if len(translRoot) > 0:	yi.paramsSetString("translucency_shader", translRoot)
		if len(mirrorRoot) > 0:	yi.paramsSetString("mirror_shader", mirrorRoot)
		if len(bumpRoot) > 0:	yi.paramsSetString("bump_shader", bumpRoot)
		
		yi.paramsSetColor("color", bCol[0], bCol[1], bCol[2])
		yi.paramsSetFloat("transparency", bTransp)
		yi.paramsSetFloat("translucency", bTransl)
		yi.paramsSetFloat("diffuse_reflect", props["diffuse_reflect"])
		yi.paramsSetFloat("emit", props["emit"])
		yi.paramsSetFloat("transmit_filter", bTransmit)
		
		yi.paramsSetFloat("specular_reflect", bSpecr)
		yi.paramsSetColor("mirror_color", mirCol[0], mirCol[1], mirCol[2])
		yi.paramsSetBool("fresnel_effect", props["fresnel_effect"])
		yi.paramsSetFloat("IOR", props["IOR"])

		if props["brdfType"] == "Oren-Nayar":
			yi.paramsSetString("diffuse_brdf", "oren_nayar")
			yi.paramsSetFloat("sigma", props["sigma"])
		
		ymat = yi.createMaterial(self.namehash(mat))
		self.materialMap[mat] = ymat


	def writeBlendShader(self, mat):
		yi = self.yi
		yi.paramsClearAll()
		props = mat.properties["YafRay"]
		yi.printInfo("Exporter: Blend material with: [" + props["material1"] + "] [" + props["material2"] + "]")
		yi.paramsSetString("type", "blend_mat")
		yi.paramsSetString("material1", self.namehash(Blender.Material.Get(props["material1"])))
		yi.paramsSetString("material2", self.namehash(Blender.Material.Get(props["material2"])))


		i=0
		
		diffRoot = ''

		mtextures = mat.getTextures()

		if hasattr(mat, 'enabledTextures'):
			used_mtextures = []
			used_idx = mat.enabledTextures
			for m in used_idx:
				mtex = mtextures[m]
				used_mtextures.append(mtex)
		else:
			used_mtextures = mtextures

		for mtex in used_mtextures:
			if mtex == None: continue
			if mtex.tex == None: continue
			if mtex.tex.type == Blender.Texture.Types.NONE: continue

			used = False
			mappername = "map%x" %i
			
			lname = "diff_layer%x" % i
			if self.writeTexLayer(lname, mappername, diffRoot, mtex, mtex.mtCol, [props["blend_value"]]):
				used = True
				diffRoot = lname
			if used:
				self.writeMappingNode(mappername, self.namehash(mtex.tex), mtex)
			i +=1

		yi.paramsEndList()
		if len(diffRoot) > 0: yi.paramsSetString("mask", diffRoot)
			
		yi.paramsSetFloat("blend_value", props["blend_value"])
		ymat = yi.createMaterial(self.namehash(mat))
		self.materialMap[mat] = ymat


	def writeMatteShader(self, mat):
		yi = self.yi
		yi.paramsClearAll()
		yi.paramsSetString("type", "shadow_mat")
		ymat = yi.createMaterial(self.namehash(mat))
		self.materialMap[mat] = ymat

	def writeNullMat(self, mat):
		yi = self.yi
		yi.paramsClearAll()
		yi.paramsSetString("type", "null")
		ymat = yi.createMaterial(self.namehash(mat))
		self.materialMap[mat] = ymat

	def writeMaterial(self, mat):
		self.yi.printInfo("Exporter: Creating Material: \"" + mat.name + "\"")
		if mat.name == "y_null":
			self.writeNullMat(mat)
		elif mat.properties["YafRay"]["type"] == "glass":
			self.writeGlassShader(mat, False)
		elif mat.properties["YafRay"]["type"] == "Rough Glass":
			self.writeGlassShader(mat, True)
		elif mat.properties["YafRay"]["type"] == "glossy":
			self.writeGlossyShader(mat, False)
		elif mat.properties["YafRay"]["type"] == "coated_glossy":
			self.writeGlossyShader(mat, True)
		elif mat.properties["YafRay"]["type"] == "shinydiffusemat":
			self.writeShinyDiffuseShader(mat)
		elif mat.properties["YafRay"]["type"] == "blend":
			self.writeBlendShader(mat)
