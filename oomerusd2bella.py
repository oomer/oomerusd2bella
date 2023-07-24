### Convert Pixar .usd to Diffuse Logic's .bsa

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

### NOTES
###======
# USD provides an industrial level API and this humble converter piggybacks on a subset of features
# Only simple composition arcs
# Overwrites existing bsa's
# all external file references are collapsed, this is a foundational USD feature called composition arcs
# udim splitting is way more complicated than originally planned

### FEATURES
###=========
# - [ x ] ngons triangulated for Bella
# - [ x ] shared vertices split for Bella
# - [ x ] explicit texcoord and normals indices ( mostly Maya )
# - [ x ] transform anim
# - [ x ] mesh deformation anim
# - [ x ] converts Sdf.AssetPaths to relative path ( file textures only)
# - [ partial ] colorDome
# - [ partial ] imageDome
# - [ better ] UsdPreviewSurface -> Bella uber
# - [ alpha ] UsdLux SphereLight, AreaLight( rectLight, diskLight), DiskLight
# - [ partial ] UsdCamera -> Bella camera
# - [ partial ] Usd mesh instancing -> Bella mesh instancing

### NOTES
###======
# - [x] when no camera is found, an arbitrary one is created
# - [x] spotlight may not exist in Usd.Lux

### TODO
###===== 
# - [ ] split mesh along udim seams   
# - [ ] partial MaterialX translator
# - [ ] partial Nvidia MDL translator
# - [ ] Usd prim variants
# - [ ] per mesh prim subdivision, not sure where flag is

### NO SUPPORT
###===========
# -[ ] udim txcoords and maps, as seen in Animal Logic alab.usd

# standard modules
from pathlib import Path  # for cross platform file paths
import time
import argparse

# third party modules
import numpy as np

# oomer modules
import OomerUsd     as oomUsd   # USD read routines
import OomerBella   as oomBella # Bella write routines

parser = argparse.ArgumentParser( "oomerusd2bella")
parser.add_argument( 'usdfile', help = "path to usd file", default = "./usd/rubbertoy.usda", type = str)
parser.add_argument( '-start', dest = "start", help = "sequence start frame", default = 0, type = int)
parser.add_argument( '-end', dest = "end", help = "sequence end frame", default = 0, type = int)
parser.add_argument( '-debug', action = 'store_true') 
parser.add_argument( '-usda', help = "output usda", action = 'store_true')
parser.add_argument( '-colordome', help = "insert white color dome", action = 'store_true')
parser.add_argument( '-ignorelights', help = "ignorelights", action = 'store_true')
parser.add_argument( '-ignorematerials', help = "ignorematerials", action = 'store_true')
parser.add_argument( '-subdivision', dest = "subdivision", help="force subdivision level", default = 0, type = int)
parser.add_argument( '-ignoreroughness', help = "ignore specular roughness", action = 'store_true')

args = parser.parse_args()
start_time=time.time()
usdFile = Path( args.usdfile)

if not usdFile.exists():
    print( args.usdFile, "does not exist")
    quit()
if not usdFile.suffix in [ '.usd', '.usdc', '.usda', '.usdz']:
    print( args.usdFile, "is not a .usd, .usdc, .usda or .usdz file")
    quit()

usdScene = oomUsd.Reader( _usdFile = usdFile, 
                          _debug = args.debug,
                          _usda = args.usda,
                        )

# USD can store animations both transforms and mesh deformations
# when no start frame is defined, .bsa is output on frame 1
if args.start==0: startFrame,endFrame,isSequence = 1, 1, False
else:
    startFrame,isSequence = args.start, True
    if args.end < args.start: endFrame = startFrame
    else: endFrame = args.end

