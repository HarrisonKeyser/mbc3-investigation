import struct, bisect
from capstone import *
BASE=0x82000000
D=open(__import__('os').environ.get('MBC3_PE','default.pe'),'rb').read()
md=Cs(CS_ARCH_PPC, CS_MODE_32|CS_MODE_BIG_ENDIAN)
def word(off): return struct.unpack('>I',D[off:off+4])[0]
def u32(va): return word(va-BASE)
pe=struct.unpack('<I',D[0x3c:0x40])[0]; nsec=struct.unpack('<H',D[pe+6:pe+8])[0]; opt=struct.unpack('<H',D[pe+20:pe+22])[0]
SECS={}
for i in range(nsec):
    s=D[pe+24+opt+i*40:pe+24+opt+i*40+40]; SECS[s[:8].rstrip(b'\0').decode()]=struct.unpack('<II',s[8:16])
vs,va=SECS['.text']; TEXT=(va,va+vs)
vs,va=SECS['.pdata']; PDATA=[]
for i in range(vs//8):
    b,f=struct.unpack('>II',D[va+i*8:va+i*8+8])
    if b: PDATA.append((b,b+((f>>8)&0x3fffff)*4))
PDATA.sort(); _st=[p[0] for p in PDATA]
def func(a):
    i=bisect.bisect_right(_st,a)-1
    return PDATA[i] if i>=0 and PDATA[i][0]<=a<PDATA[i][1] else None
def dis(a,n): return list(md.disasm(D[a-BASE:a-BASE+4*n],a))
def pr(a,n):
    for i in dis(a,n): print('%08x: %08x  %-8s %s'%(i.address,u32(i.address),i.mnemonic,i.op_str))
def prf(a):
    f=func(a); print('--- func %x-%x'%f); pr(f[0],(f[1]-f[0])//4)
_calls=None
def build_calls():
    global _calls
    _calls={}
    for off in range(TEXT[0],TEXT[1],4):
        w=word(off)
        if (w>>26)==18 and (w&3)==1:
            li=w&0x3fffffc
            if li&0x2000000: li-=0x4000000
            _calls.setdefault(BASE+off+li,[]).append(BASE+off)
def callers(t):
    if _calls is None: build_calls()
    return _calls.get(t,[])
def cstr(a,n=200):
    o=a-BASE; return D[o:D.find(b'\0',o,o+n)]
def addr_refs(va):
    hi=((va+0x8000)>>16)&0xffff; lo=va&0xffff; out=[]
    for off in range(TEXT[0],TEXT[1],4):
        w=word(off)
        if (w>>26) in (14,32,36,34,40) and (w&0xffff)==lo:
            ra=(w>>16)&31
            for k in range(1,16):
                w2=word(off-4*k)
                if (w2>>26)==15 and (w2&0xffff)==hi and ((w2>>21)&31)==ra: out.append(BASE+off); break
    return out
