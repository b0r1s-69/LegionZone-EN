import json, re, os, sys
DEC='dec'
units=json.load(open('work/units.json'))
id2zh=json.load(open('work/id2zh_smali.json'))
en={}
for f in ['work/out/s1.json','work/out/s2.json']:
    if os.path.exists(f): en.update(json.load(open(f)))
missing=[k for k in id2zh if k not in en]
print('smali translations',len(en),'missing',len(missing))
zh2en={id2zh[k]:v for k,v in en.items()}
def esc(s):
    return s.replace('\\','\\\\').replace('"','\\"').replace('\n','\\n').replace('\t','\\t').replace('\r','\\r')

# group by file
byfile={}
for k,v in units.items():
    if v['kind']!='smali': continue
    rel,ln=k.split('|')[1],int(k.split('|')[2])
    byfile.setdefault(rel,[]).append((ln,v['v']))

CS=re.compile(r'^(?P<indent>\s*)const-string(?:/jumbo)? (?P<reg>[vp]\d+), "(?P<val>.*)"\s*$')
patched=0; files=0
for rel,items in byfile.items():
    fp=os.path.join(DEC,rel)
    lines=open(fp,encoding='utf-8').read().split('\n')
    changed=False
    for ln,zh in items:
        if zh not in zh2en: continue
        line=lines[ln-1]
        m=CS.match(line)
        if not m: 
            print('NO MATCH', rel, ln, line[:80]); continue
        lines[ln-1]=f'{m.group("indent")}const-string {m.group("reg")}, "{esc(zh2en[zh])}"'
        patched+=1; changed=True
    if changed:
        open(fp,'w',encoding='utf-8').write('\n'.join(lines)); files+=1
print('patched',patched,'in',files,'files')
