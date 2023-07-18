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

Tested: 
 - Python 3.10.12
 - usd-core 23.5
 - numpy 1.2.50
 - MacOS Ventura 13.4
 - [.usdz](https://developer.apple.com/augmented-reality/quick-look/) files downloaded from Apple, unzipped
 - .usd output from Blender
 - [Nvidia Attic](https://developer.nvidia.com/usd#sample)

---
**Dependencies:**

[usd-core](https://pypi.org/project/usd-core/)
install Pixar's USD core libraries for Python

numpy used for performant vectorized math

Use [pyenv](https://github.com/pyenv/pyenv) to avoid messing up system Python

```
pip install pxr
pip install numpy
```
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




