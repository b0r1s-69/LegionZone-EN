import re, os, json, glob, html
DEC='/home/admin1/Documents/deepseek-harness/Workspace2/lz/dec'
CJK=re.compile(r'[\u4e00-\u9fff]')
units={}  # id -> dict(value, kind, where)
def add(uid,value,kind,where):
    if not value or not CJK.search(value): return
    units[uid]={'v':value,'kind':kind,'w':where}

# ---- res strings (union default + zh) ----
def load_xml_strings(p):
    s=open(p,encoding='utf-8',errors='ignore').read()
    return re.findall(r'<string name="([^"]+)"([^>]*)>(.*?)</string>',s,re.S)
keys={}
for p in ['res/values/strings.xml','res/values-zh-rCN/strings.xml']:
    for k,attrs,v in load_xml_strings(os.path.join(DEC,p)):
        prev=keys.get(k)
        if prev is None or (CJK.search(v) and not CJK.search(prev)):
            keys[k]=v
for k,v in keys.items(): add('S|'+k,v,'string','res/values/strings.xml')
# arrays / plurals / string-arrays
for p in ['res/values/arrays.xml','res/values/strings.xml','res/values-zh-rCN/arrays.xml','res/values-zh-rCN/strings.xml']:
    fp=os.path.join(DEC,p)
    if not os.path.exists(fp): continue
    s=open(fp,encoding='utf-8',errors='ignore').read()
    for m in re.finditer(r'<(string-array|array|plurals) name="([^"]+)"[^>]*>(.*?)</\1>',s,re.S):
        kind,name,body=m.group(1),m.group(2),m.group(3)
        for i,it in enumerate(re.findall(r'<(?:item|string)[^>]*>(.*?)</(?:item|string)>',body,re.S)):
            add(f'A|{name}|{i}',it,f'{kind}','res/values/arrays.xml')

# ---- layouts ----
ATTR=re.compile(r'([a-zA-Z0-9_:]+)="([^"]*)"')
for fp in glob.glob(os.path.join(DEC,'res/layout*/**/*.xml'),recursive=True):
    rel=os.path.relpath(fp,DEC)
    s=open(fp,encoding='utf-8',errors='ignore').read()
    for i,(a,v) in enumerate(ATTR.findall(s)):
        if CJK.search(v):
            add(f'L|{rel}|{a}|{i}',v,'layout',rel)

# ---- smali const-string ----
CS=re.compile(r'const-string(?:/jumbo)? ([vp]\d+), "(.*?)"\s*$')
for root in ['smali','smali_classes2']:
    for fp in glob.glob(os.path.join(DEC,root,'**/*.smali'),recursive=True):
        rel=os.path.relpath(fp,DEC)
        for ln,line in enumerate(open(fp,encoding='utf-8',errors='ignore'),1):
            m=CS.match(line.rstrip('\n'))
            if not m: continue
            raw=m.group(2)
            if '\\u' not in raw: continue
            try: v=raw.encode('utf-8').decode('unicode_escape')
            except Exception: continue
            if CJK.search(v): add(f'M|{rel}|{ln}',v,'smali',f'{rel}:{ln}')

json.dump(units,open(os.path.join(DEC,'../work/units.json'),'w'),ensure_ascii=False,indent=1)
print('units:',len(units))
from collections import Counter
print(Counter(u['kind'] for u in units.values()))
uv={u['v'] for u in units.values()}
print('unique values:',len(uv))
print('chars total:',sum(len(u['v']) for u in units.values()))
