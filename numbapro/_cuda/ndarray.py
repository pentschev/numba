import sys
from ctypes import *
import numpy as np
from numpy.ctypeslib import c_intp
from numbapro._cuda import driver as _cuda
from numbapro._cuda import default as _cuglobals


_pyobject_head_fields = [('pyhead1', c_size_t),
                         ('pyhead2', c_void_p),]

if hasattr(sys, 'getobjects'):
    _pyobject_head_fields = [('pyhead3', c_int),
                             ('pyhead4', c_int),] + \
                              _pyobject_head_fields

_numpy_fields = _pyobject_head_fields + \
      [('data', c_void_p),                      # data
       ('nd',   c_int),                         # nd
       ('dimensions', POINTER(c_intp)),       # dimensions
       ('strides', POINTER(c_intp)),          # strides
        #  NOTE: The following fields are unused.
        #        Not sending to GPU to save transfer bandwidth.
        #       ('base', c_void_p),                      # base
        #       ('desc', c_void_p),                      # descr
        #       ('flags', c_int),                        # flags
        #       ('weakreflist', c_void_p),               # weakreflist
        #       ('maskna_dtype', c_void_p),              # maskna_dtype
        #       ('maskna_data', c_void_p),               # maskna_data
        #       ('masna_strides', POINTER(c_intp)),    # masna_strides
      ]

class NumpyStructure(Structure):
    _fields_ = _numpy_fields

def ndarray_to_device_memory(ary, stream=0):
    retriever, gpu_data = ndarray_data_to_device_memory(ary, stream=stream)

    dims = ary.ctypes.shape
    gpu_dims = _cuda.DeviceMemory(_cuglobals.context, sizeof(dims))
    gpu_dims.to_device_raw(addressof(dims), sizeof(dims), stream=stream)

    strides = ary.ctypes.strides
    gpu_strides = _cuda.DeviceMemory(_cuglobals.context, sizeof(strides))
    gpu_strides.to_device_raw(addressof(strides), sizeof(strides), stream=stream)

    fields = {
        'nd':         len(ary.shape),
        'data':       c_void_p(gpu_data._handle.value),
        'dimensions': cast(c_void_p(gpu_dims._handle.value), POINTER(c_intp)),
        'strides':    cast(c_void_p(gpu_strides._handle.value), POINTER(c_intp)),
    }
    struct = NumpyStructure(**fields)

    gpu_struct = _cuda.DeviceMemory(_cuglobals.context, sizeof(struct))
    gpu_struct.to_device_raw(addressof(struct), sizeof(struct))

    # NOTE: Do not free gpu_data, gpu_dims and gpu_strides before
    #       freeing gpu_struct.
    gpu_struct.add_dependencies(gpu_data, gpu_dims, gpu_strides)

    return retriever, gpu_struct

def ndarray_data_to_device_memory(ary, stream=0):
    dataptr = ary.ctypes.data_as(c_void_p)
    datasize = ary.shape[0] * ary.strides[0]

    gpu_data = _cuda.DeviceMemory(_cuglobals.context, datasize)
    gpu_data.to_device_raw(dataptr, datasize, stream=stream)

    def retriever():
        gpu_data.from_device_raw(dataptr, datasize)

    return retriever, gpu_data
