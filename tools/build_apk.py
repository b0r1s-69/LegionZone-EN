import json, re, sys, zipfile, struct
sys.path.insert(0,'work')
from arsc_patch import patch_bytes, strip_locale_configs

def dec(s):
    s = (s.replace('&lt;','<').replace('&gt;','>').replace('&quot;','"')
          .replace('&apos;',"'"))
    s = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), s)
    s = s.replace('&amp;','&')
    out=[]; i=0
    mp={'n':'\n','t':'\t','r':'\r',"'":"'",'"':'"','\\':'\\','@':'@','?':'?'}
    while i < len(s):
        c=s[i]
        if c=='\\' and i+1 < len(s):
            n=s[i+1]
            if n in mp: out.append(mp[n]); i+=2; continue
            if n=='u' and i+5 < len(s):
                try: out.append(chr(int(s[i+2:i+6],16))); i+=6; continue
                except ValueError: pass
        out.append(c); i+=1
    s=''.join(out)
    if len(s)>=2 and s[0]=='"' and s[-1]=='"': s=s[1:-1]
    return s

id2zh=json.load(open('work/id2zh_ui.json')); en=json.load(open('work/en_map.json'))
mapping={}; conflicts=[]
for uid,zh in id2zh.items():
    if uid not in en: continue
    k=dec(zh); v=dec(en[uid])
    if k in mapping and mapping[k]!=v: conflicts.append((k,mapping[k],v))
    mapping[k]=v
print('mapping entries',len(mapping),'conflicts',len(conflicts))
for c in conflicts[:5]: print('  CONFLICT',c[0][:30],'|',c[1][:30],'|',c[2][:30])

src=zipfile.ZipFile('orig.apk')
out=zipfile.ZipFile('build2_unsigned.apk','w',allowZip64=True)
tot=0; files=0; details=[]
for info in src.infolist():
    data=src.read(info.filename)
    if info.filename=='resources.arsc' or (info.filename.startswith('res/') and info.filename.endswith('.xml')):
        nd,n=patch_bytes(data,mapping)
        if n: tot+=n; files+=1; details.append((info.filename,n))
        data=nd
        if info.filename=='resources.arsc':
            data,rem=strip_locale_configs(data); print('locale type chunks removed',rem)
    zi=zipfile.ZipInfo(info.filename, date_time=info.date_time)
    zi.compress_type=info.compress_type
    zi.external_attr=info.external_attr
    zi.internal_attr=info.internal_attr
    zi.create_system=info.create_system
    out.writestr(zi,data)
out.close(); src.close()
print('patched',tot,'strings in',files,'entries')
for f,n in sorted(details,key=lambda x:-x[1])[:8]: print('  ',f,n)
