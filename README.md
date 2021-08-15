# py-fpff

[![PyPi version](https://img.shields.io/pypi/v/py-fpff)](https://pypi.org/project/py-fpff/)

Library for working with FPFF.

## Getting Started

### Install
```
pip install py-fpff
```

### Sample Code
```
from py_fpff import FPFF, SectionType

with open('./input.fpff') as f:
    fpff = FPFF(f)
    fpff.append(SectionType.ASCII, 'Hello, world!')
    fpff.export('./exported')
```

## Testing

```
python -m unittest
```

## Building Documentation

```
# Install Sphinx and ReadTheDocs theme
pip install Sphinx sphinx_rtd_theme

cd ./docs
make html
```