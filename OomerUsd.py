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
import os.path

## third party modules
from pxr import Usd, UsdGeom, UsdShade, UsdLux , Sdf, Gf
import numpy as np

## oomer modules
import OomerUtil as oomUtil

class Reader:
    def __init__(   self, 
                    _usdFile = False, 
                    _debug = False,
                    _usda = False,
                    _unitTest = False,
                ):
            
        self.file = _usdFile
        self.debug = _debug

        if not _unitTest:
            self.stage = Usd.Stage.Open( str( _usdFile))
            if _usda: self.stage.Export( "./"+str( Path( _usdFile).with_suffix( '.usda')))
        elif isinstance( _usdFile, Usd.Stage): # slipstream in usd stage created in memory
            self.stage = _usdFile
        else: # TODO switch to slipstream method above
            self.stage = Usd.Stage.CreateInMemory( _usdFile)

        self.meshes = {}
        self.primitives = {} ### sphere, cube ( bella supports box), cylinder ( no capsule, cone )
        self.lights = {}
        self.xforms = {}
        self.instancers = {} ### point instancing
        self.scopes = {} ### TODO is a scope a grouping method?
        self.cameras = {}
        self.previewSurfaces = {}
        self.references = {}
        self.uv_textures = {}
        self.prototype_instances = {}
        self.prototype_children = []
        self.rootPrims = []
        oomerUtility = oomUtil.Mappings()
        self.usdPreviewSurface = oomerUtility.usdPreviewSurface
        ###self.udim_indices = { *() } # This defines a Python set, sets can only store a value once
        self.timeCode = False
        ### GLOBALS
        ###========
        self.copyright = False
        self.blender = False
        self.modo = False
        self.houdini = False


        self.start_timecode = self.stage.GetStartTimeCode()
        self.timecodes_per_second = self.stage.GetTimeCodesPerSecond()
        self.end_timecode = self.stage.GetEndTimeCode()
        self.defaultPrim = self.stage.GetDefaultPrim()

        if self.stage.HasMetadata( 'metersPerUnit'):
            self.meters_per_unit = self.stage.GetMetadata( 'metersPerUnit')
        else:
            self.meters_per_unit = 1
        if self.stage.HasMetadata( 'upAxis'):
            self.up_axis = self.stage.GetMetadata( 'upAxis')
        else:
            self.up_axis = 'Y'
        if self.stage.HasMetadata( 'customLayerData'):
            self.customLayerData = self.stage.GetMetadata( 'customLayerData')
            for customName in self.customLayerData.keys():
                if customName == 'copyright':
                    self.copyright = self.customLayerData[ customName]
                if customName == 'houdini':
                    self.houdini = self.customLayerData[ customName]
                    print( self.customLayerData[ customName])
        #if self.stage.HasMetadata( 'doc'):
        #    docString = self.stage.GetMetadata( 'doc')
        #    print( docString)
        #    if "Blender" in docString:
        #        print( 'found Blender')

        ## Record camera scale multiplier to ensure later cam transforms sync with world unit
        if not self.blender:
            self.cam_unit_scale = self.meters_per_unit * 100 
        else:
            self.cam_unit_scale = 1
        # Modo Pixar use cm , self.meters_per_unit == 0.01 
        # Houdni, Blender , self.meters_per_unit == 1
        ### Houdini example with metersPerUnit=1: float focalLength = 0.35
        ### thus focalLength expressed in units of 1/10 of 1 metre aka 1 decimeter
        ### 0.35 decimeters = 3.5 cm = 35 mm 
        ### very confusing but explained in https://groups.google.com/u/3/g/usd-interest/c/6EAeg-d53uI
        ### *Blender* fails to output focal length and aperture according to Pixar api in 1/10 of metresperunit but rather they use mm
        ### *Blender* uses metersPerUnit=1 but outputs focalLength=35
        ### *Blender* camera_unit_scale has to pretend that metresPerUnit==0.01
        ### I submitted bug report pre 3.x, there was some discussion but 3.6 is still wrong

        self.mat4_identity = np.array( [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]], dtype='float64')
        self.xform_cache = UsdGeom.XformCache()

    '''
    def GetAttribute( self, attribute): # UNUSED here for future use
        # - [ ] prim attributes can store local values OR have remote inputs values from another prim output
        if attribute.HasAuthoredConnections(): 
            sdfPath =  attribute.GetConnections()[0] # USD_API bool GetConnections ( SdfPathVector * sources ) const
            connectedPrim = Usd.Stage.GetPrimAtPath( self.stage, sdfPath.GetPrimPath()) 
            return connectedPrim.GetAttribute( sdfPath.name).Get() ### USD_API UsdAttribute GetAttribute ( const TfToken & attrName ) const
        else:
            return attribute.Get()
    '''

    ### rewrite of traverse_scene 2023
    ### due to usd complexity, the naive earlier approach of using PrimRange to traverse all prims
    ### leads to lack of inherited ( from parent or grandparent ) knowledge like kind, visibility, etc
    ### by using IsPostVisit() we descend each branch and toggle on inheritable switches like visibility
    # - [x] Removed timecode during traversal, was erroneously storing time specific data before it is needed
    ### Traversal is all about generalized sorting of prims into python dictionaries
    ### the usefulness of these dictionaries waxes and wanes as I learn more about the API
    ### Expect traversal to be refactored often
    def traverseScene ( self):
        ignorePrim = [] # bypass list for unwanted shaders and textures, ie proxy

        subtreeGroup      = False
        subtreeComponent  = False
        subtreeScope      = False
        subtreePrototype  = False
        subtreeInvisible  = False
        postVisit         = False
        primIter = iter( Usd.PrimRange.PreAndPostVisit( self.stage.GetPseudoRoot()))
        subtreeCounter = 0

        ancestInvisiblePrim = False
        ancestGroupPrim     = False
        usdPrototypes = self.stage.GetPrototypes() # prototypes contain a common hierarchy referenced by instances
        ### currently instancer.hiplc creates BOTH a /hidden/sphere and a /Instances/Prototypes/hidden/sphere, the latter instance referencing to
        ### the former, on top of this the actual instances point to the Prototype, which begs the question, why have two degrees of separation?
        ### to be continued
        for eachPrototype in usdPrototypes:
            children = self.prototype_children + list( eachPrototype.GetChildren())
            listPrototypePrims =  list( iter( Usd.PrimRange( eachPrototype)))

        ### TODO unittest for fragile complex invisibility and group tracking system 
        for prim in primIter:
            primGeom    = UsdGeom.Mesh( prim)
            primKind    = Usd.ModelAPI( prim).GetKind()
            primPurpose = primGeom.GetPurposeAttr().Get()
            #primPurpose = primGeom.ComputePurpose() ### compute may be expensive on large scenes according to API docs, 
            # our stack based traversal method is appropriate to gather this info as we walk through each prim
            primType    = prim.GetTypeName()
            primName    = prim.GetName()
            primUUID = oomUtil.uuidSanitize( prim.GetName(), _hashSeed = prim.GetPath()) 

            if prim == self.stage.GetPseudoRoot(): 
                subtreeCounter = 0
            elif primIter.IsPostVisit(): 
                subtreeCounter -= 1
                postVisit = True
            else: 
                subtreeCounter += 1
                postVisit = False

            ### on PrimRange() post visit turn off ancestral flags
            if prim == ancestInvisiblePrim: subtreeInvisible  = False
            if prim == ancestGroupPrim:     subtreeGroup  = False

            if not postVisit and not subtreeCounter == 0: ### a PrimRange() post visit is 2nd pass
                ### Track ancestral flags 
                if primGeom.GetVisibilityAttr().Get() == 'invisible' or primName == 'hidden': 
                    if subtreeInvisible == False: # first discovered invis ancestor
                        ancestInvisiblePrim = prim ### track ancestor prim
                    subtreeInvisible = True ### subtree one time switch, assumption all children are invis
                if primKind == 'group' or primName == 'hidden': 
                    if subtreeGroup == False: # first discovered group ancestor
                        ancestGroupPrim = prim ### track ancestor prim
                    subtreeGroup = True ### subtree one time switch, assumption all children are in group

                ### add toplevel to render list
                eachParent = prim.GetParent()
                ### this seems Bella specific because of uuid storage, seems ok
                if eachParent.GetName() == '/' and not subtreeInvisible: # append to root list if this is a toplevel prim
                    ### skip Camera xform because we create a new camera xform that can be orbited because it is in Bella's coord system
                    # rather than Usd coord system
                    foundCamera = False
                    for childPrim in prim.GetChildren():
                        if childPrim.GetTypeName() == 'Camera': foundCamera = True
                    if not foundCamera: self.rootPrims.append( primUUID)

                #print( subtreeCounter, 'group:', subtreeGroup, 'invisible:', subtreeInvisible, subtreeCounter, 'purpose:', primPurpose, prim.GetPrimPath())
                #print( subtreeCounter, 'purpose:', primPurpose, prim.GetPrimPath(), 'ins', prim.IsInstanceable(), prim.IsInstance())

                if primType == 'Xform' or primType == 'Scope':
                    hasAuthoredReferences = prim.HasAuthoredReferences()
                    self.xforms[ prim ]  = {}
                    self.xforms[ prim][ 'hasAuthoredReferences'] = hasAuthoredReferences
                    self.xforms[ prim][ 'isInvisible'] = subtreeInvisible
                    self.xforms[ prim][ 'instanceUUID'] = False

                    if prim.IsInstance():
                        instancePrim = self.resolveInstance( prim)
                        instanceUUID = oomUtil.uuidSanitize( instancePrim.GetName(), _hashSeed = instancePrim.GetPath()) 
                        self.xforms[ prim][ 'instanceUUID'] = instanceUUID
                        self.prototype_instances[ prim] =  self.resolveInstance( prim)
                ### 
                if primType == 'Mesh':
                    instancePrim = False
                    if prim.HasAuthoredReferences(): ### Referencing is used for both local and file instancing
                        instancePrim = self.resolveInstance( prim)

                    self.meshes[ prim ]  = {}
                    self.meshes[ prim][ 'instance'] = instancePrim
                    self.meshes[ prim][ 'isInvisible'] = subtreeInvisible

                # - [ ] Treat UsdPreviewSurface as a equivalent to a Bella PBR material
                if primType == 'Material' and prim not in ignorePrim: 
                    self.previewSurfaces[ prim] = {} # [ ] one UsdPreviewSurface becomes 1 bella quickMaterial
                    # A material probably holds a unique surface shader and then instances of UsdUVTextures
                    # to ingest the material, we populate 

                    # Once a Material prim is found, we kinda mass haul-in all file textures
                    # Could do a proper traversal of actually used shader connections instead
                    # to avoid proxy textures
                    ### PrimRange will traverse tree starting at prim and descending all children subtrees
                    ### 
                    for shaderNetworkPrim in Usd.PrimRange( prim): ## ( subtree traversal depth first), it this the same as gathering all the nodes of a shader network
                        usdShader = UsdShade.Shader( shaderNetworkPrim)
                        idAttr = usdShader.GetIdAttr()
                        if idAttr:
                            infoId = idAttr.Get()
                            usdShader = UsdShade.Shader( shaderNetworkPrim)

                            if infoId == 'UsdPreviewSurface':
                                self.previewSurfaces[ prim][ 'shader'] = shaderNetworkPrim # TODO is 'shader' referenced
                                # - [ ] when a diffuseColor is found, this is good enough to claim
                                # - [ ] this prim can be converted to a PBR material
                                # _input.GetConnections()[0] # - [x] why more than one, in a node architecture, each attribute is designed to allow more than one input although max is usually one
                                # - [ 2024 ] a rich node based architecture allows lots of diff type of inputs from procedurals to files to constants
                                # - [ 2024 ] right now I am assuming the use of inputs:file rather than say a checkerboard procedural
                                # - [ 2024 ] when I embark on MaterialX, these assumptions will be revisited
                                for shaderAttributeName in self.usdPreviewSurface.keys(): # loop over this dictionary mapping usdpreviewsurface to bella uber
                                    shaderAttribute = usdShader.GetInput( shaderAttributeName)
                                    if shaderAttribute and shaderAttributeName != 'normal':
                                        attribValue = shaderAttribute.Get()
                                        connectedPrimTuple = shaderAttribute.GetConnectedSource()
                                        if connectedPrimTuple: # Is input connected to another node
                                            connectableAPI = connectedPrimTuple[0]
                                            shaderPrim = UsdShade.Shader( connectableAPI.GetPrim())
                                            infoId2 = shaderPrim.GetIdAttr().Get()
                                            if infoId2 == 'UsdUVTexture':
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
                                                ### file = Usd.Prim.GetAttribute( each.GetAttribute( 'inputs:file'))
                                                ### this gets a raw string and is inappropriate because we need
                                                ### sdfAssetPath.resolvedPath because the raw string will either be relative OR absolute

                                                sdfAssetPath = shaderPrim.GetInput( 'file').Get() ### shader <- input <- sdfAssetPath
                                                absFilePath = sdfAssetPath.resolvedPath ### total API confusion, this attrib not documented, got by trying to use GetResolvedPath() and API suggested resolvedPath
                                                relFilePath = sdfAssetPath.path
                                                ### My newbie c++ brain finally figured out that .path and .resolvedPath
                                                ### SDF_API SdfAssetPath ( const std::string & 	path,
                                                ###                        const std::string & 	resolvedPath 
                                                ###                      )	
                                                if ( self.file.parent != Path( absFilePath)): ### Use relative path unless in same dir
                                                    ### pathlib relative_to files
                                                    ### ValueError: '/Users/harvey/oomerusd2bella/tv_retro/0/tv_retro_body_bc.png' is not in the subpath of '/Users/harvey/oomerusd2bella/houdini' OR one path is relative and the other is absolute. 
                                                    #file = Path(os.path.relpath( absFilePath, self.file.parent.resolve()))
                                                    file = Path( absFilePath)
                                                    #file = Path( absFilePath).relative_to( self.file.parent.resolve()) ### calculate texture relative to -usdfile path
                                                else:
                                                    file = Path( relFilePath)
                                                sourceColorSpace = usdShader.GetInput( 'sourceColorSpace').Get()
                                                wrapS = shaderPrim.GetInput( 'wrapS').Get()
                                                wrapT = shaderPrim.GetInput( 'wrapT').Get()
                                                self.uv_textures[ shaderPrim] = {} # [ ] one UsdUvTexture becomes 1 bella fileTexture
                                                self.uv_textures[ shaderPrim][ 'file'] = file
                                                self.uv_textures[ shaderPrim][ 'wrapS'] = wrapS
                                                self.uv_textures[ shaderPrim][ 'wrapT'] = wrapT
                                                self.uv_textures[ shaderPrim][ '_bellatype'] = 'fileTexture'
                                            #if infoId == 'UsdPrimvarReader_float2':
                                            #    print( 'hello', usdShade3.GetInput('varname').Get())
                                            self.previewSurfaces[ prim][ shaderAttributeName] = shaderPrim
                                        else: # store local value
                                            self.previewSurfaces[ prim][ shaderAttributeName] = attribValue

                if primType == 'Camera':
                    self.cameras[ prim]  = {}

                ### Lights TODO downgrade from dict to array
                if primType in [ 'SphereLight', 'DistantLight', 'RectLight', 'DiskLight', 'DomeLight']:
                    self.lights[ prim] = {}

                ### Primitives
                if primType in [ 'Sphere', 'Cube', 'Cylinder']:
                    self.primitives[ prim] = {}

                if primType == 'PointInstancer':
                    ### loop point instances
                    ### - [ ] separate out each prototype index
                    ### - [x] merge Usd's quat, point, scale into 4x4 matrix
                    ### - [ ] store 4x4 matrix per protoIndex
                    ### - [x] move _timeCode out of this function, since we don't want to traverse each frame
                    ### rationale behind Usd's decision to separate out orientation, translation and scale
                    ### is saving of memory when dealing with billions of instances, Bella only uses mat4f
                    primPointInstancer = UsdGeom.PointInstancer( prim)
                    positionBuf = primPointInstancer.GetPositionsAttr()
                    orientationBuf = primPointInstancer.GetOrientationsAttr()
                    scaleBuf = primPointInstancer.GetScalesAttr()
                    if positionBuf: ### TODO is this check required
                        self.instancers[ prim] = {}
                        self.instancers[ prim][ 'orientationsAttr'] = orientationBuf
                        self.instancers[ prim][ 'positionsAttr'] = positionBuf
                        self.instancers[ prim][ 'scalesAttr'] = scaleBuf
                        protoBinding = prim.GetRelationship( 'prototypes')
                        self.instancers[ prim][ 'protoChildren'] = protoBinding

    ###
    def resolveInstance(self, _prim ):
        # The powerful layering system allowing usd to compose the scene from many sources
        # leads to roundabout ways to find the prim that introduces a mesh
        # There seems to be an instance method but Blender exports a <prepend references>
        # References is also used for referencing external file.usda so seems overkill for a prim on the current stage
        # UsdPrim.GetReferences() gets the references but I can't seem to list the original mesh
        # so we must use the full power of the UsdPrimCompositionQuery to discover the original prim via the prim reference
        compQuery = Usd.PrimCompositionQuery.GetDirectReferences( _prim)
        compArc = compQuery.GetCompositionArcs()
        sdfPath = compArc[0].GetTargetNode().GetPathAtIntroduction()
        return self.stage.GetPrimAtPath( sdfPath)

    ### - [ ] TODO move function into a OomerProcess.py module leaving OomerUsd.py for reading and OomerBella.py for bella specific wrirting
    def triangulateNgons( self, 
                          _faceVertexCounts,  # int[]
                          _faceVertexIndices, # int[] 
                          _txcoordIndices = False, # int[]
                          _normalIndices = False, # int[]
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

        ogVertCount = 0 
        newVertCount = 0
        newVertexCounts = []    ### int[] faceVertexCount
        newVertexIndices = []   ### int[] faceVertexIndices
        newTxcoordIndices = []  ### int[] faceVertexIndices
        newNormalIndices = []   ### int[] faceVertexIndices
        ngonVertexLimit = 5

        # steps to triangulate a polygon
        # ngons triangulates to (numfaceverts - 2) triangles, ie a pentagon produces 5 (verts) - 2 = 3 triangles
        # _faceVertexCounts is a 1D array equal in size to total number of polygons, each array element stores number of vertices per face
        # _faceVertexIndices is a 1D array equal in size the sum of array elements in usdFaceVertexCounts
        #    where each element is an index that points to usd points list
        # usd_point_list is a 2D array of points in a mesh (faceVertexIndices stores indices to this list allowing multiple faces to share point data)
        # point data is XYZ location

        for face in range( 0, len( _faceVertexCounts)):
            numVertsPerFace = _faceVertexCounts[ face] 
            if numVertsPerFace < ngonVertexLimit: # default triangle and quad processing
                newVertexCounts.append( numVertsPerFace)
                newVertexIndices += list( npFaceVertexIndices[ ogVertCount :ogVertCount + int( numVertsPerFace)])
                ### 2024
                if _txcoordIndices: # optional explict indices
                    newTxcoordIndices += list( npTxcoordIndices[ ogVertCount :ogVertCount + int( numVertsPerFace)])
                if _normalIndices: # optional explict indices
                    newNormalIndices += list( npNormalIndices[ ogVertCount :ogVertCount + int( numVertsPerFace)])
                ogVertCount += numVertsPerFace
                newVertCount += numVertsPerFace
            else: # ngon triangulation 
                # [x] triangulation by slipstreaming modified faceVertexCounts and faceVertexIndices
                # [x] single ngon face converts to numVerts-2 triangle faces, 5 verts = 3 tris
                # [x] actual attribs will be recalculated after indices are modified
                #     a return new to old mapping array is required after this operation
                ngonVertexOffset = 0
                for each_new_triangle in range( 0, numVertsPerFace - 2): # [x] decimating ngons results in this number of triangles 

                    # append new triangles
                    newVertexCounts.append( 3)
                    newVertexIndices.append( int( npFaceVertexIndices[ ogVertCount + 0 ] ))
                    newVertexIndices.append( int( npFaceVertexIndices[ ogVertCount + ngonVertexOffset + 1]))
                    newVertexIndices.append( int( npFaceVertexIndices[ ogVertCount + ngonVertexOffset + 2]))
                    if _txcoordIndices:
                        newTxcoordIndices.append( int( npTxcoordIndices[ ogVertCount + 0]))
                        newTxcoordIndices.append( int( npTxcoordIndices[ ogVertCount + ngonVertexOffset + 1]))
                        newTxcoordIndices.append( int( npTxcoordIndices[ ogVertCount + ngonVertexOffset + 2]))
                    if _normalIndices:
                        newNormalIndices.append( int( npNormalIndices[ ogVertCount + 0]))
                        newNormalIndices.append( int( npNormalIndices[ ogVertCount + ngonVertexOffset + 1]))
                        newNormalIndices.append( int( npNormalIndices[ ogVertCount + ngonVertexOffset + 2]))
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
                 _prim = False,              #UsdPrim
                 _faceVertexCounts = False,  #int[]
                 _faceVertexIndices = False, #int[]
                 _usdNormals = False,        #vec3f
                 _usdPoints = False,         #vec3f
                 _usdTxcoords = False,       #vec3f
               ):
        # ================================================
        # * USD stores faceVertexIndices as a one dimensional list mixing tris, quads, and ngons
        # * Bella's polygon is vec4 stored in C4D style to support both quads and triangles
        # This code avoids using Python loops and instead uses numpy methods to mold the data into a Bella
        # friendly format ( vectorized processing)
        # by putting data into numpy arrays, indexing and processing will be simplified
        # - [ ] WARNING: snapshot of mesh on frame 1 meaning no animated topology changes 
        if _prim: usdGeom = UsdGeom.Mesh( _prim)
        if _prim:
            ### faceVertexCounts = _prim.GetAttribute( 'faceVertexCounts' ).Get( time = _timeCode )
            faceVertexCounts = usdGeom.GetFaceVertexCountsAttr().Get( time = 1)
        else: ## unittest
            faceVertexCounts = _faceVertexCounts

        if len( faceVertexCounts) == 0: # Return False when no polygons found
            if self.debug: print( 'FAIL:', _prim, 'zero faces')
            return False, False, False, False, False, False

        if _prim:
            usdPoints = _prim.GetAttribute( 'points').Get( 1) # array of points and their positions
            faceVertexIndices = usdGeom.GetFaceVertexIndicesAttr().Get( 1)
        else: ## unittest
            usdPoints = _usdPoints
            faceVertexIndices = _faceVertexIndices

        # TEXCOORDS
        # =========
        # [x] Use primvar relationship in USD to determine attribute name for texcoords
        # [ 2024 ] found Scales_baby.usda output with multiple UV texcoords2f primvars:body primvars:head
        # [ 2024 ] Blender USD export supports one texture, multiple UV channels ( useful to increase texel density as needed)
        #           Required a mix node for image texture and 2 uvmap nodes
        if _prim:
            dynTxcoordString = 'st' ### fallback 
            if _prim.HasRelationship( 'material:binding'): ### Is there a material bound to this prim?
                materialRelationship = _prim.GetRelationship( 'material:binding')
                materialSdfPath = materialRelationship.GetTargets()[ 0]
                materialPrim = self.stage.GetPrimAtPath( materialSdfPath)
                for materialShaderPrims in Usd.PrimRange( materialPrim): ## local traversal
                    infoId = UsdShade.Shader( materialShaderPrims).GetIdAttr().Get()
                    if infoId == 'UsdPrimvarReader_float2':
                        usdShadeInput = UsdShade.Shader( materialShaderPrims).GetInput( 'varname') ## resolve to input name
                        ### Get sdfPath to another prim where value is stored
                        ### - [ ] Could this be connected to another node, do I need a reursive loop?
                        connect2 = usdShadeInput.GetAttr().GetConnections()
                        ### Returns list of input connections
                        if len(connect2) == 1: # input
                            sdfPath2 = usdShadeInput.GetAttr().GetConnections()[ 0] # naive assumption that connections to only one leaf node, otherwise we need a full tree search
                            matPrim2 = self.stage.GetPrimAtPath( sdfPath2.GetPrimPath()) ### Get UsdPrima that at end of this connection
                            dynTxcoordString = matPrim2.GetAttribute( sdfPath2.name).Get() ### UsdPrim.GetAttribute(  ) 
                        else: # local value stored on input
                            dynTxcoordString = usdShadeInput.Get()

            ### 2024 material binding
            ###materialBinding =  _prim.GetRelationship('material:binding')
            ###if materialBinding.GetTargets():
            ###    materialSdfPath = materialBinding.GetTargets()[ 0]
            ###    materialPrim = self.stage.GetPrimAtPath( materialSdfPath)

        ### Look for txccords with explicit indices
        explicitTxcoordIndices = False  
        usdTxcoords = False
        if _prim: 
            if _prim.GetAttribute( 'primvars:' + dynTxcoordString).IsValid():  # houdini, blender, maya
                usdTxcoords = _prim.GetAttribute( 'primvars:' + dynTxcoordString).Get( 1)
                if _prim.GetAttribute( 'primvars:' + dynTxcoordString + ':indices').IsValid(): # maya stores explicit indices
                    # Maya writes usd with explicit texcoord indices while Blender and Houdini use implicit texcoords indexing
                    # - [ ] document implicit versus explicit
                    explicitTxcoordIndices = _prim.GetAttribute( 'primvars:' + dynTxcoordString + ':indices').Get()
        else: ## unittest
            usdTxcoords = _usdTxcoords
 
        ### NORMALS
        ###======== tv_retro.usda = normals t51-helmet.usda = primvars:normals : - [ ] why two string tokens?
        explicitNormalIndices = False
        usdNormals = False
        if _prim:
            if _prim.GetAttribute( 'primvars:normals').IsValid(): # TODO Shouldn't access raw attrib, need pxr wrapper: same reason why texcoords was switched, may not apply in this case
                usdNormals = _prim.GetAttribute( 'primvars:normals').Get( 1)
                if _prim.GetAttribute( 'primvars:normals:indices').IsValid(): 
                    explicitNormalIndices = _prim.GetAttribute( 'primvars:normals:indices').Get()
            elif _prim.GetAttribute( 'normals').IsValid(): # TODO Shouldn't access raw attrib, need pxr wrapper
                usdNormals = UsdGeom.Mesh( _prim).GetNormalsAttr().Get()
                if _prim.GetAttribute( 'normals:indices').IsValid(): 
                    explicitNormalIndices = _prim.GetAttribute( 'normals:indices').Get()
            else:
                usdNormals = _usdNormals
        else:
            usdNormals = _usdNormals

        ### NGONS
        ###======
        # - [x] triangulate ngons by restructuring counts and indices
        npFaceVertexCounts = np.array( faceVertexCounts, dtype=np.int32)  ## need numpy array here to test for ngons
        if npFaceVertexCounts[ npFaceVertexCounts > 4].size > 0:
            if explicitTxcoordIndices: ### example tv_retro.usdz
                if explicitNormalIndices:
                    faceVertexCounts, faceVertexIndices, explicitTxcoordIndices, explicitNormalIndices \
                    = self.triangulateNgons( faceVertexCounts,          #int[]
                                             faceVertexIndices,         #int[] 
                                             explicitTxcoordIndices,    #int[]
                                             explicitNormalIndices,     #int[]
                                           )
                else:
                    faceVertexCounts, faceVertexIndices, explicitTxcoordIndices \
                    = self.triangulateNgons( faceVertexCounts,          #int[]
                                              faceVertexIndices,        #int[]
                                              explicitTxcoordIndices,   #int[]
                                            )
            else:
                faceVertexCounts, faceVertexIndices = self.triangulateNgons( faceVertexCounts, faceVertexIndices)
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
        b1 = npCumulativeIndex.reshape( (numFaces,1))
        # repeat single column 3 more times to create a numFaces x 4 array
        npCumulativeIndex2 = np.repeat(b1,4,axis=1)

        npCumulativeIndex2[ :,1] += 1
        npCumulativeIndex2[ :,2] += 2
        npCumulativeIndex2[ :,3] += 2

        # repeat previous index if triangle
        l = npCumulativeIndex2[ :,3]  
        m = np.where( npFaceVertexCounts == 4, l+1 , l)
        npCumulativeIndex2[ :,3] = m

        ### npFaceVertexIndices sequentialy lists tris and quads, delimited by npfaceVertexCount ( triangulated and split)
        ### npIndicesInC4dStyle lists tris [a,b,c,c] and quads [a,b,c,d]
        npIndicesInC4DStyle = npCumulativeIndex2.ravel()

        ### since npFaceVertexIndices repeats itself when you have shared verts we automatically duplicate values 
        ### thus shared verts -> unshared verts in one step
        npPoints = npPoints[ ( npFaceVertexIndices)]

        if usdTxcoords: 
            if explicitTxcoordIndices: # Maya tends to export explicitly indexed vertex buffers
                npTxcoords = np.array( usdTxcoords, dtype='float64')[ ( npExplicitTxcoordIndices)] # nparray reindexed using explicit indices
            elif len(usdTxcoords) == len(npFaceVertexIndices): ##  if vertices were split these won't match
                npTxcoords = np.array( usdTxcoords, dtype='float64') ## pass through 
            else: ### Magic sauce using numpy to split vertices in a single vectorized operation
                ### - [ ] TODO document the magic sauce
                npTxcoords = np.array( usdTxcoords, dtype='float64')[ ( npFaceVertexIndices)]
        else: # no txcoords
            npTxcoords = False

        # - [ ] TODO need to verify normals
        # - [ ] TODO add a unit test for normals
        npNormals = False
        if usdNormals: 
            if explicitNormalIndices: ## Maya tends to export explicitly indexed vertex buffers
                npNormals = np.array( usdNormals, dtype='float64')[ ( npExplicitNormalIndices)]  
            elif len(usdNormals) == len(npFaceVertexIndices): ##  if vertices were split these won't match
                npNormals = np.array( usdNormals, dtype='float64')
            else: ### Magic sauce using numpy to split vertices in a single vectorized operation
                ### - [ ] document the magic sauce
                npNormals = np.array( usdNormals, dtype='float64')[ ( npFaceVertexIndices)]  # - [ ] split verts if needed magic sauce
        else: ### - no normals at all TODO maybe switch to bool
            npNormals = False
            #npNormals = np.zeros( [0,3], dtype='float64')

        return  npFaceVertexCounts, \
                npIndicesInC4DStyle, \
                npPoints, \
                npNormals, \
                npTxcoords


