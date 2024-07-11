# uncrater
LuSEE Night binary blob unpackager

## Header File Conversion
`./include/core_loop.h` was converted to `./core_loop.py` using `ctypesgen`. Within the root directory, run
```
ctypesgen include/core_loop.h > core_loop.py
```
if `core_loop.h` is ever updated.
