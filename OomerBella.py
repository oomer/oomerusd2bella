### Bella write module

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

## third party modules
import numpy as np
from pxr import Gf, UsdGeom, UsdShade, UsdLux 

## standard modules
from pathlib import Path  # used for cross platform file paths
import json
import os.path 
import io  # used for unittests, in memory file like

## oomer modules
import OomerUtil as oomUtil

class SceneAscii:
    def __init__( self, 
                  _bsaFile = False, 
                  _usdScene = False,
                  _debug = False,
                  _colorDome = False,
                  _unitTest = False,
                ):

        self.renderer_up_axis = 'Z'
        self.worldNodes = []
        self.usdScene = _usdScene
        self.imageDome = False
        self.colorDome = _colorDome
        self.debug = _debug
        self.timeCode = 1

        if not _unitTest:
            if not _bsaFile.parent.exists():
                _bsaFile.parent.mkdir()
            self.bsaFile = _bsaFile
            self.file = open( str( _bsaFile), 'w')
            self.writeHeader()
            self.writeGlobal()
            self.writeState()
            self.writeBeautyPass()
            if _usdScene.copyright: 
                self.writeString( 'copyright', json.dumps ( _usdScene.copyright))
                self.worldNodes.append('notes')
        else: ### unittest, in memory file
            self.bsaFile = False
            self.file = io.StringIO()

        self.camera = ''
        u = self.usdScene.meters_per_unit  
        if self.usdScene.up_axis == self.renderer_up_axis: # up axis matches Bella
            _basis_change_mat4 = [[ u, 0, 0, 0],
                                  [ 0, u, 0, 0],
                                  [ 0, 0, u, 0],
                                  [ 0, 0, 0, 1]]
        else:
            _basis_change_mat4 = [[ u, 0, 0, 0],
                                  [ 0, 0, u, 0],
                                  [ 0, -u, 0, 0],
                                  [ 0, 0, 0, 1]]
        self.np_basis_change_mat4 = np.array( _basis_change_mat4)

        oomerUtility = oomUtil.Mappings()
        self.usdPreviewSurface = oomerUtility.usdPreviewSurface

    def setTimeCode( self, _timeCode=False):
        self.timeCode = _timeCode

    ## nice 27 space text formatting
    def nice( self, _attrib):
        return str("  ." + f'{_attrib:27}' + '= ')

    ##
    def writeHeader( self):
        self.file.write('# bella scene\n')
        self.file.write('# version: 20230411\n')
    ##
    def writeGlobal( self):
        self.file.write('global global:\n')
        self.file.write(self.nice('states[*]') + 'state;\n')
    ##
    def writeState( self):
        self.file.write('state state:\n')
        self.file.write(self.nice('settings') + 'settings;\n')
        self.file.write(self.nice('world') + 'world;\n')
    ##
    def writeGroundPlane( self, _elevation=0):
        self.file.write('groundPlane groundPlane:\n')
        self.file.write(self.nice('elevation') + str( _elevation) + 'f;\n')
    ##
    def writeString( self, _name = False, _string = False):
        self.file.write('string  notes:\n')
        self.file.write(self.nice('name') + '"' + _name + '";\n')
        self.file.write(self.nice('value') + _string + ';\n')
    ##
    def writeBeautyPass( self):
        self.file.write('beautyPass beautyPass;\n')
    ##
    def writeSkyDome( self):
        self.file.write('skyDome skyDome;\n')
    ##
    def writeBox( self, _sizeX = 1, _sizeY = 1, _sizeZ = 1, _radius = 0):
        self.file.write( 'box box:\n')
        self.file.write(self.nice( 'radius') + str( _radius) + 'f;\n')
        self.file.write(self.nice( 'sizeX') + str( _sizeX) + 'f;\n')
        self.file.write(self.nice( 'sizeY') + str( _sizeY) + 'f;\n')
        self.file.write(self.nice( 'sizeZ') + str( _sizeZ) + 'f;\n')
    ##
    def writeColor( self, _rgba=( 1, 1, 1, 1), _variation=0):
        self.file.write( 'color color:\n')
        self.file.write( self.nice( 'color') + 
                                    'rgba(' + 
                                    str( _rgba[0]) + ' ' + 
                                    str( _rgba[1]) + ' ' + 
                                    str( _rgba[2]) + ' ' + 
                                    str( _rgba[3]) + ');\n'
                       )
        self.file.write(self.nice( 'variation') + str( _variation) + 'f;\n')

    ##
    def writeAttribConnected( self, _name = False, _value = False):
        self.file.write('  .' + f'{_name:26}' + '|= ' + _value + ';\n')

    def writeNode( self, _type = False, _uuid = False):
        self.file.write( _type + ' ' + _uuid + ':\n')

    def writeAttribFloat( self, _name = False, _value= 1.0):
        self.file.write( self.nice( _name) + str( _value) + 'f;\n')
    
    def writeAttribInt( self, _name = False, _value= 1):
        self.file.write( self.nice( _name) + str( _value) + ';\n')
    
    def writeAttribUint( self, _name = False, _value= 1):
        self.file.write( self.nice( _name) + str( _value) + 'u;\n')

    def writeAttribString( self, _name = False, _value= ''):
        self.file.write( self.nice( _name) + '"' + _value + '";\n')
    
    def writeAttribRaw( self, _name = False, _value= 'obj'):
        self.file.write( self.nice( _name) + _value + ';\n')

    def writeNodeAttribNumpy( self,
                              _name = False,
                              _type = False,
                              _nparray = False,
                              _lbracket = '{',
                              _rbracket = '}',
                            ):
        #https://stackoverflow.com/questions/53820891/speed-of-writing-a-numpy-array-to-a-text-file
        #Assumed numpy.savetxt was performant, it is not! Saving 0020_060 Sprite fright went from 4 minutes to 1 minute
        npArray = _nparray.ravel() # - [ ] doc
        self.file.write( self.nice( _name) + _type)
        self.file.write( _lbracket)
        npFormat = ' '.join([ '%g'] * npArray.size) #- [ ] document npFormat
        npFormat = '\n'.join([ npFormat])
        data = npFormat % tuple( npArray )
        self.file.write( data)
        self.file.write( _rbracket)
        self.file.write( ';\n')

    def writeAttribNumpy( self,
                          _name = False,
                          _type = False,
                          _nparray = False,
                          _bracket = False,
                        ):
        #https://stackoverflow.com/questions/53820891/speed-of-writing-a-numpy-array-to-a-text-file
        #Assumed numpy.savetxt was performant, it is not! Saving 0020_060 Sprite fright went from 4 minutes to 1 minute
        if      _bracket == '{' or _bracket == False: 
            _bracket = '{'
            endBracket = '}'
        elif    _bracket == '(': endBracket = ')'
        elif    _bracket == '[': endBracket = ']'
        
        npArray = _nparray.ravel() # - [ ] doc
        self.file.write( self.nice( _name) + _type)
        self.file.write( _bracket)
        npFormat = ' '.join([ '%g'] * npArray.size) #- [ ] document npFormat
        npFormat = '\n'.join([ npFormat])
        data = npFormat % tuple( npArray )
        self.file.write( data)
        self.file.write( endBracket)
        self.file.write( ';\n')


    ###
    def writeCamera( self, 
                    _prim = False, #UsdPrim
                   ):
        uuid = oomUtil.uuidSanitize( _prim.GetName(), _hashSeed = _prim.GetPath())
        self.camera = uuid

        if _prim.GetAttribute( 'horizontalAperture').HasValue():
            horizontalAperture = _prim.GetAttribute( 'horizontalAperture').Get( self.timeCode) * self.usdScene.cam_unit_scale
            if horizontalAperture > 1000: ### Blender hack to deal with it's hardcoded mm unit for camera
                horizontalAperture /= 100
        else:
            horizontalAperture = 36
        if _prim.GetAttribute( 'horizontalApertureOffset').HasValue():
            horizontalApertureOffset = _prim.GetAttribute( 'horizontalApertureOffset').Get( self.timeCode) * self.usdScene.cam_unit_scale
            if horizontalApertureOffset > 1000: ### Blender hack to deal with it's hardcoded mm unit for camera
                horizontalApertureOffest /= 100
        else:
            horizontalApertureOffset = 0
        if _prim.GetAttribute( 'verticalAperture').HasValue():
            verticalAperture = _prim.GetAttribute( 'verticalAperture').Get( self.timeCode) * self.usdScene.cam_unit_scale
            if verticalAperture > 1000: ### Blender hack to deal with it's hardcoded mm unit for camera
                verticalAperture /= 100
        else:
            verticalAperture = 24
        if _prim.GetAttribute( 'verticalApertureOffset').HasValue(): 
            verticalApertureOffset = _prim.GetAttribute( 'verticalApertureOffset').Get( self.timeCode) * self.usdScene.cam_unit_scale
            if verticalApertureOffset > 1000: ### Blender hack to deal with it's hardcoded mm unit for camera
                verticalApertureOffest /= 100
        else:
            verticalApertureOffset = 0
        if _prim.GetAttribute( 'projection').HasValue():
            projection = _prim.GetAttribute( 'projection').Get( self.timeCode)
        else:
            projection = 'PERSPECTIVE'

        if _prim.GetAttribute( 'focalLength').HasValue():
            focalLength = _prim.GetAttribute( 'focalLength').Get( self.timeCode) * self.usdScene.cam_unit_scale
            if focalLength > 1000: ### Blender hack to deal with it's hardcoded mm unit for camera
                focalLength /= 100
        else:
            focalLength = 50

        if _prim.GetAttribute( 'aspectRatio').HasValue():
            pixelAspect = _prim.GetAttribute( 'aspectRatio').Get( self.timeCode) 
        else:
            pixelAspect = 1.0

        if _prim.GetAttribute( 'focusDistance').HasValue():
            focusDistance = _prim.GetAttribute( 'focusDistance').Get( self.timeCode)
            if focusDistance <=0:
                focusDistance = 0.877
        else:
            focusDistance = 0.877
        if _prim.GetAttribute( 'fStop').HasValue():
            fStop = _prim.GetAttribute( 'fStop').Get( self.timeCode)
        else:
            fStop = 8
        if fStop == 0:
            fStop = 8

        nSteps = 1
        shutter = 250
        iso = 100
        diaphragmType = "CIRCULAR"
        angle = 60  #bokeh POLYGONAL
        nBlades = 6 #bokeh POLYGONAL
        fps = int( self.usdScene.timecodes_per_second)
        xRes = 1920
        yRes = 1080

        # Bella camera node
        self.writeNode( _type = 'camera', _uuid = uuid)
        self.writeAttribRaw( _name = 'lens', _value = uuid + '_thinLens')
        self.writeAttribRaw( _name = 'resolution',
                              _value = 'vec2( ' + str( xRes ) + ' ' + str( yRes ) + ' )',
                            )
        self.writeAttribRaw( _name = 'sensor', _value = uuid + '_sensor')
        self.writeAttribFloat( _name = 'ev', _value = 13.5)
        self.writeSensor( uuid, horizontalAperture, verticalAperture)
        self.writeThinLens( uuid, focusDistance, focalLength, fStop)
        self.writeCameraXform( _uuid = uuid, _prim = _prim)

    ###
    def writeSensor( self, _uuid, _horizontalAperture, _verticalAperture):
        self.writeNode( _type = 'sensor', _uuid = _uuid + '_sensor')
        self.writeAttribRaw( _name = 'size',
                             _value = 'vec2(' + str( _horizontalAperture) +
                                            ' ' +
                                            str( _verticalAperture) + ')')

    def writeThinLens( self, 
                       _uuid,
                       _focusDistance = 5,
                       _focalLength = 50,
                       _fStop = 8,
                       _nBlades = 6,
                       _angle = 60,
                       _diaphragmType = 'CIRCULAR'
                     ):

        if _diaphragmType == 'POLYGONAL':
            _diaphragmType = 'straight'
        else:
            _diaphragmType = 'circular'
        self.writeNode( _type = 'thinLens', _uuid = _uuid + '_thinLens')
        self.writeAttribFloat( _name = 'steps[0].fStop', _value = _fStop)
        self.writeAttribFloat( _name = 'steps[0].focalLen', _value = _focalLength)
        self.writeAttribFloat( _name = 'steps[0].focusDist', _value = _focusDistance)
        self.writeAttribInt( _name = 'aperture.blades', _value = _nBlades)
        self.writeAttribFloat( _name = 'aperture.rotation', _value = _angle)
        self.writeAttribString( _name = 'aperture.shape', _value = _diaphragmType)

    ###
    def writeCameraXform( self, 
                          _uuid = False, #str
                          _prim = False, #UsdPrim
                        ):
        uuidXform = _uuid + 'Xform'
        self.worldNodes.append( uuidXform) 
        self.writeNode( _type = 'xform', _uuid = uuidXform)
        self.writeAttribString( _name = 'name', _value = uuidXform)
        self.writeAttribRaw( _name = 'children[*]', _value = _uuid)

        self.usdScene.xform_cache.SetTime( self.timeCode) #if cache time is unset it uses DEFAULT which is always going to be wrong
        np_matrix4 = np.array( self.usdScene.xform_cache.GetLocalToWorldTransform( _prim), dtype='float64')  # get CTM for camera
        np_bella = np_matrix4 @ self.np_basis_change_mat4  # transform camera CTM in DCC coordsys to bella coordsys
        np_bella[1] *= -1  # Flip Bella y axis
        np_bella[2] *= -1  # Flip Bella z axis
        np_matrix4_1d = np_bella.ravel()  # 1-D array copy of the elements of an array in row-major order
        self.writeAttribNumpy( _name = 'steps[0].xform',
                                   _type = 'mat4',
                                   _nparray = np_matrix4_1d,
                                   _bracket = '(',
                                 )

    def writeMesh( self, 
                   _prim= False,            #UsdPrim
                   _npVertexCount = False,  #numpyint[]
                   _npVertexIndices = False,#numpyint[] 
                   _npPoints = False,       #numpyvec3f[]
                   _npNormals = False,      #numpyvec3f[]
                   _npTxcoords = False,     #numpyvec3f[]
                   _xformCache = False,     #Usd.Stage.XformCache
                   _subdivision = False,    #int
                   _colordome = False,      #bool
                  ):
        # Along with a mesh, this function inserts an xform node to
        # 1. capture usd's gprim's ability to hold a transfrom
        # 2. to hold onto any materials
        # 3. because no xform attribute exists on Bella's mesh node

        if _colordome: self.colorDome=True

        primName = _prim.GetName()
        uuid = oomUtil.uuidSanitize( _prim.GetName(), _hashSeed = _prim.GetPath())

        usdGeom = UsdGeom.Imageable(_prim)
        primPurpose = usdGeom.ComputePurpose()
        primVisibility = usdGeom.GetVisibilityAttr().Get()
        if primPurpose != 'default' and primPurpose != 'render':
        #if primPurpose != 'default' and primPurpose != 'render' and primVisibility != 'invisible':
            return # Skip write mesh if proxy

        ### 2024 material binding
        materialBinding =  _prim.GetRelationship('material:binding')
        matPrim = False
        if materialBinding.GetTargets():
            materialSdfPath = materialBinding.GetTargets()[ 0]
            matPrim = self.usdScene.stage.GetPrimAtPath( materialSdfPath)
            if matPrim: ### if null then this material may be deactivated
                materialName = oomUtil.uuidSanitize( matPrim.GetName(), _hashSeed = matPrim.GetPath())

        np_matrix4 = np.array( _xformCache.GetLocalTransformation( _prim)[0])
        # INSERT XFORM 
        # the name of xform should be the same as usd gprim
        # this way the GetChildren() query done anywhere will be correct
        # since we create intermediate xforms here, renaming the prim with mesh is easy 
        self.writeNode( _type = 'xform',
                        _uuid = uuid
                       )
        self.writeAttribString( _name = 'name', _value= primName)
        uuid += '_m' # xform gets OG name, mesh gets _mesh name
        np_matrix4_1d = np_matrix4.ravel()  # reshape [[a1, b1, c1, d1],[a2, b2, c2, d2]] to [(a1 b1 c1 d1 a2 b2 c2 d2)] 
        self.writeAttribRaw( _name = 'children[*]', _value = uuid)
        self.writeAttribNumpy( _name = 'steps[0].xform',
                               _type = 'mat4',
                               _bracket = '(',
                               _nparray = np_matrix4_1d,
                             )
        if matPrim:
            self.writeAttribRaw( _name = 'material', _value = materialName)

        self.writeNode( _type = 'mesh', _uuid = uuid)
        self.writeAttribString( _name = 'name', _value = primName)
        self.writeAttribNumpy( _name = 'polygons',
                               _type = 'vec4u[' + str( _npVertexCount.size) + ']',
                               _nparray = _npVertexIndices,
                             )

        numRows, _ = _npPoints.shape
        self.writeAttribNumpy( _name = 'steps[0].points',
                               _type = 'pos3f[' + str( numRows) + ']',
                               _nparray = _npPoints,
                             )
        if isinstance( _npNormals, np.ndarray):
            self.writeAttribNumpy( _name = 'steps[0].normals',
                                   _type = 'vec3f[' + str( len( _npNormals)) + ']',
                                   _nparray = _npNormals,
                                 )

        if primVisibility == 'invisible':
            self.writeAttribString( _name = 'visibility', _value = 'hidden')
       
        try:
            if isinstance( _npTxcoords, np.ndarray): # fail on non np.ndarray
                self.writeAttribNumpy( _name = 'steps[0].uvs',
                                       _type = 'vec2f[' + str( _npTxcoords.shape[0] ) + ']',
                                       _nparray=_npTxcoords,
                                     )
        except:
            if self.debug: print( 'FAIL writeMesh()', uuid)

        if _subdivision > 0:
            self.writeAttribInt(  _name = 'subdivision.level',       
                                  _value = _subdivision,
                                )

        ### Bella flag to skip mesh optimization 
        ### self.writeNodeAttrib( attribute_name = 'optimized',       
        #                           attribute_value='true',
        #                         )

    def writeInstance(  self,
                        _prim = False,          #UsdPrim
                        _instancePrim = False,  #UsdPrim
                     ):
        primName = _prim.GetName() 
        name = oomUtil.uuidSanitize( primName, _hashSeed = _prim.GetPath()) 
        instancePrimName = _instancePrim.GetName() 
        instanceName = oomUtil.uuidSanitize( instancePrimName, _hashSeed = _instancePrim.GetPath()) 
        self.writeNode( _type = 'xform', _uuid = name)
        self.writeAttribString( _name = 'name', _value = primName)
        self.writeAttribRaw( _name = 'children[*]', _value = instanceName)
        self.writeAttribNumpy( _name = 'steps[0].xform',
                               _type = 'mat4',
                               _nparray = np.array( [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]], dtype='float64'),
                               _bracket = '(',
                             )

    def writePrimitive( self,
                        _prim = False,
                      ):
        primName = _prim.GetName() 
        uuid = oomUtil.uuidSanitize( primName, _hashSeed = _prim.GetPath()) 
        usdType = _prim.GetTypeName()
        #primType = self.usdScene.primitives[_prim][ 'type']
        np_matrix4 = np.array( self.usdScene.xform_cache.GetLocalTransformation( _prim)[0])
        # INSERT XFORM 
        # the name of xform should be the same as usd gprim
        # this way the GetChildren() query done anywhere will be correct
        # since we create intermediate xforms here, renaming the prim with mesh is easy 
        self.writeNode( _type = 'xform',
                        _uuid = uuid,
                       )
        self.writeAttribString( _name = 'name', _value = primName)
        uuid += '_m' # xform gets OG name, mesh gets _mesh name
        np_matrix4_1d = np_matrix4.ravel()  # reshape [[a1, b1, c1, d1],[a2, b2, c2, d2]] to [(a1 b1 c1 d1 a2 b2 c2 d2)] 
        self.writeAttribRaw( _name = 'children[*]', _value = uuid)
        self.writeAttribNumpy( _name = 'steps[0].xform',
                               _type = 'mat4',
                               _bracket = '(',
                               _nparray = np_matrix4_1d,
                             )

        ### 2024 material binding
        materialBinding =  _prim.GetRelationship('material:binding')
        matPrim = False
        if materialBinding.GetTargets():
            materialSdfPath = materialBinding.GetTargets()[ 0]
            matPrim = self.usdScene.stage.GetPrimAtPath( materialSdfPath)
            if matPrim: ### if null then this material may be deactivated
                materialName = oomUtil.uuidSanitize( matPrim.GetName(), _hashSeed = matPrim.GetPath())
        if matPrim:
            self.writeAttribRaw( _name = 'material', _value = materialName)

        if usdType == 'Sphere':
            usdGeom = UsdGeom.Sphere( _prim)
            self.writeNode( _type = 'sphere', _uuid = uuid)
            self.writeAttribString( _name = 'name', _value = primName)
            self.writeAttribFloat( _name = 'radius', _value = usdGeom.GetRadiusAttr().Get()) 
        if usdType == 'Cube':
            self.writeNode( _type = 'box', _uuid = uuid)
            usdGeom = UsdGeom.Cube( _prim)
            sizeCube = usdGeom.GetSizeAttr().Get()
            self.writeAttribString( _name = 'name', _value = primName)
            self.writeAttribFloat( _name = 'sizeX', _value = sizeCube)
            self.writeAttribFloat( _name = 'sizeY', _value = sizeCube)
            self.writeAttribFloat( _name = 'sizeZ', _value = sizeCube)
        if usdType == 'Cylinder':
            usdGeom = UsdGeom.Cylinder( _prim)
            self.writeNode( _type = 'cylinder', _uuid = uuid)
            self.writeAttribString( _name = 'name', _value = primName)
            self.writeAttribFloat( _name = 'radius', _value = usdGeom.GetRadiusAttr().Get())
            self.writeAttribFloat( _name = 'height', _value = usdGeom.GetHeightAttr().Get())

    ###
    def writePointInstance(  self,
                             _prim = False, #UsdPrim
                          ):
        primName = _prim.GetName() 
        name = oomUtil.uuidSanitize( primName, _hashSeed = _prim.GetPath()) 
        self.writeNode( _type = 'instancer', _uuid = name)
        self.writeAttribString( _name = 'name', _value = primName)
        orientationBuf = self.usdScene.instancers[ _prim][ 'orientationsAttr'].Get( self.timeCode)
        positionBuf = self.usdScene.instancers[ _prim][ 'positionsAttr'].Get( self.timeCode)
        scaleBuf = self.usdScene.instancers[ _prim][ 'scalesAttr'].Get( self.timeCode)
        listMat4 = []
        for pointNum in range(len( positionBuf)): 
            quatOrient = orientationBuf[ pointNum]
            pos = positionBuf[ pointNum]
            scale = scaleBuf[ pointNum]

            ### buildup matrix
            scaleMat4 = Gf.Matrix4f() 
            scaleMat4.SetScale( scale) ### merge 
            rot = Gf.Rotation( quatOrient) ### quatOrient is stored half precision 
            mat4a = Gf.Matrix4f() 
            rotPosMat = mat4a.SetTransform( rot, pos)
            listMat4.append( scaleMat4 * rotPosMat) ### apply sclae
        multMat4 = np.array( listMat4)

        for protoSdfPath in self.usdScene.instancers[ _prim]['protoChildren'].GetTargets():
            protoPrim = self.usdScene.stage.GetPrimAtPath( protoSdfPath) ### bad stage stage naming
            if protoPrim:
                uuid = oomUtil.uuidSanitize( protoPrim.GetName(), _hashSeed = protoPrim.GetPath()) 
                self.writeAttribRaw( _name = 'children[*]', _value = uuid)

        self.writeAttribNumpy( _name = 'steps[0].instances',
                               _type = 'mat4f[' + str( len( multMat4)) +  ']',
                               _nparray = multMat4.ravel(),
                               _bracket = '{',
                             )
        #self.writeNodeAttrib( _name = 'material', _value = 'grains_ca610fc0')

    ###2024 refactored
    ### - [ ] USD mesh nodes have an optional xform attribute, Bella mesh nodes don't
    def writeXform( self, 
                    _prim = False, 
                    _instanceUUID = False,
                  ):
        if _prim.IsInstance():
            protoPrim =  _prim.GetPrototype().GetChildren()

        ### TODO skip Camera xform because we create a new camera xform that can be orbited because it is in Bella's coord system
        # rather than Usd coord system
        for childPrim in _prim.GetChildren():
            if childPrim.GetTypeName() == 'Camera': return
        # Workaround to get useful name from Animal Logic prototype
        primName = _prim.GetName() 
        primVisibility = UsdGeom.Imageable( _prim).GetVisibilityAttr().Get()
        alusd_name = False 
        if _prim in self.usdScene.prototype_children: # Spelunk and try to find useful name  
            alusd_name = _prim.GetAttribute( 'alusd_originalName').Get() # [ ] GetName() gives us a useless "GEO" name, original name much more relevant
            if isinstance( alusd_name, str): prim_name = alusd_name  
        name = oomUtil.uuidSanitize( primName, _hashSeed = _prim.GetPath()) 

        self.usdScene.xform_cache.SetTime( self.timeCode)  ### Set xform cache to animation time
        np_matrix4 = np.array( self.usdScene.xform_cache.GetLocalTransformation( _prim)[0]) #flatten transforms to mat4

        ### 2024 material binding
        materialBinding =  _prim.GetRelationship('material:binding')
        matPrim = False
        if materialBinding.GetTargets():
            materialSdfPath = materialBinding.GetTargets()[ 0]
            matPrim = self.usdScene.stage.GetPrimAtPath( materialSdfPath)
            if matPrim: ### if null then this material may be deactivated
                materialName = oomUtil.uuidSanitize( matPrim.GetName(), _hashSeed = matPrim.GetPath())

        self.writeNode( _type = 'xform', _uuid = name)
        self.writeAttribString( _name = 'name', _value = primName)

        # - [2024] document prototypes and test 
        # - add unit tests
        if _prim in self.usdScene.prototype_instances: 
            # handler for top level prototype prims, ie the NS:GEO node in Animal Logic Assets
            ### start rewriting this because it is before my understanding of UsdGeom and UsdShader
            childPrim = self.usdScene.prototype_instances[ _prim]
            if childPrim:
                alusd_name = childPrim.GetAttribute( 'alusd_originalName').Get()
                if isinstance( alusd_name, str):
                    childName = oomUtil.uuidSanitize( alusd_name, _hashSeed = childPrim.GetPath())
                else:
                    childName = oomUtil.uuidSanitize( childPrim.GetName())
                self.writeAttribRaw( _name = 'children[*]', _value = childName)

        else:  # normal workflow, including children of toplevel prototype prims
            for childPrim in _prim.GetChildren():
                childName = oomUtil.uuidSanitize( childPrim.GetName(), _hashSeed = childPrim.GetPath())
                self.writeAttribRaw( _name = 'children[*]', _value = childName)
        if _instanceUUID:
            self.writeAttribRaw( _name = 'children[*]', _value = _instanceUUID)

        if matPrim:
            self.writeAttribRaw( _name = 'material', _value = materialName)

        ### Usd stores matrix in row major order
        # numpy scipy does column major order
        # transform3d
        # - [ ] No longer used but has future usefullness: ax, ay, az = pokadot_transform3d.mat2euler(np_matrix4[:3, 0:3]) # convert rotation matrix portion to euler
        # rotate_mxs = Cvector(math.degrees(ax), math.degrees(ay), math.degrees(az))
        # reshape [(a1 b1 c1 d1),(a2 b2 c2 d2)] to [(a1 b1 c1 d1 a2 b2 c2 d2)] for np.savetxt
        #np_matrix4_1d = np_matrix4.flatten()  # 1-D array copy of elements of array in row-major order
        np_matrix4_1d = np_matrix4.ravel()  # 1-D array copy of elements of array in row-major order
        self.writeAttribNumpy( _name = 'steps[0].xform',
                               _type = 'mat4',
                               _nparray = np_matrix4_1d,
                               _bracket = '(',
                             )
        if 'bellaemitter' in name: # hack
            self.writeAttribRaw(  _name = 'material', _value = 'emitter')

    def writeScope( self, 
                    _prim = False,  #UsdPrim
                  ):
        
        materialBinding =  _prim.GetRelationship( 'material:binding')
        if materialBinding.GetTargets():
            materialSdfPath = materialBinding.GetTargets()[ 0]
            materialPrim = self.stage.GetPrimAtPath( materialSdfPath)
        # Workaround to get useful name from Animal Logic prototype
        primName = _prim.GetName() # no wackiness here
        alusd_name = False 
        if _prim in self.usdScene.prototype_children: # Spelunk and try to find useful name  
            alusd_name = _prim.GetAttribute( 'alusd_originalName').Get() # [ ] GetName() gives us a useless "GEO" name, original name much more relevant
            if isinstance( alusd_name, str): prim_name = alusd_name  
        name = oomUtil.uuidSanitize( primName, _hashSeed = _prim.GetPath()) 

        self.stage.xform_cache.SetTime( self.timeCode)  ### Set xform cache to animation time
        np_matrix4 = np.array( self.stage.xform_cache.GetLocalTransformation( _prim)[ 0]) #flatten transforms to mat4

        self.writeNode( _type = 'xform', _uuid = name)
        self.writeAttribString( _name = 'name', _value = primName)

        ### - [2024] document prototypes and test 
        # - [ ] TODO add unit tests
        if _prim in self.usdScene.prototype_instances: 
            # handler for top level prototype prims, ie the NS:GEO node in Animal Logic Assets
            childPrim = self.usdScene.prototype_instances[ _prim]
            if childPrim:
                alusd_name = childPrim.GetAttribute( 'alusd_originalName').Get()
                if isinstance( alusd_name, str):
                    childName = oomUtil.uuidSanitize( alusd_name, _hashSeed = childPrim.GetPath())
                else:
                    childName = oomUtil.uuidSanitize( childPrim.GetName())
                self.writeAttribRaw( _name = 'children[*]', _value = childName)

        else:  # normal workflow, including children of toplevel prototype prims
            for childPrim in _prim.GetChildren():
                childName = oomUtil.uuidSanitize( childPrim.GetName(), _hashSeed = childPrim.GetPath())
                self.writeAttribRaw( _name = 'children[*]', _value = childName)

        ###See writeXform for notes, this was copied from there
        ### TODO can this be left off because it is just identity matrix
        self.writeAttribNumpy( _name = 'steps[0].xform',
                               _type = 'mat4',
                               _nparray = self.usdScene.mat4_identity,
                               _bracket = '(',
                             )

    def writeSettings( self):
        self.writeNode( _type = 'settings', _uuid = 'settings')
        self.writeAttribRaw( _name = 'beautyPass', _value = 'beautyPass')

        if self.camera: 
            self.writeAttribRaw( _name = 'camera', _value = self.camera) # - why use self.camera
        if self.colorDome:
            self.writeAttribRaw( _name = 'environment', _value = 'colorDome')
        if self.imageDome:
            self.writeAttribRaw( _name = 'environment', _value = self.imageDome)
        self.writeAttribFloat( _name = 'iprScale', _value = 100)
        self.writeAttribInt( _name = 'threads', _value = -1)
        self.writeAttribRaw( _name = 'useGpu', _value = 'true')
        self.writeAttribString( _name = 'iprNavigation', _value = 'maya')
        if self.colorDome: self.writeColorDome()
    
    def writeColorDome( self ):
        self.writeNode( _type = 'colorDome', _uuid = 'colorDome')

    def writeImageDome( self, filePath):
        relPath = Path( os.path.relpath( filePath, self.bsaFile.parent)) ### remove absolute path
        self.writeAttribString( _name = 'dir', _value = str( relPath.parent))
        self.writeAttribString( _name = 'ext', _value = str( relPath.suffix))
        self.writeAttribString( _name = 'file', _value = str( relPath.stem)) 

    ###
    def writeOomerCamera( self): #Convenience helper to add a default camera when .usd has none
        focalLength        = 20
        focusDistance      = 0.877 # [ ] TODO use scene extents to calc
        horizontalAperture = 36
        verticalAperture   = 24
        fstop               = 8
        cameraName         = 'oomerCamera'
        self.camera = cameraName
        self.worldNodes.append( cameraName+'_xform') # TODO is this needed OLD?
        self.writeNode( _type = 'xform', _uuid = cameraName + '_xform')
        self.writeAttribString( _name = 'name', _value = cameraName + '_xform')
        self.writeAttribRaw( _name = 'children[*]', _value = cameraName)
        self.writeAttribRaw( _name = 'steps[0].xform', _value = 'mat4(1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1)')

        self.writeNode( _type = 'camera', _uuid = cameraName)
        self.writeAttribRaw( _name = 'lens', _value = cameraName + '_thinLens')
        self.writeAttribRaw( _name = 'resolution', _value = 'vec2( 1920 1080)')
        self.writeAttribRaw( _name = 'sensor', _value = cameraName + '_sensor')

        self.writeNode( _type = 'sensor', _uuid = cameraName + '_sensor')
        self.writeAttribRaw( _name = 'size', _value = 'vec2(' + str( horizontalAperture) + ' ' + str( verticalAperture) + ')') 

        self.writeNode( _type = 'thinLens', _uuid = cameraName + '_thinLens')
        self.writeAttribFloat( _name = 'steps[0].fStop', _value = fstop)
        self.writeAttribFloat( _name = 'steps[0].focalLen', _value = focalLength)
        self.writeAttribFloat( _name = 'steps[0].focalDist', _value = focusDistance)

    ###
    def writeUsdRoot( self):
        uuid = oomUtil.uuidSanitize( self.usdScene.file.stem) + '_usd'
        self.writeNode( _type = 'xform', _uuid = uuid)
        self.worldNodes.append( uuid)
        for childuuid in self.usdScene.rootPrims:
            self.writeAttribRaw( _name = 'children[*]', _value = childuuid)
        self.writeAttribNumpy( _name = 'steps[0].xform',
                               _type = 'mat4',
                               _nparray = self.np_basis_change_mat4,
                               _bracket = '(',
                             )

    ###
    def writeWorld(self):
        self.writeNode( _type = 'xform', _uuid = 'world')
        for uuid in self.worldNodes:
            self.writeAttribRaw( _name = 'children[*]', _value = uuid)
        self.writeAttribNumpy( _name = 'steps[0].xform',
                               _type = 'mat4',
                               _nparray = self.usdScene.mat4_identity,
                               _bracket = '(',
                             )

    ###
    def writeShaderTexture( self,
                          _usdShader,
                          _filePath,
                        ):
        uuid = oomUtil.uuidSanitize( _usdShader.GetPrim().GetName(), _hashSeed = _usdShader.GetPath())
        relPath = Path( os.path.relpath( _filePath, self.bsaFile.parent)) ### remove absolute path
        self.writeNode( _type='fileTexture', _uuid = uuid)
        self.writeAttribString( _name = 'dir', _value = str( relPath.parent))
        self.writeAttribString( _name = 'ext', _value = str( relPath.suffix))
        self.writeAttribString( _name = 'file', _value = str( relPath.stem))

    ###
    def writeNormalTexture( self,
                            _prim,
                            _filePath,
                          ):
        uuid = oomUtil.uuidSanitize( _prim.GetName(), _hashSeed = _prim.GetPath()) + 'normalMap'
        self.writeNode( _type = 'normalMap', _uuid = uuid)
        self.writeAttribString( _name = 'dir', _value = str(_filePath.parent))
        self.writeAttribString( _name = 'ext', _value = '.' + str(_filePath.suffix))
        self.writeAttribString( _name = 'file', _value = str(_filePath.stem))

    ###
    def writeUberMaterial( self,
                           _prim  = False,
                           _forceRoughness = False,
                           _ignoreRoughness = False,
                         ):
        primName = _prim.GetName()
        uuid = oomUtil.uuidSanitize( primName, _hashSeed = _prim.GetPath())
        self.writeNode( _type = 'uber', _uuid = uuid)
        self.writeAttribString( _name = 'name', _value = primName)
        ### USD shaders are defined in a node network
        # USD's MaterialX and UsdShade functionality are still a work in progress
        # https://openusd.org/release/spec_usdpreviewsurface.html  
        # UsdPreviewSurfaces is a Physically Based Surface and supports a limited set of nodes
        # The word Preview specifically refers to the performance nature of the shaders in a Hyrda/Storm 
        # context for rendering 100's of thousands of objects for human animation scrubbing speeds
        # so not specifically realtime but this means UsdPreviewSurface has no transmission
        # found in most Path tracers and realtime engines.
        # Converting to a Bella's material requires traversing the UsdPreviewSurface shader network 
        # and recreating that network with Bella nodes
        # - [x] do a basic translation to Bella uber with only texture maps and constant values
        # - [x] support imagemaps
        # - [ ] support normalmaps 
        # - [ ] should ambient occlusion blend multiply with base color
        # found UsdPreviewSurfaces were stored in a dictionary _usdScene.previewSurfaces
        # Python dict key is ( nodeInput or attribute, UsdPrim or null) 

        ### naivePrimOrVal : naive in this case because the network shader is not properly traversed
        ### each attribute is assumed either a file texture or a local value
        for shaderInputName in self.usdScene.usdPreviewSurface: # loop over all UsdPreviewSurface input names
            if shaderInputName in self.usdScene.previewSurfaces[ _prim]:
                naivePrimOrVal = self.usdScene.previewSurfaces[ _prim][ shaderInputName] # dict stores next shader prim or val
                if type( naivePrimOrVal) == Gf.Vec3f:
                    self.writeAttribRaw( _name = self.usdPreviewSurface[ shaderInputName],
                                            _value = 'rgba(' + str( naivePrimOrVal[0]) +
                                            ' ' +
                                            str( naivePrimOrVal[1]) +
                                            ' ' +
                                            str( naivePrimOrVal[2]) +
                                            ' 1 )'
                                        )
                elif type( naivePrimOrVal) == float:
                    self.writeAttribFloat( _name = 'base.weight', _value = 1)
                    if shaderInputName in ('opacity', 'roughness'): 
                        if _forceRoughness:
                            shaderVal = _forceRoughness * 100
                        else:
                            shaderVal = naivePrimOrVal * 100
                    else: 
                        shaderVal = naivePrimOrVal
                    if shaderInputName == 'metallic': 
                        self.writeAttribFloat( _name = 'base.metallicRoughness', _value = 0.0)
                    if not _ignoreRoughness:
                        self.writeAttribFloat( _name = self.usdPreviewSurface[ shaderInputName],
                                               _value = shaderVal,
                                             )

                elif type( naivePrimOrVal) == int:
                    self.writeAttribUint( _name = self.usdPreviewSurface[ shaderInputName],
                                          _value = naivePrimOrVal,
                                        )
                elif type( naivePrimOrVal) == UsdShade.Shader:
                    if shaderInputName == 'diffuseColor': outType = '.outColor'
                    else: outType = '.outAverage'
                    if shaderInputName == 'metallic': 
                        self.writeAttribFloat( _name = 'base.metallicRoughness', _value = 0)
                    uuidTexture = oomUtil.uuidSanitize( naivePrimOrVal.GetPrim().GetName(), _hashSeed = naivePrimOrVal.GetPath())
                    self.writeAttribConnected( _name = self.usdPreviewSurface[ shaderInputName],
                                               _value = uuidTexture + outType,
                                             )

    def writeRenderFlags( self):
        self.writeNode( _type = 'renderFlags', _uuid = 'oomRenderHide')
        self.writeAttribString( _name = 'name', _value= 'hideFlag')
        self.writeAttribRaw( _name = 'visibleToCamera', _value= 'false')


    ### Trying storing the UsdLux in dictionary, is this wiser than just using UsdPrim which is used elsewhere
    def writeLight( self, 
                    _prim=False,
                  ): 
        usdType = _prim.GetTypeName()
        uuid = oomUtil.uuidSanitize( _prim.GetName(), _hashSeed = _prim.GetPath())

        local_mat4 = np.array( [[ 1,0,0,0],[ 0,-1,0,0],[ 0,0,-1,0],[ 0,0,0,1]], dtype='float64') 
        if _prim.GetAttribute( 'xformOp:transform' ).HasValue():
            usd_matrix4 = _prim.GetAttribute( 'xformOp:transform' ).Get( self.timeCode)
            l_mat4 = np.array( usd_matrix4, dtype='float64')  # convert to numpy for performance
            flipMat4 = np.array( [[ 1,0,0,0],[ 0,-1,0,0],[ 0,0,-1,0],[ 0,0,0,1]], dtype='float64') 
            local_mat4 = flipMat4 @ l_mat4

        ### 
        if usdType == 'SphereLight':
            ### Usd overloads pointLight in SphereLight
            usdLux = UsdLux.SphereLight( _prim)
            if usdLux.GetTreatAsPointAttr().Get() or usdLux.GetRadiusAttr().Get() == 0:
                bellaType = 'pointLight' 
            else:
                bellaType = 'sphereLight' ### no such bella type, need to create sphere
        elif usdType == 'RectLight':
            bellaType = 'areaLight'
            usdLux = UsdLux.RectLight( _prim)
        elif usdType == 'DiskLight':
            bellaType = 'areaLight'
            usdLux = UsdLux.DiskLight( _prim)
        elif usdType == 'DomeLight':
            bellaType = 'imageDome'
            usdLux = UsdLux.DomeLight( _prim)
        elif usdType == 'DistantLight':
            bellaType = 'directionalLight'
            usdLux = UsdLux.DistantLight( _prim)
        #elif usdType == 'SpotLight':
        #    bellaType = 'spotLight'
        else: return

        if not bellaType == 'sphereLight':
            ### Need to insert a intermediate xform to 180 rotate light, easier to do here rather than the generic xform pass
            ### - [ ] USD is -z, Bella is +z TODO bake this into parent xform, maybe do matrix accumulation before writing out xforms
            self.writeNode( _type = 'xform', _uuid = uuid)
            self.writeAttribString( _name = 'name', _value= uuid + '_flip')
            uuid += '_l' # xform gets OG name, light gets _l name
            self.writeAttribRaw( _name = 'children[*]', _value = uuid)
            self.writeAttribNumpy( _name='steps[0].xform',
                                   _type='mat4',
                                   _bracket='(',
                                   _nparray = local_mat4,
                                 )
            self.writeAttribRaw( _name = 'renderFlags', _value = 'oomRenderHide')

        else: ### special case to crete an emitter material on a sphere primitive
            ### Bella areaLight is constructed internally with an emitter materials
            ### intensity * multiplier * 8 
            emitteruuid = uuid + 'emitter'
            self.writeNode( _type = 'emitter', _uuid = emitteruuid)
            l_intensity = usdLux.GetIntensityAttr().Get( self.timeCode)
            lumenCalc = l_intensity * 30000 * 8
            modColor = list( usdLux.GetColorAttr().Get( self.timeCode))
            modColor.append( 1) #vec3 -> vec4
            self.writeAttribNumpy( _name = 'color',
                                   _type = 'rgba',
                                   _bracket = '(',
                                   _nparray = np.array( modColor),
                                 )
            self.writeAttribFloat( _name = 'intensity', _value = l_intensity)
            self.writeAttribFloat( _name = 'energy', _value = lumenCalc)
 
            self.writeNode( _type = 'xform', _uuid = uuid)
            self.writeAttribString( _name = 'name', _value= uuid + '_xform')
            sphereuuid = uuid + '_sphere' # xform gets OG name, light gets _sphere name
            self.writeAttribRaw( _name = 'children[*]', _value = sphereuuid)
            self.writeAttribNumpy( _name = 'steps[0].xform',
                                   _type = 'mat4',
                                   _bracket = '(',
                                   _nparray = local_mat4,
                                 )
            #self.writeAttribRaw( _name = 'renderFlags', _value = 'oomRenderHide')
            self.writeAttribRaw( _name = 'material', _value= emitteruuid)
            self.writeNode( _type = 'sphere', _uuid = sphereuuid)
            l_radius = usdLux.GetRadiusAttr().Get( self.timeCode)
            self.writeAttribFloat( _name = 'radius', _value = l_radius)
            return

        self.writeNode( _type = bellaType, _uuid = uuid)
        ### UsdLux common attributes
        if usdType in [ 'SphereLight', 'DistantLight', 'RectLight', 'DiskLight']:
            l_intensity = usdLux.GetIntensityAttr().Get( self.timeCode)
            modColor = list(usdLux.GetColorAttr().Get( self.timeCode))
            modColor.append(1)
            self.writeAttribNumpy( _name = 'color',
                                    _type = 'rgba',
                                    _bracket = '(',
                                    _nparray = np.array( modColor),
                                    )
            self.writeAttribFloat( _name = 'intensity', _value = l_intensity)
            #self.writeAttribRaw( _name = 'renderFlags', _value = 'oomRenderHide')
            
        if bellaType == "pointLight":
            self.writeAttribFloat( _name = 'radius', _value = 0.0)

        ### TODO why am I multiplying by such a large amount? Scene scale
        if bellaType == "directionalLight":
            angle = usdLux.GetAngleAttr().Get( self.timeCode )
            self.writeAttribFloat( _name = 'size', _value = angle)
        elif bellaType in ('areaLight', 'pointLight'): 
            self.writeAttribFloat( _name = 'multiplier', _value = 30000)

        if bellaType == 'imageDome':
            sdfAssetPath = usdLux.GetTextureFileAttr().Get()
            absFilePath = sdfAssetPath.resolvedPath ### total API confusion, this attrib not documented, got by trying to use GetResolvedPath() and API suggested resolvedPath
            relFilePath = sdfAssetPath.path
            ### My newbie c++ brain finally figured out that .path and .resolvedPath
            ### SDF_API SdfAssetPath ( const std::string & 	path,
            ###                        const std::string & 	resolvedPath 
            ###                      )	
            ### TODO - [ ] change this hardcoded transform with UsdLux DomeLight transform
            self.writeAttribRaw( _name = 'xform', _value = 'mat3(-1 0 -0 -0 -1 0 0 0 1)')
            if ( self.bsaFile.parent != Path( absFilePath)): ### Use relative path unless in same dir
                fileDome = Path( absFilePath)
            else:
                fileDome = Path( relFilePath)
            self.writeImageDome( fileDome)
            self.imageDome = uuid

        ### TODO Blender 3.6 USD only exports spotlight xform, there is no UsdLux.SpotLight
        ### TODO add -blenderspotlighthack: xforms with a certain name, or a custom attrib are a proxy for UsdLux.Spotlight
        if bellaType == 'spotLight':
            self.writeAttribFloat( _name = 'aperture', _value = 100)
            self.writeAttribFloat( _name = 'penumbra', _value = 4)
            self.writeAttribFloat( _name = 'radius', _value = 1.9)

        ###
        if bellaType == 'areaLight':
            if usdType == "DiskLight":
                self.writeAttribString( _name = 'shape', _value = 'disk')
                l_size = usdLux.GetRadiusAttr().Get() ### TODO erroneously Blender outputs diameter size 2 as  float inputs:radius = 2 
                self.writeAttribFloat( _name = 'sizeX', _value = l_size) # DiskLight supports circle only areaLight supports ovals
                self.writeAttribFloat( _name = 'sizeY', _value = l_size) 
            else: ### - [x] UsdLux.RectLight distinct from UsdLux.DiskLight, unlike Bella areaLight
                textureFile = usdLux.GetTextureFileAttr().Get()
                self.writeAttribFloat( _name = 'sizeX', _value = usdLux.GetWidthAttr().Get())
                self.writeAttribFloat( _name = 'sizeY', _value = usdLux.GetHeightAttr().Get())
    ###
    def writeEmitter2(self):
        self.writeNode( _type = 'emitter', _uuid = 'emitter')
        self.writeAttribRaw( _name = 'color', _value = 'rgba(0.502886474133 0.450785845518 0.036889452487 1)')
        self.writeAttribFloat( _name = 'energy', _value = 10000)
    ###
    def close(self, _usdScene):
        self.writeSettings()
        self.writeUsdRoot() # the usd scene is stored under this single xform
        self.writeWorld()
        self.file.close()
