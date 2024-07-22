# import cppyy
# import cppyy.ll
# import ctypes
# cppyy.include('uncrater/include/core_loop.h')

# def c2py (struct, data):
#     c_data = ctypes.create_string_buffer(data)
#     s = cppyy.ll.cast[struct + '*'](c_data)
#     # we attach data back to the object os that it is not garbage collected
#     s.__storage = c_data
#     return s

def copy_attrs (src, dst):
    for attr in dir(src): 
        if "__" in attr:
            continue
        setattr(dst, attr, getattr(src, attr))