endFrame += 1 # Python range end not inclusive, requires end to be +1
for timeCode in range( startFrame, endFrame, 1):  # usd timecode starts on frame 1 not 0
    if isSequence:
        bsaDire = usdFile.parent.joinpath( str( usdFile.stem)+'_bsa')  # use subdir for output, helps organize sequences
        bsaFile = Path( usdFile.stem + str( timeCode).zfill(5) + '.bsa')
        bsa = oomBella.SceneAscii( _bsaFile = bsaDire / bsaFile, 
                                   _usdScene = usdScene, 
                                   _colorDome = args.colordome
                                 ) 
    else:
        bsaFile = Path( usdFile.name ).with_suffix( '.bsa')
        bsa = oomBella.SceneAscii( _bsaFile = usdFile.parent / bsaFile, 
                                   _usdScene = usdScene,
                                   _colorDome = args.colordome
                                 )

    # discovery pass for prims
    # Work done by oomUSD class in OomerUSD module
    # - [ ] filter by purpose, USD allows for non renderable meshes, default for Bella to render ALL meshes
    # - [ ] I believe that prototype prims were birthed at origin
    # - [ ] document thsi better, not sure what False means
    usdScene.traverseScene( filter_by_purpose=False)

    ### MESH 
    ###=====
    for prim in usdScene.meshes.keys():
        if usdScene.debug: 
            print( 'usd mesh:', prim)
            npFaceVertexCount, \
            npFaceVertexIndices, \
            npPoints, \
            npNormals, \
            npTxcoords, \
            = usdScene.getMesh( _prim = prim, _timeCode = timeCode)
        else:
            try: # Bypass prims that crash with calls to pxr API 
                npFaceVertexCount, \
                npFaceVertexIndices, \
                npPoints, \
                npNormals, \
                npTxcoords \
                = usdScene.getMesh( _prim = prim, _timeCode = timeCode)
                if not isinstance( npFaceVertexCount, np.ndarray): continue # return var == False indicates BAD ( ie zero faces ) geometry .. skip
            except:
                if usdScene.debug: print( "FAIL:", prim, 'ERROR')
                continue

        # isinstance(x,y) Python function to check if x is of object type y
        if isinstance( npFaceVertexCount, np.ndarray): 
            if usdScene.debug: 
                print( '\tnpFaceVertexCount', len( npFaceVertexCount))
        if isinstance( npFaceVertexIndices, np.ndarray):
            if usdScene.debug: 
                print( '\tnpFaceVertexIndices', len( npFaceVertexIndices))
        if isinstance( npPoints, np.ndarray):
            if usdScene.debug: 
                print( '\tnpPoints', len( npPoints))
        if isinstance( npNormals, np.ndarray):
            if usdScene.debug: 
                print( '\tnpNormals', len( npNormals))
        if isinstance( npTxcoords, np.ndarray):
            if usdScene.debug: 
                print( '\tnpTxcoords', len( npTxcoords))

        ### MATERIALS
        ###==========
        if 'material_prim' in usdScene.meshes[ prim]:
            materialPrim = usdScene.meshes[ prim][ 'material_prim'] 
        else: materialPrim = False
        if not usdScene.meshes[ prim][ 'instance']:
            bsa.writeMesh( prim,
                        npFaceVertexCount,
                        npFaceVertexIndices,
                        npPoints,
                        npNormals,
                        npTxcoords,
                        timeCode,
                        materialPrim,
                        usdScene.xform_cache,
                        args.subdivision,
                        args.colordome,
                        )
        else:
            bsa.writeInstance( prim,
                               usdScene.meshes[ prim][ 'instance']
                             )

    ### LIGHTS 
    ###=======
    if not args.ignorelights:
        for prim in usdScene.lights.keys():
            bsa.writeLight( _lightDict = usdScene.lights[ prim], 
                            _timeCode = timeCode)

    ### CAMERA
    ###=======
    ### [ 2024 ] Use extents to frame scene
    if not usdScene.cameras: 
        bsa.writeOomerCamera()
    for prim in usdScene.cameras.keys(): bsa.writeCamera( prim, timeCode)

    ### XFORM
    ###======
    for prim in usdScene.xforms.keys():
        bsa.writeXform( _prim = prim,
                        _usdScene = usdScene,
                        _timeCode = timeCode,
                      )

    ### USDPREVIEWSURFACE
    ###==================
    if not args.ignorematerials:
        for prim in usdScene.previewSurfaces.keys():  
            bsa.writeUberMaterial(  _prim = prim, 
                                    _usdScene = usdScene,
                                    _ignoreRoughness = args.ignoreroughness,
                                 )

    ### USDUVTEXTURE
    ###============= 
    ### usd file string surrounded by @
    for shader in usdScene.uv_textures.keys(): 
        bsa.writeShaderTexture( shader, 
                                usdScene.uv_textures[ shader][ 'file'], 
                              )

    # not sure how I can tell that a file is used as a normalmap
    #for usd_prim in usdScene.uv_textures.keys(): # write out usd uv textures as bella file textures
    #    bsa.write_normal_texture(   usd_prim, 
    #                                str(usdScene.uv_textures[ usd_prim ][ 'file' ])[ 1:-1 ], 
    #                            )

    bsa.close( usdScene)
execution_time = ( time.time() - start_time)
if usdScene.debug: print( 'Execution time in seconds', execution_time)
