# uncrater
LuSEE Night binary blob unpackager

## Header File Conversion
`./uncrater/include/core_loop.h` was converted to `./uncrater/core_loop.py` using `ctypesgen`. Within the `uncrater` directory, run
```bash
ctypesgen include/core_loop.h > core_loop.py
```
if `core_loop.h` is ever updated.
