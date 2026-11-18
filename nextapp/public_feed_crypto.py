"""AES-CBC for a public feed using OS crypto libraries; no bundled new crypto stack."""
import ctypes as C, ctypes.util, os


def aes_cbc_decrypt(data,key,iv):
    if len(key)!=16 or len(iv)!=16 or not data or len(data)%16 or len(data)>8*1024*1024:
        raise ValueError('Invalid public feed ciphertext')
    if os.name=='nt':return _windows(data,key,iv)
    lib=C.CDLL(C.util.find_library('crypto') or 'libcrypto.so.3')
    lib.EVP_CIPHER_CTX_new.restype=C.c_void_p
    lib.EVP_CIPHER_CTX_free.argtypes=[C.c_void_p]
    lib.EVP_aes_128_cbc.restype=C.c_void_p
    lib.EVP_DecryptInit_ex.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p]
    lib.EVP_DecryptUpdate.argtypes=[C.c_void_p,C.c_void_p,C.POINTER(C.c_int),C.c_void_p,C.c_int]
    lib.EVP_DecryptFinal_ex.argtypes=[C.c_void_p,C.c_void_p,C.POINTER(C.c_int)]
    ctx=lib.EVP_CIPHER_CTX_new()
    if not ctx:raise ValueError('Crypto provider unavailable')
    try:
        out=C.create_string_buffer(len(data)+16);first=C.c_int();last=C.c_int()
        if lib.EVP_DecryptInit_ex(ctx,lib.EVP_aes_128_cbc(),None,C.create_string_buffer(key),C.create_string_buffer(iv))!=1:raise ValueError('Crypto initialization failed')
        if lib.EVP_DecryptUpdate(ctx,out,C.byref(first),C.create_string_buffer(data),len(data))!=1:raise ValueError('Feed decrypt failed')
        if lib.EVP_DecryptFinal_ex(ctx,C.byref(out,first.value),C.byref(last))!=1:raise ValueError('Invalid feed padding')
        return out.raw[:first.value+last.value]
    finally:lib.EVP_CIPHER_CTX_free(ctx)


def _windows(data,key,iv):
    # Windows CNG AES-CBC, PKCS#7 padding. Handles are always released.
    lib=C.WinDLL('bcrypt');handle=C.c_void_p();key_handle=C.c_void_p()
    u=C.c_uint32;ptr=C.c_void_p;status=C.c_int32
    prototypes={
        'BCryptOpenAlgorithmProvider':([C.POINTER(ptr),C.c_wchar_p,C.c_wchar_p,u],status),
        'BCryptSetProperty':([ptr,C.c_wchar_p,ptr,u,u],status),
        'BCryptGetProperty':([ptr,C.c_wchar_p,ptr,u,C.POINTER(u),u],status),
        'BCryptGenerateSymmetricKey':([ptr,C.POINTER(ptr),ptr,u,ptr,u,u],status),
        'BCryptDecrypt':([ptr,ptr,u,ptr,ptr,u,ptr,u,C.POINTER(u),u],status),
        'BCryptDestroyKey':([ptr],status),'BCryptCloseAlgorithmProvider':([ptr,u],status)}
    for name,(args,result) in prototypes.items():getattr(lib,name).argtypes=args;getattr(lib,name).restype=result
    def ok(code):
        if code<0:raise ValueError('Windows public-feed crypto failed')
    try:
        ok(lib.BCryptOpenAlgorithmProvider(C.byref(handle),'AES',None,0))
        mode=C.create_unicode_buffer('ChainingModeCBC');ok(lib.BCryptSetProperty(handle,'ChainingMode',mode,C.sizeof(mode),0))
        size=u();written=u();ok(lib.BCryptGetProperty(handle,'ObjectLength',C.byref(size),C.sizeof(size),C.byref(written),0))
        obj=C.create_string_buffer(size.value);raw_key=C.create_string_buffer(key)
        ok(lib.BCryptGenerateSymmetricKey(handle,C.byref(key_handle),obj,size.value,raw_key,len(key),0))
        out=C.create_string_buffer(len(data));raw=C.create_string_buffer(data);ivbuf=C.create_string_buffer(iv)
        ok(lib.BCryptDecrypt(key_handle,raw,len(data),None,ivbuf,len(iv),out,len(data),C.byref(written),1))
        return out.raw[:written.value]
    finally:
        if key_handle:lib.BCryptDestroyKey(key_handle)
        if handle:lib.BCryptCloseAlgorithmProvider(handle,0)
