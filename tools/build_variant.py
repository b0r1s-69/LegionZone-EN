import json, sys, zipfile
sys.path.insert(0,'work')
from arsc_patch import patch_bytes, strip_locale_configs
from build_apk import dec

variant=sys.argv[1]           # v1 | v2
out_name=sys.argv[2]
OVERRIDE={'奖品福利':'Rewards','加速游戏':'Games','开通':'Join','如未注册将自动创建':'Auto-created if new'}
id2zh=json.load(open('work/id2zh_ui.json')); en=json.load(open('work/en_map.json'))
mapping={}
for uid,zh in id2zh.items():
    e=OVERRIDE.get(zh, en.get(uid))
    if e: mapping[dec(zh)]=dec(e)
DEX={'classes.dex':'work/classes.dex',
     'classes2.dex': 'work/classes2_enui.dex' if variant=='v2' else 'work/classes2.dex'}
ASSET_FIX='assets/h5_cache/ai-voice-ball/index.html'
src=zipfile.ZipFile('orig.apk')
out=zipfile.ZipFile(out_name,'w',allowZip64=True)
for info in src.infolist():
    n=info.filename
    if n in ('META-INF/RELEASEK.SF','META-INF/RELEASEK.RSA','META-INF/MANIFEST.MF'): continue
    if n in DEX: data=open(DEX[n],'rb').read()
    elif n==ASSET_FIX: data=open('dec/'+ASSET_FIX,'rb').read()
    else:
        data=src.read(n)
        if n=='resources.arsc' or (n.startswith('res/') and n.endswith('.xml')):
            data,_=patch_bytes(data,mapping)
            if n=='resources.arsc': data,_=strip_locale_configs(data)
    zi=zipfile.ZipInfo(n,date_time=info.date_time); zi.compress_type=info.compress_type
    zi.external_attr=info.external_attr; zi.internal_attr=info.internal_attr; zi.create_system=info.create_system
    out.writestr(zi,data)
out.close(); src.close()
print('built',out_name)
