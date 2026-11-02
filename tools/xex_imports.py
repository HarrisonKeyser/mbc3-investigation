import struct,sys
def imports(xex_path, pe_path, base=0x82000000):
    d=open(xex_path,'rb').read(); img=open(pe_path,'rb').read()
    cnt=struct.unpack('>I',d[20:24])[0]; h={}
    for i in range(cnt):
        k,v=struct.unpack('>II',d[24+i*8:32+i*8]); h[k]=v
    o=h[0x103ff]
    size,strsz,nstr=struct.unpack('>III',d[o:o+12])
    s=d[o+12:o+12+strsz]; names=[x.decode() for x in s.split(b'\0') if x]
    p=o+12+strsz; res={}
    for li in range(nstr):
        lsz=struct.unpack('>I',d[p:p+4])[0]
        nameidx,count=struct.unpack('>HH',d[p+0x24:p+0x28])
        recs=[struct.unpack('>I',d[p+0x28+j*4:p+0x2c+j*4])[0] for j in range(count)]
        for r in recs:
            v=struct.unpack('>I',img[r-base:r-base+4])[0]
            typ=v>>24; ordn=v&0xffff
            res[r]=(names[nameidx],typ,ordn)
        p+=lsz
    return res
if __name__=='__main__':
    for a,(n,t,o) in sorted(imports(sys.argv[1],sys.argv[2]).items()): print(hex(a),n,t,hex(o))
