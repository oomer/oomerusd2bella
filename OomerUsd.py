### USD read module

'''
MIT License

Copyright (c) 2023 Harvey Fong

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

## standard modules
from pathlib import Path  # used for cross platform file paths

## third party modules
from pxr import Usd, UsdGeom, UsdShade   
import numpy as np

## oomer modules
import OomerUtil as oomUtil

class Reader:
    def __init__(   self, 
                    inFile, 
                    _debug=False,
                    _usda=False,
                    _unittest=False,
                ):
            
        self.file = inFile


        self.debug = _debug
        self.unittest = _unittest

        if not _unittest:
            self.stage = Usd.Stage.Open( str( inFile ) )
            if _usda: self.stage.Export( "./"+str( Path( inFile).with_suffix( '.usda')))
        else:
            self.stage = Usd.Stage.CreateInMemory( inFile )

        self.meshes = {}
        self.lights = {}
        self.xforms = {}
        self.cameras = {}
        self.preview_surfaces = {}
        self.uv_textures = {}
        self.prototype_instances = {}
        self.prototype_children = []
        self.root_prims = []
        oomerUtility = oomUtil.Mappings()
        self.usdPreviewSurface = oomerUtility.usdPreviewSurface
        ###self.udim_indices = { *() } # This defines a Python set, sets can only store a value once

        ### GLOBALS
        ###========
        if self.stage.HasMetadata( 'metersPerUnit' ):
            self.meters_per_unit = self.stage.GetMetadata( 'metersPerUnit' )
        else:
            self.meters_per_unit = 1
        if self.stage.HasMetadata( 'upAxis' ):
            self.up_axis = self.stage.GetMetadata( 'upAxis' )
        else:
            self.up_axis = 'Y'
        if self.stage.HasMetadata( 'timeCodesPerSecond' ):
            self.timecodes_per_second = self.stage.GetMetadata( 'timeCodesPerSecond' )
        else:
            self.timecodes_per_second = 30
        if self.stage.HasMetadata( 'startTimeCode' ):
            self.start_timecode = self.stage.GetMetadata( 'startTimeCode' )
        else:
            self.start_timecode = 0
        if self.stage.HasMetadata( 'endTimeCode' ):
            self.end_timecode = self.stage.GetMetadata( 'endTimeCode' )
        else:
            self.end_timecode = 0

        self.timecodes_per_second = self.stage.GetMetadata( 'timeCodesPerSecond')
        self.start_timecode = self.stage.GetMetadata( 'startTimeCode')
        self.end_timecode = self.stage.GetMetadata( 'endTimeCode')

        ## Record camera scale multiplier to ensure later cam transforms sync with world unit
        if self.meters_per_unit == 0.01:
            self.cam_unit_scale = 1
        else: # [ ] hardcoded but should be calculated based on self.meters_per_unit 
            self.cam_unit_scale = 1

        self.mat4_identity = np.array( [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]], dtype='float64')
        self.mat4_light = np.array( [[1,0,0,0],[0,-1,0,0],[0,0,-1,0],[0,0,0,1]], dtype='float64')
        self.xform_cache = UsdGeom.XformCache()

    def GetAttribute( self, attribute ): # UsdAttribute
        # - [ ] prim attributes can store local values OR have remote inputs values from another prim output
        if attribute.HasAuthoredConnections(): 
            sdf_path =  attribute.GetConnections()[0] # USD_API bool GetConnections ( SdfPathVector * sources ) const
            _connection_prim = Usd.Stage.GetPrimAtPath( self.stage, sdf_path.GetPrimPath()) 
            return _connection_prim.GetAttribute( sdf_path.name).Get() ### USD_API UsdAttribute GetAttribute ( const TfToken & attrName ) const
        else:
            return attribute.Get()

    # depth first search for prims convertable to bella
    def traverse_scene( self, filter_by_purpose=False ):
        # - USD notes
        # - UsdStage.traverse() filters out prototypes and possibly other prims
        # - Usd.PrimRange allows custom traversal filter

        rootPrim = self.stage.GetPseudoRoot() ### TODO doc GetPseudoRoot()
        listPrims = list( Usd.PrimRange( rootPrim)) ### TODO doc PrimRange()
        listPrototypePrims = [] 
        usdPrototypes = self.stage.GetPrototypes() # prototypes contain a common hierarchy referenced by instances
        for eachPrototype in usdPrototypes:
            self.prototype_children = self.prototype_children + list( eachPrototype.GetChildren())
            listPrototypePrims = listPrototypePrims + list( iter( Usd.PrimRange( eachPrototype )))
        listAllPrims = listPrototypePrims + listPrims
        ignorePrim = [] # bypass list for unwanted shaders and textures, ie proxy

        # ancestor state tracking
        # TODO better documentation
        purpose=False
        ancestorPurpose=False
        materialPrim = False

        for eachPrim in listAllPrims:
            # toplevel xform holds purpose and material
            # context switcher carrying purpose and material to descendants
            eachParent = eachPrim.GetParent()
            if eachParent:
                ### this seems Bella specific because of uuid storage, seems ok
                if eachPrim.GetParent().GetName() == '/': # append to root list if this is a toplevel prim
                    name = oomUtil.uuidSanitize( eachPrim.GetName(), _hashSeed = eachPrim.GetPath() ) 
                    self.root_prims.append( name)

            if eachPrim.HasAttribute( 'purpose'): # USD: render, ...
                purpose = eachPrim.GetAttribute( 'purpose').Get()
            #p1 = UsdShade.MaterialBindingAPI(usd_prim).DirectBinding().Get()
            #p2 = dir(UsdShade.MaterialBindingAPI(usd_prim))

            if eachPrim.HasRelationship( 'material:binding'): # [ ] doesn't seem efficient
                materialRelationship = eachPrim.GetRelationship( 'material:binding')
                materialSdfPath = materialRelationship.GetTargets()[0]
                materialPrim = self.stage.GetPrimAtPath( materialSdfPath)

            if purpose == 'default': purpose = ancestorPurpose # [ ] default really means always on
            if purpose == None: purpose = ancestorPurpose # [ ] assume that missing purpose is a DCC output failure
            if purpose == 'proxy': purpose=False # [ ] use Boolean False rather than store string
            ancestorPurpose = purpose 

            if filter_by_purpose == False: purpose = 'render' # force render purpose on all prims

            if eachPrim.GetTypeName() == 'Xform':
                self.xforms[ eachPrim ]  = {}
                if eachPrim.IsInstance():
                    # Dictionary map of xform prim to instance prim
                    self.prototype_instances[eachPrim] =  self.resolveInstanceToPrim(eachPrim)
            if eachPrim.GetTypeName() == 'Mesh' and purpose == 'render':
                if filter_by_purpose == True and purpose == 'render' or filter_by_purpose == False:
                    self.meshes[ eachPrim ]  = {}
                    if materialPrim: self.meshes[ eachPrim][ 'material_prim'] = materialPrim
            # - [ ] Does this find prims without a purpose
            # - [ ] This traversal seems naive
            if filter_by_purpose == True and purpose == False:
                # traverse materials under proxy mesh and add to ignore_prim
                # - [ ] document why I ignore these ones, related to Animal Logic usdlab methinks
                for eachRelationship in eachPrim.GetRelationships():
                    if 'material:binding' in eachRelationship.GetName(): # have seen both material:binding and material:binding:preview used
                        materialSdfPath = eachRelationship.GetTargets()[ 0]
                        materialPrim = self.stage.GetPrimAtPath( materialSdfPath)
                        if self.debug: print( 'IGNORING', materialPrim)
                        ignorePrim.append( materialPrim)

            # - [ ] Treat UsdPreviewSurface as a equivalent to a Bella PBR material
            if eachPrim.GetTypeName() == 'Material' and eachPrim not in ignorePrim and 'proxy' not in eachPrim.GetName(): # filter out proxy materials
                self.preview_surfaces[ eachPrim] = {} # [ ] one UsdPreviewSurface becomes 1 bella quickMaterial
                surfaceOutput = eachPrim.GetAttribute( 'outputs:surface')

                # A material probably holds a unique surface shader and then instances of UsdUVTextures
                # to ingest the material, we populate 

                # Once a Material prim is found, we kinda mass haul-in all file textures
                # Could do a proper traversal of actually used shader connections instead
                # to avoid proxy textures
                # - [ ] document what PrimRange does
                for each in Usd.PrimRange( eachPrim): ## ( subtree traversal depth first)
                    infoId = each.GetAttribute( 'info:id').Get()
                    if infoId == 'UsdUVTexture':
                        ### file paths are relative to .usd file where they are defined
                        ### ./main.usd
                        ### ./textureDir/cat.png
                        ### ./geomDir/cat.usd
                        # -- ./geomdir/cat.usd is referenced is ./main.usd
                        # -- cat.usd uses texture with a locator string "../textureDir/cat.png"
                        # -- during scene composition, all prims appear under one scenegraph
                        # -- but "../textureDir/cat.png" 
                        #maybe flattewn

                        ### This is how NOT to get an attrib
                        ### file = self.GetAttribute( each.GetAttribute( 'inputs:file'))
                        ### this gets a raw string and is inappropriate because we need
                        ### sdfAssetPath.resolvedPath because the raw string will either be relative OR absolute

                        usdShader = UsdShade.Shader(each)
                        sdfAssetPath = usdShader.GetInput('file').Get() ### shader <- input <- sdfAssetPath
                        absFilePath = sdfAssetPath.resolvedPath ### total API confusion, this attrib not documented, got by trying to use GetResolvedPath() and API suggested resolvedPath
                        relFilePath = sdfAssetPath.path
                        ### My newbie c++ brain finally figured out that .path and .resolvedPath
                        ### SDF_API SdfAssetPath ( const std::string & 	path,
                        ###                        const std::string & 	resolvedPath 
                        ###                      )	
                        if (self.file.parent != Path(absFilePath)): ### Use relative path unless in same dir
                            file = Path(absFilePath).relative_to( self.file.parent.resolve() ) ### calculate texture relative to -usdfile path
                        else:
                            file = Path(absFilePath)
                        wrapS = str( each.GetAttribute( 'inputs:wrapS').Get())
                        wrapT = str( each.GetAttribute( 'inputs:wrapT').Get())
                        self.uv_textures[ each] = {} # [ ] one UsdUvTexture becomes 1 bella fileTexture
                        self.uv_textures[ each][ 'file'] = file
                        self.uv_textures[ each][ 'wrapS'] = wrapS
                        self.uv_textures[ each][ 'wrapT'] = wrapT
                        self.uv_textures[ each][ '_bellatype'] = 'fileTexture'

                if surfaceOutput.HasAuthoredConnections(): 
                    surfaceConnection =  surfaceOutput.GetConnections()[ 0] # assume first one [ ] why is there more than one?
                    surfaceShader = Usd.Stage.GetPrimAtPath( self.stage, surfaceConnection.GetPrimPath()) 
                    infoId = surfaceShader.GetAttribute( 'info:id').Get()
                    if infoId == 'UsdPreviewSurface': 
                        self.preview_surfaces[ eachPrim][ 'shader'] = surfaceShader # TODO is 'shader' referenced
                        # - [ ] when a diffuseColor is found, this is good enough to claim
                        # - [ ] this prim can be converted to a PBR material
                        # _input.GetConnections()[0] # - [x] why more than one, in a node architecture, each attribute is designed to allow more than one input although max is usually one
                        # - [ 2024 ] a rich node based architecture allows lots of diff type of inputs from procedurals to files to constants
                        # - [ 2024 ] right now I am assuming the use of inputs:file rather than say a checkerboard procedural
                        # - [ 2024 ] when I embark on MaterialX, these assumptions will be revisited

                        for shaderInput in self.usdPreviewSurface.keys():
                            if surfaceShader.HasAttribute( 'inputs:'+ shaderInput):
                                shaderAttribute = surfaceShader.GetAttribute( 'inputs:'+ shaderInput)
                                if shaderAttribute.HasAuthoredConnections(): # A connection is an incoming input to prim
                                    # - [ ] this only handles file references and not procedurals
                                    connectionPrim = Usd.Stage.GetPrimAtPath( self.stage, shaderAttribute.GetConnections()[ 0].GetPrimPath()) # discover incoming prim
                                    ###fix 2024 if eachInput == 'normal': # - [ ] hack to set bella conversion type required
                                    ###    self.uv_textures[_connection_prim]['_bellatype'] = 'normalMap'
                                    self.preview_surfaces[ eachPrim][ shaderInput] = self.GetAttribute( connectionPrim.GetAttribute( 'inputs:file')) # - [ ] sdf get filepath
                                    self.preview_surfaces[ eachPrim][ ( shaderInput, 'connection_prim')] = connectionPrim
                                else: 
                                    self.preview_surfaces[ eachPrim][ shaderInput] = shaderAttribute.Get() # - [ ] local value

                        if surfaceShader.HasAttribute( 'inputs:diffuseColor'):
                            shaderAttribute = surfaceShader.GetAttribute( 'inputs:diffuseColor')
                            if shaderAttribute.HasAuthoredConnections(): # means there is a prim input
                                attribConnection =  shaderAttribute.GetConnections()[ 0] # assume first one [ ] why is there more than one?
                                connectionPrim = Usd.Stage.GetPrimAtPath( self.stage, attribConnection.GetPrimPath()) 
                                self.preview_surfaces[ eachPrim][ 'connection'] = connectionPrim
                            else:
                                if self.debug: print( shaderAttribute.Get())

            if eachPrim.GetTypeName() == 'Camera':
                self.cameras[ eachPrim ]  = {}

            if eachPrim.GetTypeName() == 'SphereLight':
                self.lights[ eachPrim ] = {}

            # Sun
            if eachPrim.GetTypeName() == 'DistantLight':
                self.lights[ eachPrim ] = {}
                #self.distant_lights[ each_prim ]['color']  = each_prim.GetAttribute('inputs:color').Get()
                #self.distant_lights[ each_prim ]['intensity']  = each_prim.GetAttribute('inputs:intensity').Get()
            # Arealight
            if eachPrim.GetTypeName() == 'RectLight':
                self.lights[ eachPrim ] = {}
            # Spotlight
            if eachPrim.GetTypeName() == 'SpotLight':
                self.lights[ eachPrim ] = {}
            # Domelight            
            if eachPrim.GetTypeName() == 'DomeLight':
                self.lights[ eachPrim ] = {}
                if eachPrim.GetAttribute( 'texture:file').IsValid():
                    if self.debug: print( eachPrim.GetAttribute( 'texture:file').Get())

    def resolveInstanceToPrim(self, _prim): # hardcoded to ALUSD
        usdPrototype= _prim.GetPrototype() # Animal Logic Alab.usd  should return GEO GEOPROXY Material
        for eachChildPrim in usdPrototype.GetChildren():
            if eachChildPrim.HasAttribute( 'purpose'):
                if eachChildPrim.GetAttribute( 'purpose').Get() == 'render':
                    return eachChildPrim # Assumes never having more than one prim with render purpose
        return False

    def triangulate_ngons( self, 
                           _faceVertexCounts,  # int[]
                           _faceVertexIndices, # int[] 
                           _txcoordIndices = False,
                           _normalIndices = False,
                         ):

        ### feed original usd arrays, returns modfified usd arrays
        # triangulates polygons with greater than 4 vertices ( aka ngons )
        # og_vertex_counts [ 3,3,4,5,4,3 ] -> [ 3,3,4,3,3,3,4,3 ] faceVertexCounts
        # in this case we take the 4th polygon and triangulate to 3,3,3
        # og_vertex_indices [ 0,1,2, 0,2,3, 3,4,5,6, 7,8,9,10,11, 12,13,14,15, 16,17,19 ] faceVertexIndices
        # -> [ 0,1,2, 0,2,3, 3,4,5,6, 7,8,9, 7,9,10, 7,10,11, 12,13,14,15, 16,17,19]

        npFaceVertexIndices  = np.array( _faceVertexIndices)  #convert to nparray so we can use slicing
        if _txcoordIndices:
            npTxcoordIndices  = np.array( _txcoordIndices)  #convert to nparray so we can use slicing
            newTxcoordIndices = []
        if _normalIndices:
            npNormalIndices = np.array( _normalIndices)  #convert to nparray so we can use slicing
            newNormalsIndices = []

        ogVertCount = 0 
        newVertCount = 0
        newVertexCounts = []    ### int[] faceVertexCount
        newVertexIndices = []   ### int[] faceVertexIndices
        newTxcoordIndices = []   ### int[] faceVertexIndices
        newNormalIndices = []   ### int[] faceVertexIndices
        ngonVertexLimit = 5

        # steps to triangulate a polygon
        # ngons triangulates to (numfaceverts - 2) triangles, ie a pentagon produces 5 (verts) - 2 = 3 triangles
        # _faceVertexCounts is a 1D array equal in size to total number of polygons, each array element stores number of vertices per face
        # _faceVertexIndices is a 1D array equal in size the sum of array elements in usdFaceVertexCounts
        #    where each element is an index that points to usd points list
        # usd_point_list is a 2D array of points in a mesh (faceVertexIndices stores indices to this list allowing multiple faces to share point data)
        # point data is XYZ location

        for face in range(0,len( _faceVertexCounts)):
            numVertsPerFace = _faceVertexCounts[ face ] 
            if numVertsPerFace < ngonVertexLimit: # default triangle and quad processing
                newVertexCounts.append( numVertsPerFace)
                newVertexIndices += list( npFaceVertexIndices[ ogVertCount :ogVertCount + int ( numVertsPerFace)])
                ### 2024
                if _txcoordIndices: # optional explict indices
                    newTxcoordIndices += list( npTxcoordIndices[ ogVertCount :ogVertCount + int ( numVertsPerFace)])
                if _normalIndices: # optional explict indices
                    newNormalIndices += list( npNormalIndices[ ogVertCount :ogVertCount + int ( numVertsPerFace)])
                ogVertCount += numVertsPerFace
                newVertCount += numVertsPerFace
            else: # ngon triangulation 
                # [x] triangulation by slipstreaming modified faceVertexCounts and faceVertexIndices
                # [x] single ngon face converts to numVerts-2 triangle faces, 5 verts = 3 tris
                # [x] actual attribs will be recalculated after indices are modified
                #     a return new to old mapping array is required after this operation
                ngonVertexOffset = 0
                for each_new_triangle in range( 0, numVertsPerFace - 2 ): # [x] decimating ngons results in this number of triangles 

                    # append new triangles
                    newVertexCounts.append( 3 )
                    newVertexIndices.append( int( npFaceVertexIndices[ ogVertCount + 0 ] ))
                    newVertexIndices.append( int( npFaceVertexIndices[ ogVertCount + ngonVertexOffset + 1 ] ))
                    newVertexIndices.append( int( npFaceVertexIndices[ ogVertCount + ngonVertexOffset + 2 ] ))
                    if _txcoordIndices:
                        newTxcoordIndices.append( int( npTxcoordIndices[ ogVertCount + 0 ] ))
                        newTxcoordIndices.append( int( npTxcoordIndices[ ogVertCount + ngonVertexOffset + 1 ] ))
                        newTxcoordIndices.append( int( npTxcoordIndices[ ogVertCount + ngonVertexOffset + 2 ] ))
                    if _normalIndices:
                        newNormalIndices.append( int( npNormalIndices[ ogVertCount + 0 ] ))
                        newNormalIndices.append( int( npNormalIndices[ ogVertCount + ngonVertexOffset + 1 ] ))
                        newNormalIndices.append( int( npNormalIndices[ ogVertCount + ngonVertexOffset + 2 ] ))
                    ngonVertexOffset += 1
                    newVertCount += 3
                ogVertCount += numVertsPerFace
        
        if _txcoordIndices and _normalIndices:
            return newVertexCounts, newVertexIndices, newTxcoordIndices, newNormalIndices
        elif _txcoordIndices:
            return newVertexCounts, newVertexIndices, newTxcoordIndices
        else:
            return newVertexCounts, newVertexIndices


    ##
    def getMesh( self, 
                 _prim = False, 
                 _timeCode = False, 
                 _faceVertexCounts = False,
                 _faceVertexIndices = False,
                 _usdNormals = False,
                 _usdPoints = False,
                 _usdTxcoords = False,
               ):
        # ================================================
        # * USD stores faceVertexIndices as a one dimensional list mixing tris, quads, and ngons
        # * Bella's polygon is vec4 stored in C4D style to support both quads and triangles
        # This code avoids using Python loops and instead uses numpy methods to mold the data into a Bella
        # friendly format ( vectorized processing)
        # by putting data into numpy arrays, indexing and processing will be simplified

        if not _prim == False:
            faceVertexCounts = _prim.GetAttribute( 'faceVertexCounts' ).Get( time = _timeCode )
        else: ## unittest
            faceVertexCounts = _faceVertexCounts

        if len( faceVertexCounts) == 0: # Return False when no polygons found
            if self.debug: print( 'FAIL:', _prim, 'zero faces')
            return False, False, False, False, False, False

        if not _prim == False:
            usdPoints = _prim.GetAttribute( 'points' ).Get( time = _timeCode ) # array of points and their positions
            faceVertexIndices = _prim.GetAttribute( 'faceVertexIndices' ).Get( time = _timeCode )
        else: ## unittest
            usdPoints = _usdPoints
            faceVertexIndices = _faceVertexIndices

        # TEXCOORDS
        # =========
        # Deal with usda's multitude of attribute names where uv coords can be stored
        # [x] Use primvar relationship in USD to determine attribute name
        # [ 2024 ] found Scales_baby.usda output with multiple UV texcoords2f primvars:body primvars:head
        # [ 2024 ] Blender USD export supports one texture, multiple UV channels ( useful to increase texel density as needed)
        #           Required a mix node for image texture and 2 uvmap nodes
        dynTxcoordString = 'st' ### fallback 
        if _prim.HasRelationship( 'material:binding'): 
            materialRelationship = _prim.GetRelationship( 'material:binding')
            materialSdfPath = materialRelationship.GetTargets()[0]
            materialPrim = self.stage.GetPrimAtPath( materialSdfPath)
            for materialShaderPrims in Usd.PrimRange( materialPrim): ## local traversal
                infoId = materialShaderPrims.GetAttribute( 'info:id').Get()
                if infoId == 'UsdPrimvarReader_float2':
                    usdShadeInput = UsdShade.Shader( materialShaderPrims).GetInput( 'varname') ## resolve to input name
                    ### Get sdfPath to another prim where value is stored
                    ### - [ ] Could this be connected to another node, do I need a reursive loop?
                    connect2 = usdShadeInput.GetAttr().GetConnections()
                    ### Returns list of input connections
                    if len(connect2) == 1: # input
                        sdfPath2 = usdShadeInput.GetAttr().GetConnections()[0] # assuming single connection world 
                        matPrim2 = self.stage.GetPrimAtPath(sdfPath2.GetPrimPath()) ### Get UsdPrima that at end of this connection
                        dynTxcoordString = matPrim2.GetAttribute(sdfPath2.name).Get() ### UsdPrim.GetAttribute(  ) 
                    else: # local value stored on input
                        dynTxcoordString = usdShadeInput.Get()

        ### - [x] finally realized that the texcoord primvar string is stored in UsdShade graph
        explicitTxcoordIndices = False  
        usdTxcoords = False
        if not _prim == False: 
            print(dynTxcoordString)
            if _prim.GetAttribute( 'primvars:' + dynTxcoordString ).IsValid():  # houdini, blender, maya
                usdTxcoords = _prim.GetAttribute( 'primvars:' + dynTxcoordString ).Get( time = _timeCode )
                if _prim.GetAttribute( 'primvars:' + dynTxcoordString + ':indices' ).IsValid(): # maya stores explicit indices
                    # Maya writes usd with explicit texcoord indices while Blender and Houdini use implicit texcoords indexing
                    # - [ ] document implicit versus explicit
                    explicitTxcoordIndices = _prim.GetAttribute( 'primvars:' + dynTxcoordString + ':indices' ).Get()
        else: ## unittest
            usdTxcoords = _usdTxcoords
 
        ### NORMALS
        ###======== tv_retro.usda = normals t51-helmet.usda = primvars:normals : - [ ] why two string tokens?
        explicitNormalIndices = False
        usdNormals = False
        if not _prim == False:
            if _prim.GetAttribute( 'primvars:normals' ).IsValid(): # TODO Shouldn't access raw attrib, need pxr wrapper: same reason why texcoords was switched, may not apply in this case
                usdNormals = _prim.GetAttribute( 'primvars:normals' ).Get( time = _timeCode )
                if _prim.GetAttribute( 'primvars:normals:indices' ).IsValid(): 
                    explicitNormalIndices = _prim.GetAttribute( 'primvars:normals:indices' ).Get()
            elif _prim.GetAttribute( 'normals' ).IsValid(): # TODO Shouldn't access raw attrib, need pxr wrapper
                usdNormals = _prim.GetAttribute( 'normals' ).Get( time = _timeCode )
                if _prim.GetAttribute( 'normals:indices' ).IsValid(): 
                    explicitNormalIndices = _prim.GetAttribute( 'normals:indices' ).Get()
            else:
                usdNormals = _usdNormals
        else:
            usdNormals = _usdNormals

        ### NGONS
        ###======
        # - [x] triangulate ngons by restructuring counts and indices
        npFaceVertexCounts = np.array( faceVertexCounts, dtype=np.int32)  ## need numpy array here to test for ngons
        if npFaceVertexCounts[ npFaceVertexCounts > 4 ].size > 0:
            if explicitTxcoordIndices: ### example tv_retro.usdz
                if explicitNormalIndices:
                    faceVertexCounts, faceVertexIndices, explicitTxcoordIndices, explicitNormalIndices \
                    = self.triangulate_ngons(   faceVertexCounts, 
                                                faceVertexIndices, 
                                                explicitTxcoordIndices, 
                                                explicitNormalIndices
                                            )
                else:
                    faceVertexCounts, faceVertexIndices, explicitTxcoordIndices  \
                    = self.triangulate_ngons(   faceVertexCounts, 
                                                faceVertexIndices, 
                                                explicitTxcoordIndices, 
                                            )
            else:
                faceVertexCounts, faceVertexIndices = self.triangulate_ngons( faceVertexCounts, faceVertexIndices)
            npFaceVertexCounts = np.array( faceVertexCounts, dtype=np.int32) # redata nparray with triangulated version

        ### numpy-ify
        ###==========
        numFaces = npFaceVertexCounts.size 
        npFaceVertexIndices = np.array( faceVertexIndices, dtype=np.int32)  
        npPoints = np.array( usdPoints, dtype='float64') 
        if explicitTxcoordIndices: ### 
            npExplicitTxcoordIndices = np.array( explicitTxcoordIndices, dtype=np.int32)   
        if explicitNormalIndices: ### 
            npExplicitNormalIndices = np.array( explicitNormalIndices, dtype=np.int32)   
            
        # convert USD mixed tri/vert shared verts -> Bella unshared verts
        # A usda triangle/quad/triangle might look like this 
        # int[] faceVertexCounts = [3, 4, 3]
        # int[] faceVertexIndices = [0, 1, 2, 4, 0, 3, 5, 2, 3, 0]
        # We need to duplicate verts for Bella and add delimiter of vert.c=vert.d for triangles
        # Bella -> vec4u[3] { 0 1 2 2 3 4 5 6 7 8 9 9 }
        # unshared vertex indices will follow a simple ascending numbering scheme

        # A. numpy cumulative sum gives us initial index of second polygon onwards [ ignore last element with :-1])
        # B. concat 0@front gives us an array of initial indices [0] of all polygon ( either quad or tri)
        # followed by new views with sequential increments
        npCumulativeIndex = np.concatenate( ( np.array([ 0]), np.cumsum(npFaceVertexCounts)[:-1])) #one liner for A. & B.

        # create ndarray of simple unshared verts, each face gets a new 1,2,3,[4] incremented range
        # convert to a single column 2d array
        b1 = npCumulativeIndex.reshape( (numFaces,1) )
        # repeat single column 3 more times to create a numFaces x 4 array
        npCumulativeIndex2 = np.repeat(b1,4,axis=1)

        npCumulativeIndex2[ :,1] += 1
        npCumulativeIndex2[ :,2] += 2
        npCumulativeIndex2[ :,3] += 2

        # repeat previous index if triangle
        l = npCumulativeIndex2[ :,3 ]  
        m = np.where( npFaceVertexCounts==4, l+1 , l)
        npCumulativeIndex2[ :,3] = m

        ### npFaceVertexIndices is still uses Usd vertex indexing, sequentialy list tris and quads and delimited by npfaceVertexCount
        ### npIndicesInC4dStyle 
        ### 
        npIndicesInC4DStyle = npCumulativeIndex2.ravel()


        # since npFaceVertexIndices repeats itself when you have shared verts we automatically duplicate values 
        # thus shared verts -> unshared verts in one step
        npPoints = npPoints[ ( npFaceVertexIndices )]

        if usdTxcoords: 
            if explicitTxcoordIndices: # Maya tends to export explicitly indexed vertex buffers
                npTxcoords = np.array( usdTxcoords, dtype='float64')[ ( npExplicitTxcoordIndices) ] # nparray reindexed using explicit indices
            elif len(usdTxcoords) == len(npFaceVertexIndices): ##  if vertices were split these won't match
                npTxcoords = np.array( usdTxcoords, dtype='float64') ## pass through 
            else: ### Magic sauce useing numpy to split vertices in a single vectorized operation
                ### - [ ] document the magic sauce
                npTxcoords = np.array( usdTxcoords, dtype='float64')[ ( npFaceVertexIndices ) ]
        else: # no txcoords
            npTxcoords = False

        # - [ ] need to verify normals
        # - [ ] add a unit test for normals
        # I think I disovered that we can just use npFaceVertexIndices
        npNormals = False
        if usdNormals: 
            if explicitNormalIndices: ## Maya tends to export explicitly indexed vertex buffers
                npNormals = np.array( usdNormals, dtype='float64')[ ( npExplicitNormalIndices)]  
            elif len(usdNormals) == len(npFaceVertexIndices): ##  if vertices were split these won't match
                npNormals = np.array( usdNormals, dtype='float64')
            else: ### Magic sauce using numpy to split vertices in a single vectorized operation
                ### - [ ] document the magic sauce
                npNormals = np.array( usdNormals, dtype='float64')[ ( npFaceVertexIndices)]  # - [ ] split verts if needed magic sauce
        else: ### - no normals at all
            npNormals = np.zeros( [0,3], dtype='float64' )

        return  npFaceVertexCounts, \
                npIndicesInC4DStyle, \
                npPoints, \
                npNormals, \
                npTxcoords


