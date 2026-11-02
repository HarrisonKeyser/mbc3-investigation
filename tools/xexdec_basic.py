import struct,sys,subprocess,os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
d=open(sys.argv[1],'rb').read()
magic,flags,pe_off,res,sec_off,cnt=struct.unpack('>4sIIIII',d[:24])
hdrs={}
for i in range(cnt):
    k,v=struct.unpack('>II',d[24+i*8:32+i*8]); hdrs[k]=v
ffi=hdrs[0x3ff]
size,enc,comp=struct.unpack('>IHH',d[ffi:ffi+8])
imgsize=struct.unpack('>I',d[sec_off+4:sec_off+8])[0]
body=d[pe_off:]
if enc==1:
    key=d[sec_off+0x150:sec_off+0x160]
    def ecb(k,x): c=Cipher(algorithms.AES(k),modes.ECB()).decryptor(); return c.update(x)+c.finalize()
    sk=ecb(bytes.fromhex('20B185A59D28FDC340583FBB0896BF91'),key)
    body=body[:len(body)//16*16]
    c=Cipher(algorithms.AES(sk),modes.CBC(b'\0'*16)).decryptor(); body=c.update(body)+c.finalize()
print('enc',enc,'comp',comp,'img',hex(imgsize))
if comp==1:
    out=bytearray(); p=0
    for i in range((size-8)//8):
        ds,zs=struct.unpack('>II',d[ffi+8+i*8:ffi+16+i*8])
        out+=body[p:p+ds]; out+=b'\0'*zs; p+=ds
    open(sys.argv[2],'wb').write(bytes(out[:imgsize]).ljust(imgsize,b'\0'))
else:
    raise SystemExit('use xexdec.py for LZX')
