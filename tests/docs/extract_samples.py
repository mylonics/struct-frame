#!/usr/bin/env python3
import argparse, json, re, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DOCS=ROOT/'docs/src/content/docs'
OUT=ROOT/'tests/docs/_samples'
LANG_EXT={'c':'c','cpp':'cpp','python':'py','py':'py','ts':'ts','typescript':'ts','js':'js','javascript':'js','rust':'rs','csharp':'cs','cs':'cs'}
CANON={'py':'python','python':'python','typescript':'ts','ts':'ts','javascript':'js','js':'js','c':'c','cpp':'cpp','rust':'rust','csharp':'csharp','cs':'csharp'}
FENCE=re.compile(r'```([^\n`]*)\n(.*?)\n```', re.S)
def sanitize(path): return re.sub(r'[^A-Za-z0-9_.-]+','_',str(path))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--keep', action='store_true'); args=ap.parse_args()
    if OUT.exists() and not args.keep: shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    manifest=[]
    for doc in sorted(DOCS.rglob('*')):
        if doc.suffix not in ('.md','.mdx'): continue
        rel=doc.relative_to(DOCS); text=doc.read_text(encoding='utf-8')
        idx=0
        for m in FENCE.finditer(text):
            info=m.group(1).strip(); parts=info.split(); lang=parts[0].lower() if parts else ''
            if lang not in LANG_EXT: continue
            flags=set(p.lower() for p in parts[1:])
            idx+=1; ext=LANG_EXT[lang]
            out=OUT/f'{sanitize(rel)}__{idx}.{ext}'
            out.write_text(m.group(2).strip()+"\n", encoding='utf-8')
            manifest.append({'source':str(rel),'index':idx,'language':CANON[lang],'path':str(out.relative_to(ROOT)),'flags':sorted(flags),'compile': not ({'skip','no-compile'} & flags)})
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Extracted {len(manifest)} samples to {OUT}')
if __name__=='__main__': raise SystemExit(main())
