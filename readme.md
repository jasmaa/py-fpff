# py-fpff

Reads, writes, and exports FPFF files

## Installation and Usage

### Install
```
pip install py-fpff
```
### Sample code
```
from py_fpff import fpff

# create fpff
s = fpff.FPFF()
s.add("hello world", fpff.FileType.ASCII)

# write
s.write("hello_world.fpff")

# read
s.read("hello_world_2.fpff")

# export
s.export("export-hello-world-2")
```