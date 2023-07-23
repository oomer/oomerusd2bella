### oomer util module

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

# standard modules
import re
import hashlib

# added modules
import numpy as np

class Mappings:
    def __init__( self ):
        self.usdPreviewSurface = {'clearcoat':'thinMedium.color',
                                  'clearcoatRoughness':'thinMedium.scattering',
                                  'diffuseColor':'base.color',
                                  'metallic':'base.metallic',
                                  'emissiveColor':'trns.color',
                                  'ior':'ior',
                                  'normal':'normal',
                                  'occlusion':'occlusion',
                                  'displacement':'displacment',
                                  'opacity':'opacity',
                                  'roughness':'specular.roughness',
                                  'specular':'specular',
                                  }

def str_increment(s):
    reg_search = re.search(r'\d*(\D*)$', str(s))
    if reg_search:
        str_digits = reg_search.group()
        return s[0:reg_search.start()] + str(int(str_digits) + 1).zfill(len(str_digits))

def uuidSanitize(name, _hashSeed=None):
    # can be usd.GetPath() or a plain string
    node_name = str( name).split( '/')[ -1]
    # ensure identifier compliance
    #  Remove invalid characters
    s = re.sub('[^0-9a-zA-Z_]', '', node_name)
    # Remove leading characters until we find a letter or underscore
    s = re.sub('^[^a-zA-Z_]+', '', s)
    # [ ] figure out when to introduce str incrementing
    if _hashSeed:
        s = s + "_" + hashlib.sha1( str( _hashSeed).encode( 'utf-8')).hexdigest()[:8]
    return s

def normalize_vec3(npy_vec3):
    """ Normalize a np array of 3 component vectors shape=(n,3)
    Normalization of a vector is to scale it to length of 1
    Use Pythagoreom's thereom to calcuate length of vector
    square root the sum of each vector component squared
    np performantly does this without an explicit loop ( vectorization )
    """
    length_vector = np.sqrt(npy_vec3[:, 0] ** 2 + npy_vec3[:, 1] ** 2 + npy_vec3[:, 2] ** 2)
    # divide each component by length_vector to normalize it
    npy_vec3[:, 0] /= length_vector
    npy_vec3[:, 1] /= length_vector
    npy_vec3[:, 2] /= length_vector
    return npy_vec3
