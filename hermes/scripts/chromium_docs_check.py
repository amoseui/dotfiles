#!/usr/bin/env python3
import urllib.request, json, hashlib, datetime, os, tempfile
from pathlib import Path
VAULT=Path.home()/'Obsidian/amoseui'
STATE=VAULT/'6-agents/state/chromium-docs.json'
BASE=VAULT/'5-wiki/references/chromium-docs'
def raw_url(path): return f'https://raw.githubusercontent.com/chromium/chromium/main/{path}'
def fetch(path):
    return urllib.request.urlopen(urllib.request.Request(raw_url(path),headers={'User-Agent':'Hermes/1.0'}),timeout=30).read().decode('utf-8','replace')
state=json.loads(STATE.read_text(encoding='utf-8'))
changed=[]; errors=[]; untranslated=[]
for doc_id,d in state['docs'].items():
    try:
        txt=fetch(d['path'])
        sha=hashlib.sha256(txt.encode()).hexdigest()
        if sha != d.get('sha256'):
            changed.append({'id':doc_id,'title':d['title'],'path':d['path'],'old_sha':d.get('sha256'),'new_sha':sha,'chars':len(txt)})
            d['sha256']=sha; d['bytes']=len(txt.encode()); d['last_changed_detected_at']=datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        d['last_checked']=datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        if d.get('status') != 'translated':
            untranslated.append({'id':doc_id,'title':d['title'],'path':d['path'],'status':d.get('status'),'chars':len(txt)})
    except Exception as e:
        errors.append({'id':doc_id,'path':d.get('path'), 'error':repr(e)})
state['updated_at']=datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
fd,tmp_name=tempfile.mkstemp(prefix=f'.{STATE.name}.new-',dir=STATE.parent)
try:
    with os.fdopen(fd,'w',encoding='utf-8') as handle:
        json.dump(state,handle,ensure_ascii=False,indent=2)
        handle.write('\n'); handle.flush(); os.fsync(handle.fileno())
    os.replace(tmp_name,STATE)
finally:
    Path(tmp_name).unlink(missing_ok=True)
print(json.dumps({'changed':changed,'untranslated_queue':untranslated[:5],'untranslated_total':len(untranslated),'errors':errors,'state':str(STATE),'notes_dir':str(BASE)},ensure_ascii=False,indent=2))
