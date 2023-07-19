## oomerusd2bella.py

> NOT production quality. This is a personal WIP project.

Using Pixar's USD open source library, oomerusd2bella.py is a Python program to convert a USD scene into a single Bella ascii .bsa file. 

```
oomerusd2bella.py = run me
OomerBella.py     = Bella write module
OomerUsd.py       = USD read module
OomerUtil.py      = oomer utility module
```

 - [ x ] ngons triangulated for Bella
 - [ x ] shared vertices split for Bella
 - [ x ] explicit texcoord and normals indices ( mostly Maya )
 - [ x ] transform anim
 - [ x ] mesh deformation anim
 - [ partial ] colorDome
 - [ partial ] imageDome
 - [ partial ] UsdPreviewSurface -> Bella uber
 - [ partial ] Usd PointLight -> Bella PointLight
 - [ partial ] UsdCamera -> Bella camera
 - [ alpha ] Usd mesh instancing -> Bella mesh instancing

TODO
 - [ ] split mesh along udim seams 
 - [ ] partial MaterialX translator
 - [ ] partial Nvidia MDL translator
 - [ ] -override material.bsa, slipstream attribs for anims from a manually material-ed .bsa file 

Tested on: 
 - Linux
 - MacOS Ventura 13.4
 - Window 11 Pro 21H2
 - [.usdz](https://developer.apple.com/augmented-reality/quick-look/) files downloaded from Apple, unzipped
 - .usd output from Blender
 - [Nvidia Attic](https://developer.nvidia.com/usd#sample)

---
**Dependencies:**

> do NOT install Python 3.11+
 
 - Python >=3.6, <3.11 

    - MacOs/Linux: recommended [pyenv](https://github.com/pyenv/pyenv) ( Mac requires homebrew)

    - Windows: recommended-> Microsoft Store version ( getting DLL fail with pyenv-win and python.org ) 

Install Pixar's USD Python libraries [usd-core](https://pypi.org/project/usd-core/)


>pip install usd-core

Install numpy for performant vectorized math operations

>pip install numpy
---

```
usage: oomerusd2bella [-h] [-usdfile USDFILE] [-start START] [-end END] [--debug] [--colordome] [-subdivision SUBDIVISION]

options:
  -h, --help                show this help message and exit
  -usdfile USDFILE          path to usd file
  -start START              sequence start frame
  -end END                  sequence end frame
  --debug
  --usda                    output usda
  --colordome               insert white color dome
  -subdivision SUBDIVISION  force subdivision level

```

---

Run oomerunittests.py to confirm that dependencies are met
```
python oomerunittest.py

PASSED: oomUsd.Reader.triangulate_ngons()
PASSED: faceVertexCount
PASSED: faceVertexIndices
PASSED: normals
PASSED: txcoords
```

## Examples
>python oomerusd2bella.py --usdfile ./usd/tv_retro/tv_retro.usdc --colordome

![](/images/tv_retro.png)

## Notes
- .bsa file is written next to .usd file
- .bsa is overwritten
- -start/end params force .bsa output to subfolder with name of the .usd file
- -start/end .bsa files are 5 digit padded

