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

## standard modules
from pathlib import Path  # used for cross platform file paths

## oomer modules
import OomerUtil as oomUtil

class SceneAscii:
    def __init__( self, out_file, 
                  usd_stage,
                  debug = False,
                  _colorDome = False,
                ):
        if not out_file.parent.exists():
            out_file.parent.mkdir()
        self.file = open( str( out_file), 'w')
        self.renderer_up_axis = 'Z'
        self.world_nodes = []
        self.stage = usd_stage
        self.image_dome = False
        self.colorDome = _colorDome
        self.debug = debug

        self.writeHeader()
        self.writeGlobal()
        self.writeState()
        self.writeBeautyPass()
        self.writeGroundPlane()
        self.camera = ''
        u = self.stage.meters_per_unit  
        if self.stage.up_axis == self.renderer_up_axis: # up axis matches Bella
            _basis_change_mat4 = [[ u, 0, 0, 0],
                                  [ 0, u, 0, 0],
                                  [ 0, 0, u, 0],
                                  [ 0, 0, 0, 1]]
        else:
            _basis_change_mat4 = [[ u, 0, 0, 0],
                                  [ 0, 0, u, 0],
                                  [ 0, -u, 0, 0],
                                  [ 0, 0, 0, 1]]
        self.np_basis_change_mat4 = np.array( _basis_change_mat4 )

        oomerUtility = oomUtil.Mappings()
        self.usdPreviewSurface = oomerUtility.usdPreviewSurface

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
    def writeBeautyPass( self):
        self.file.write('beautyPass beautyPass;\n')
    ##
    def writeSkyDome( self):
        self.file.write('skyDome skyDome;\n')
    ##
    def writeBox( self, _sizeX = 1, _sizeY = 1, _sizeZ = 1, _radius = 0):
        self.file.write('box box:\n')
        self.file.write(self.nice('radius') + str( _radius) + 'f;\n')
        self.file.write(self.nice('sizeX') + str( _sizeX) + 'f;\n')
        self.file.write(self.nice('sizeY') + str( _sizeY) + 'f;\n')
        self.file.write(self.nice('sizeZ') + str( _sizeZ) + 'f;\n')
    ##
    def writeColor( self, _rgba=( 1, 1, 1, 1), _variation=0):
        self.file.write('color color:\n')
        self.file.write( self.nice( 'color') + 
                                    'rgba(' + 
                                    str( _rgba[0]) + ' ' + 
                                    str( _rgba[1]) + ' ' + 
                                    str( _rgba[2]) + ' ' + 
                                    str( _rgba[3]) + ');\n'
                       )
        self.file.write(self.nice('variation') + str( _variation) + 'f;\n')
    ##
    def writeNodeAttrib( self, _name = False, _connected = False, _value = False):
        if _connected:
            self.file.write('  .' + f'{_name:26}' + '|= ' + _value + ';\n')
        else:
            self.file.write('  .' + f'{_name:27}' + '= ' + _value + ';\n')

    def writeFloat( self, _name = False, _value= 1.0):
        self.file.write(self.nice(_name) + str( _value) + 'f;\n')

    def writeNode( self, _type = False, _uuid = False):
        self.file.write( _type + ' ' + _uuid + ':\n')

    def writeNodeAttribNumpy( self,
                              _name = False,
                              _type = False,
                              _nparray = False,
                              _lbracket = '{',
                              _rbracket = '}',
                            ):
        #https://stackoverflow.com/questions/53820891/speed-of-writing-a-numpy-array-to-a-text-file
        #Assumed numpy.savetxt was performant, it is not! Saving 0020_060 Sprite fright went from 4 minutes to 1 minute
        self.file.write(self.nice(_name) + _type)
        self.file.write( _lbracket)
        npArray = _nparray.ravel() # - [ ] doc
        npFormat = ' '.join(['%g'] * npArray.size) #- [ ] document npFormat
        npFormat = '\n'.join([ npFormat])
        data = npFormat % tuple( npArray )
        self.file.write( data)
        self.file.write( _rbracket)
        self.file.write( ';\n')

    def writeCamera( self, _usd_prim, _time_code):
        uuid = oomUtil.uuidSanitize( _usd_prim.GetName(), _hashSeed = _usd_prim.GetPath() )
        self.camera = uuid

        if _usd_prim.GetAttribute( 'horizontalAperture').HasValue():
            horizontal_aperture = _usd_prim.GetAttribute( 'horizontalAperture').Get( time = _time_code)
        else:
            horizontal_aperture = 36
        if _usd_prim.GetAttribute( 'horizontalApertureOffset').HasValue():
            horizontal_aperture_offset = _usd_prim.GetAttribute( 'horizontalApertureOffset').Get( time = _time_code)
        else:
            horizontal_aperture_offset = 0
        if _usd_prim.GetAttribute( 'verticalAperture').HasValue():
            vertical_aperture = _usd_prim.GetAttribute( 'verticalAperture').Get(time = _time_code)
        else:
            vertical_aperture = 24
        if _usd_prim.GetAttribute( 'verticalApertureOffset').HasValue():
            vertical_aperture_offset = _usd_prim.GetAttribute( 'verticalApertureOffset').Get( time = _time_code)
        else:
            vertical_aperture_offset = 0
        if _usd_prim.GetAttribute( 'projection').HasValue():
            projection = _usd_prim.GetAttribute( 'projection').Get( time = _time_code)
        else:
            projection = 'PERSPECTIVE'

        if _usd_prim.GetAttribute( 'focalLength').HasValue():
            focal_length = _usd_prim.GetAttribute( 'focalLength').Get(time = _time_code)
        else:
            focal_length = 50

        if _usd_prim.GetAttribute( 'aspectRatio').HasValue():
            pixel_aspect = _usd_prim.GetAttribute( 'aspectRatio').Get( time = _time_code)
        else:
            pixel_aspect = 1.0

        if _usd_prim.GetAttribute( 'focusDistance').HasValue():
            x = _usd_prim.GetAttribute( 'focusDistance').Get( time = _time_code)
            if x !=0: # [ ] blender does not export a focus distance to USDA
                focus_distance = x
            else:
                focus_distance = 0.877
        else:
            focus_distance = 0.877
        if _usd_prim.GetAttribute( 'fStop').HasValue():
            fstop = _usd_prim.GetAttribute( 'fStop').Get( time = _time_code)
        else:
            fstop = 8
        if fstop == 0:
            fstop = 8

        nSteps = 1
        shutter = 250
        iso = 100
        diaphragmType = "CIRCULAR"
        angle = 60  #bokeh POLYGONAL
        nBlades = 6 #bokeh POLYGONAL
        fps = int( self.stage.timecodes_per_second)
        xRes = 1280
        yRes = 720
        #_lens_type = TYPE_THIN_LENS

        # Bella camera node
        self.writeNode( _type = 'camera', _uuid = uuid )
        self.writeNodeAttrib( _name = 'lens', _value = uuid + '_thinLens')
        self.writeNodeAttrib( _name = 'resolution',
                              _value = 'vec2( ' + str( xRes ) + ' ' + str( yRes ) + ' )',
                            )
        self.writeNodeAttrib( _name = 'sensor', _value = uuid + '_sensor')
        self.writeNodeAttrib( _name = 'ev', _value = '13.5f')
        self.writeSensor( uuid, horizontal_aperture, vertical_aperture)
        self.writeThinLens( uuid, focus_distance, focal_length, fstop)
        self.writeCameraXform( uuid, _usd_prim, _time_code)

    def writeSensor( self, _uuid, _horizontal_aperture, _vertical_aperture):
        self.writeNode( _type = 'sensor', _uuid = _uuid + '_sensor')
        self.writeNodeAttrib( _name='size',
                              _value='vec2(' + str( _horizontal_aperture * self.stage.cam_unit_scale) +
                                            ' ' +
                                            str( _vertical_aperture * self.stage.cam_unit_scale) +
                                          ')'
                            )

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
        self.writeNodeAttrib( _name = 'steps[0].fStop', _value = str(_fStop) + 'f')
        self.writeNodeAttrib( _name = 'steps[0].focalLen', _value=str( _focalLength * self.stage.cam_unit_scale) + 'f')
        self.writeNodeAttrib( _name = 'steps[0].focusDist', _value = str( _focusDistance * self.stage.cam_unit_scale) + 'f')
        self.writeNodeAttrib( _name = 'aperture.blades', _value = str( _nBlades) + 'u')
        self.writeNodeAttrib( _name = 'aperture.rotation', _value = str( _angle) + 'f')
        self.writeNodeAttrib( _name = 'aperture.shape', _value = '"' + str( _diaphragmType) + '"')

    def writeCameraXform( self, _uuid, _usd_prim, _time_code):
        uuidXform = _uuid + 'Xform'
        self.world_nodes.append( uuidXform) 
        self.writeNode( _type = 'xform', _uuid = uuidXform)
        self.writeNodeAttrib( _name = 'name',
                              _value = '"' + uuidXform + '"',
                            )
        self.writeNodeAttrib( _name = 'children[*]',
                              _value = _uuid,
                            )

        self.stage.xform_cache.SetTime( _time_code) #if cache time is unset it uses DEFAULT which is always going to be wrong
        np_matrix4 = np.array( self.stage.xform_cache.GetLocalToWorldTransform( _usd_prim),
                              dtype='float64')  # get CTM for camera

        np_bella = np_matrix4 @ self.np_basis_change_mat4  # transform camera CTM in DCC coordsys to bella coordsys
        np_bella[1] *= -1  # Flip Bella y axis
        np_bella[2] *= -1  # Flip Bella z axis

        np_matrix4_1d = np_bella.ravel()  # 1-D array copy of the elements of an array in row-major order
        self.writeNodeAttribNumpy( _name = 'steps[0].xform',
                                   _type = 'mat4',
                                   _nparray = np_matrix4_1d,
                                   _lbracket = '(',
                                   _rbracket = ')',
                                 )

    def writeMesh( self, 
                   _usdPrim, 
                   _npVertexCount,
                   _npVertexIndices, 
                   _npPoints, 
                   _npNormals, 
                   np_texcoords_vertex_buffer, 
                   time_code,
                   material_prim,
                   xform_cache,
                   subdivision,
                   _colordome,
                  ):
        # Along with a mesh, this function inserts an xform node to
        # 1. capture usd's gprim's ability to hold a transfrom
        # 2. to hold onto any materials
        # 3. because no xform attribute exists on Bella's mesh node

        if _colordome: self.colorDome=True

        ####type_name = usd_prim.GetTypeName()
        primName = _usdPrim.GetName()
        uuid = oomUtil.uuidSanitize( _usdPrim.GetName(), _hashSeed = _usdPrim.GetPath())
        if material_prim:
            material_name = oomUtil.uuidSanitize( material_prim.GetName(), _hashSeed = material_prim.GetPath())
        else:
            material_name = "None"

        np_matrix4 = np.array( xform_cache.GetLocalTransformation( _usdPrim)[0])
        # INSERT XFORM 
        # the name of xform should be the same as usd gprim
        # this way the GetChildren() query done anywhere will be correct
        # since we create intermediate xforms here, renaming the gprim is easy 
        self.writeNode( _type = 'xform',
                        _uuid = uuid,
                       )
        self.writeNodeAttrib( _name = 'name', _value= '"' + primName + '"')
        uuid += '_m' # xform gets OG name, mesh gets _mesh name
        np_matrix4_1d = np_matrix4.ravel()  # reshape [[a1, b1, c1, d1],[a2, b2, c2, d2]] to [(a1 b1 c1 d1 a2 b2 c2 d2)] for np.savetxt
        self.writeNodeAttrib( _name = 'children[*]', _value = uuid)
        self.writeNodeAttribNumpy( _name='steps[0].xform',
                                   _type='mat4',
                                   _lbracket='(',
                                   _nparray=np_matrix4_1d,
                                   _rbracket=')',
                                 )
        self.writeNodeAttrib( _name = 'material',       
                              _value=material_name,
                            )

        self.writeNode( _type = 'mesh', _uuid = uuid)
        self.writeNodeAttrib( _name = 'name', _value = '"' + primName + '"')
        self.writeNodeAttribNumpy( _name = 'polygons',
                                   _type = 'vec4u[' + str( _npVertexCount.size) + ']',
                                   _nparray = _npVertexIndices,
                                 )

        numRows, _ = _npPoints.shape
        self.writeNodeAttribNumpy( _name = 'steps[0].points',
                                   _type = 'pos3f[' + str( numRows) + ']',
                                   _nparray = _npPoints,
                                 )

        self.writeNodeAttribNumpy( _name = 'steps[0].normals',
                                   #_type = 'vec3f[' + str( len( _npNormals)) + ']',
                                   _type = 'vec3f[' + str( _npNormals.size) + ']',
                                   _nparray = _npNormals,
                                 )
    
        try:
            if isinstance( np_texcoords_vertex_buffer, np.ndarray): # fail on non np.ndarray
                self.writeNodeAttribNumpy( _name = 'steps[0].uvs',
                                           _type = 'vec2f[' + str( np_texcoords_vertex_buffer.shape[0] ) + ']',
                                           _nparray=np_texcoords_vertex_buffer,
                                         )
        except:
            if self.debug: print( 'FAIL writeMesh()', uuid)

        if subdivision > 0:
            self.writeNodeAttrib(  _name = 'subdivision.level',       
                                   _value=str( subdivision)+'u',
                                )

        ### Bella flag to skip mesh optimization 
        #self.writeNodeAttrib( attribute_name = 'optimized',       
        #                           attribute_value='true',
        #                         )

    #2024 refactored
    # - [ ] USD mesh nodes have an optional xform attribute, Bella mesh nodes don't
    # - [ ] is time code even needed
    def writeXform( self, 
                    _usdPrim, 
                    _usdScene
                  ):
        
        # Workaround to get useful name from Animal Logic prototype
        primName = _usdPrim.GetName() # no wackiness here
        alusd_name = False 
        if _usdPrim in _usdScene.prototype_children: # Spelunk and try to find useful name  
            alusd_name = _usdPrim.GetAttribute( 'alusd_originalName').Get() # [ ] GetName() gives us a useless "GEO" name, original name much more relevant
            if isinstance( alusd_name, str): prim_name = alusd_name  
        name = oomUtil.uuidSanitize( primName, _hashSeed = _usdPrim.GetPath() ) 

        np_matrix4 = np.array( self.stage.xform_cache.GetLocalTransformation( _usdPrim)[0]) #flatten transforms to mat4

        self.writeNode( _type = 'xform', _uuid = name)
        self.writeNodeAttrib( _name = 'name',
                              _value = '"' + primName + '"',
                            )

        # - [2024] document prototypes and test 
        # - add unit tests
        if _usdPrim in _usdScene.prototype_instances: 
            # handler for top level prototype prims, ie the NS:GEO node in Animal Logic Assets
            childPrim = _usdScene.prototype_instances[ _usdPrim]
            if childPrim:
                alusd_name = childPrim.GetAttribute( 'alusd_originalName').Get()
                if isinstance( alusd_name, str):
                    childName = oomUtil.uuidSanitize( alusd_name, _hashSeed = childPrim.GetPath())
                else:
                    childName = oomUtil.uuidSanitize( childPrim.GetName())
                self.writeNodeAttrib( _name = 'children[*]',
                                      _value = childName,
                                    )

        else:  # normal workflow, including children of toplevel prototype prims
            for childPrim in _usdPrim.GetChildren():
                childName = oomUtil.uuidSanitize( childPrim.GetName(), _hashSeed = childPrim.GetPath())
                if childPrim in _usdScene.meshes: # is mesh?
                    self.writeNodeAttrib( _name = 'children[*]', _value = childName)
                else: # add non mesh child
                    self.writeNodeAttrib( _name = 'children[*]', _value = childName)

        #if usd_matrix4:
        # usd stores matrix in row major order
        # numpy scipy does column major order
        # transform3d
        # ax, ay, az = pokadot_transform3d.mat2euler(np_matrix4[:3, 0:3]) # convert rotation matrix portion to euler
        # rotate_mxs = Cvector(math.degrees(ax), math.degrees(ay), math.degrees(az))
        # reshape [(a1 b1 c1 d1),(a2 b2 c2 d2)] to [(a1 b1 c1 d1 a2 b2 c2 d2)] for np.savetxt
        #np_matrix4_1d = np_matrix4.flatten()  # 1-D array copy of elements of array in row-major order
        np_matrix4_1d = np_matrix4.ravel()  # 1-D array copy of elements of array in row-major order
        self.writeNodeAttribNumpy( _name = 'steps[0].xform',
                                   _type = 'mat4',
                                   _nparray = np_matrix4_1d,
                                   _lbracket = '(',
                                   _rbracket = ')',
                                 )

    def writeSettings( self ):
        self.writeNode( _type = 'settings', _uuid = 'settings' )
        self.writeNodeAttrib( _name = 'beautyPass', _value = 'beautyPass' )

        if self.camera: 
            self.writeNodeAttrib( _name ='camera', _value =self.camera ) # - why use self.camera
        if self.colorDome:
            self.writeNodeAttrib( _name = 'environment', _value = "colorDome" )
        self.writeNodeAttrib( _name = 'iprScale', _value = '100f' )
        self.writeNodeAttrib( _name = 'threads', _value = '-1' )
        self.writeNodeAttrib( _name = 'useGpu', _value = 'true' )
        self.writeNodeAttrib( _name = 'iprNavigation', _value='"maya"' )
        if self.colorDome: self.writeColorDome()
    
    def writeColorDome( self ):
        self.writeNode( _type = 'colorDome', _uuid = 'colorDome' )

    def writeImageDome( self, extension, directory, file ):
        # Bella imageDome node
        self.writeNodeAttrib( _name = 'ext',
                              _value = '"'+extension[1:]+'"',
                            )
        self.writeNodeAttrib( _name = 'dir',
                              _value = '"../'+str(directory)+'"',
                            )
        self.writeNodeAttrib( _name = 'file',
                              _value = '"'+file+'"',
                            )

    def writeOomerCamera( self ):
        #Convenience helper to add a default camera when .usd has none
        focal_length        = 20
        focus_distance      = 0.877 # [ ] use scene extents to calc
        horizontal_aperture = 36
        vertical_aperture   = 24
        fstop               = 8
        camera_name         = 'oomerCamera'
        self.camera = camera_name
        self.world_nodes.append(camera_name+'_xform')
        self.file.write( 'xform '+camera_name+'_xform:\n' )
        self.file.write('  .name                    = "' + camera_name + '_xform";\n' )
        self.file.write('  .children[*]             = ' + camera_name + ';\n' )
        self.file.write('  .steps[0].xform          = mat4(1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1);\n')

        self.file.write('camera ' + camera_name + ':\n' )
        self.file.write('  .lens                    = ' + camera_name+'_thinLens;\n' )
        self.file.write('  .resolution              = vec2(1920 1080);\n' )
        self.file.write('  .sensor                  = ' + camera_name + '_sensor;\n' )

        self.file.write('sensor '+camera_name+'_sensor:\n')
        self.file.write('  .size                    = vec2(' + str( horizontal_aperture ) + ' ' + str ( vertical_aperture ) + ');\n' )

        self.file.write( 'thinLens ' + camera_name + '_thinLens:\n' )
        self.file.write( '  .steps[0].fStop          = ' + str( fstop )+'f;\n' )
        self.file.write( '  .steps[0].focalLen       = ' + str( focal_length )+'f;\n' )
        self.file.write( '  .steps[0].focusDist      = ' + str( focus_distance )+'f;\n' )

    def writeUsdRoot(self, _usdScene):
        uuid = oomUtil.uuidSanitize( self.stage.file.stem) + '_usd'
        self.writeNode( _type = 'xform', _uuid = uuid)
        self.world_nodes.append( uuid )
        for node_uuid in _usdScene.root_prims:
            self.writeNodeAttrib( _name = 'children[*]', _value = node_uuid)
        self.writeNodeAttribNumpy( _name = 'steps[0].xform',
                                   _type = 'mat4',
                                   _nparray = self.np_basis_change_mat4,
                                   _lbracket = '(',
                                   _rbracket = ')',
                                 )

    def writeWorld(self):
        self.writeNode( _type = 'xform', _uuid = 'world')
        for node_name in self.world_nodes:
            self.writeNodeAttrib( _name = 'children[*]', _value = node_name)
        self.writeNodeAttribNumpy( _name = 'steps[0].xform',
                                   _type = 'mat4',
                                   _nparray = self.stage.mat4_identity,
                                   _lbracket = '(',
                                   _rbracket = ')',
                                 )

    def writeFileTexture( self,
                          _usdPrim,
                          _filePath,
                        ):
        uuid = oomUtil.uuidSanitize( _usdPrim.GetName(), _hashSeed = _usdPrim.GetPath())
        self.writeNode( _type='fileTexture', _uuid = uuid)
        self.file.write( self.nice('dir')  + '"' + str( _filePath.parent)+'";\n' )
        self.file.write( self.nice('ext')  + '"' + str( _filePath.suffix) +'";\n' )
        self.file.write( self.nice('file') + '"' + str( _filePath.stem) +'";\n' )

    def writeNormalTexture( self,
                            _usdPrim,
                            _filePath,
                          ):
        uuid = oomUtil.uuidSanitize( _usdPrim.GetName(), _hashSeed = _usdPrim.GetPath()) + 'normalMap'
        self.writeNode( _type = 'normalMap', _uuid = uuid)
        bella_file = Path( _filePath)
        self.file.write( self.nice( 'dir')  + '"' + str( _filePath.parent) + '";\n')
        self.file.write( self.nice( 'ext')  + '"' + str( _filePath.suffix) + '";\n')
        self.file.write( self.nice( 'file') + '"' + str( _filePath.stem)   + '";\n')

    def writeUberMaterial( self,
                           _usdPrim,
                           _usdScene,
                         ):
        uuid = oomUtil.uuidSanitize( _usdPrim.GetName(), _hashSeed = _usdPrim.GetPath())
        self.writeNode( _type = 'uber', _uuid = uuid)

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
        # found UsdPreviewSurfaces were stored in a dictionary _usdScene.preview_surfaces
        # Python dict key is ( nodeInput or attribute, UsdPrim or null) 

        # _usdScene.usdPreviewSurface dictionary keys=shaderInputs val=bellaName
        for shaderInput in _usdScene.usdPreviewSurface:
            if ( shaderInput, 'connection_prim') in _usdScene.preview_surfaces[ _usdPrim]: # why did I use a tuple for the key, is this elegant or complicated
                # i think I used a tuple, rather than a string ie normal_connection_prim
                if shaderInput == 'normal':
                    outType = '.outNormal'
                    inputPrim = _usdScene.preview_surfaces[ _usdPrim][( shaderInput, 'connection_prim')]
                    inputName = oomUtil.uuidSanitize( inputPrim.GetName(), _hashSeed = inputPrim.GetPath())
                    inputName += 'normalMap'
                    self.writeNodeAttrib( _name = self.usdPreviewSurface[ shaderInput],
                                          _value = inputName + outType,
                                          _connected = True,
                                        )
                else: # directly connected fileTexure
                    if shaderInput == 'diffuseColor': outType = '.outColor'
                    else: outType = '.outAverage'
                    inputPrim = _usdScene.preview_surfaces[ _usdPrim][( shaderInput, 'connection_prim')]
                    inputName = oomUtil.uuidSanitize( inputPrim.GetName(), _hashSeed = inputPrim.GetPath())
                    self.writeNodeAttrib( _name = self.usdPreviewSurface[ shaderInput],
                                          _value = inputName + outType,
                                          _connected = True,
                                        )
            else:
                if shaderInput in _usdScene.preview_surfaces[ _usdPrim]:
                    if shaderInput != 'opacity': # opacity erroneously set to 1 should be 100
                        shaderValue = _usdScene.preview_surfaces[ _usdPrim][ shaderInput]
                        if type( shaderValue) == float:
                            self.writeFloat( _name = self.usdPreviewSurface[ shaderInput],
                                             _value = shaderValue,
                                           )
                        if shaderInput == 'diffuseColor': #pxr.Gf.Vec3f
                            self.writeNodeAttrib( _name = 'base.color',
                                                  _value = 'rgba(' + str( shaderValue[0]) +
                                                  ' ' +
                                                  str( shaderValue[1]) +
                                                  ' ' +
                                                  str( shaderValue[2]) +
                                                  ' 1 )'
                                                )
                        if shaderInput == 'roughness': 
                            self.writeNodeAttrib( _name = 'specular.roughness', _value = str( shaderValue * 100) + 'f' )

    def writeLight( self, 
                    _lightDict=False,
                    _timeCode=False,
                  ): 
        prim = _lightDict['UsdLux'].GetPrim()
        usdType = prim.GetTypeName()
        uuid = oomUtil.uuidSanitize( prim.GetName(), _hashSeed = prim.GetPath())

        local_mat4 = False
        localXform = _lightDict['UsdLux'].GetLocalTransformation # TODO switch low level prim query to UsdLux query
        if prim.GetAttribute( 'xformOp:transform' ).HasValue():
            usd_matrix4 = prim.GetAttribute( 'xformOp:transform' ).Get( time = _timeCode )
            local_mat4 = np.array( usd_matrix4, dtype='float64')  # convert to numpy for performance
            local_mat4 = local_mat4 * self.stage.mat4_light

        # 
        if usdType == 'SphereLight':    bellaType = 'pointLight' 
        elif usdType == 'RectLight':    bellaType = 'areaLight'
        elif usdType == 'DiskLight':    bellaType = 'areaLight'
        elif usdType == 'DomeLight':    bellaType = 'imageDome'
        elif usdType == 'DistantLight': bellaType = 'directionalLight'
        elif usdType == 'SpotLight':    bellaType = 'spotLight'
        else: return

        ### UsdLux common attributes
        l_color = np.array(_lightDict['UsdLux'].GetColorAttr().Get( time = _timeCode))
        l_intensity = _lightDict['UsdLux'].GetIntensityAttr().Get( time = _timeCode)
        l_visibility = _lightDict['UsdLux'].GetVisibilityAttr().Get() # needed?
        l_specular = _lightDict['UsdLux'].GetSpecularAttr().Get( time = _timeCode) # needed?

        ### Need to insert a intermediate xform to 180 rotate light, easier to do here rather than the generic xform pass
        ### - [ ] USD is -z, Bella is +z TODO bake this into parent xform, maybe do matrix accumulation before writing out xforms
        self.writeNode( _type = 'xform', _uuid = uuid)
        self.writeNodeAttrib( _name = 'name', _value= '"' + uuid + '_flip"')
        uuid += '_l' # xform gets OG name, light gets _l name
        flipMat4 = np.array( [[1,0,0,0],[0,-1,0,0],[0,0,-1,0],[0,0,0,1]], dtype='float64')  
        self.writeNodeAttrib( _name = 'children[*]', _value = uuid)
        self.writeNodeAttribNumpy( _name='steps[0].xform',
                                   _type='mat4',
                                   _lbracket='(',
                                   _nparray=flipMat4,
                                   _rbracket=')',
                                 )

        self.writeNode( _type = bellaType, _uuid = uuid )
        self.writeNodeAttribNumpy( _name = 'color',
                                   _type = 'rgba',
                                   _lbracket = '(',
                                   _nparray = np.array(l_color),
                                   _rbracket = ' 1 )',
                                 )
        self.writeNodeAttrib( _name = 'intensity', _value = str( l_intensity) + 'f',)
        
        if bellaType == "pointLight":
            l_radius = _lightDict['UsdLux'].GetRadiusAttr().Get( time = _timeCode)
            self.writeNodeAttrib(   _name = 'radius', _value = str( l_radius) +'f')

        # TODO why am I multiplying by such a large amount? Scene scale
        if bellaType == "directionalLight":
            angle = _lightDict['UsdLux'].GetAngleAttr().Get( time = _timeCode )
        else: ### Why skip distant light?
            self.writeNodeAttrib(   _name = 'multiplier', _value = '100000f')

        if bellaType == 'imageDome':
            textureFile = _lightDict['UsdLux'].GetTextureFileAttr().Get()
            fileDome = Path( textureFile)
            self.writeImageDome( fileDome.suffix, fileDome.parent, fileDome.stem)
            self.image_dome = uuid

        ### TODO Blender 3.6 USD only exports spotlight xform, there is no SpotLight prim
        ### can add a -blenderspotlighthack where xforms with a certain name, or a custom attrib
        if bellaType == 'spotLight':
            self.writeNodeAttrib( _name = 'aperture', _value = '100f')
            self.writeNodeAttrib( _name = 'penumbra', _value = '4f')
            self.writeNodeAttrib( _name = 'radius', _value = '1.9f')
        if bellaType == 'areaLight':
            if usdType == "DiskLight":
                self.writeNodeAttrib( _name = 'shape', _value = '"disk"')
                l_size = _lightDict['UsdLux'].GetRadiusAttr().Get() ### TODO erroneously Blender outputs diameter size 2 as  float inputs:radius = 2 
                self.writeNodeAttrib( _name = 'sizeX', _value = str( l_size) +'f') # DiskLight supports circle only areaLight supports ovals
                self.writeNodeAttrib( _name = 'sizeY', _value = str( l_size) +'f') 
            else: ### RectLight is distinct from DiskLight, merged in areaLight
                textureFile = _lightDict['UsdLux'].GetTextureFileAttr().Get()
                width = _lightDict['UsdLux'].GetWidthAttr().Get()
                height = _lightDict['UsdLux'].GetHeightAttr().Get()
                self.writeNodeAttrib( _name = 'sizeX', _value = str( width) +'f')
                self.writeNodeAttrib( _name = 'sizeY', _value = str( height) +'f')

    def close(self, _usd_scene):
        self.writeSettings()
        self.writeUsdRoot( _usd_scene ) # the usd scene is stored under this single xform
        self.writeWorld()
        self.file.close()
