#!/usr/bin/env python3
import argparse, json, os, shutil, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'tests/docs/_samples'
SCRATCH=ROOT/'tests/docs/_scratch'

def run(cmd, cwd=ROOT):
    return subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
def env_skip(lang): return os.getenv(f'DOCSAMPLES_SKIP_{lang.upper()}') == '1'
def looks_like_fragment(path):
    s=path.read_text(errors='ignore')
    markers=['...', '<your', 'TODO', 'Generated', 'import {', 'from generated', '$ ', 'python -m ', 'npm ']
    lines=[line for line in s.splitlines() if line.strip()]
    indented_fragment = bool(lines and (lines[0].startswith(' ') or lines[0].startswith('\t'))) or any(line.startswith('  ') or line.startswith('\t') for line in lines)
    return indented_fragment or any(m in s for m in markers)
def command(sample, quick):
    lang=sample['language']; path=ROOT/sample['path']
    if env_skip(lang): return None, 'env-skip'
    if quick and lang in {'c','cpp','ts','rust','csharp'}: return None, 'quick-skip'
    if looks_like_fragment(path): return None, 'fragment-skip'
    if lang=='python': return [sys.executable, '-m', 'py_compile', str(path)], None
    if lang=='js': return ['node', '--check', str(path)], None if shutil.which('node') else (None, 'missing-tool')
    if lang=='ts':
        tsc=ROOT/'tests/ts/node_modules/.bin/tsc'
        if not tsc.exists(): return None, 'missing-tool'
        return [str(tsc), '--noEmit', '--target', 'es2020', '--module', 'esnext', '--strict', 'false', str(path)], None
    if lang=='c': return [os.environ.get('CC','gcc'), '-fsyntax-only', str(path)], None if shutil.which(os.environ.get('CC','gcc')) else (None, 'missing-tool')
    if lang=='cpp': return [os.environ.get('CXX','g++'), '-std=c++20', '-fsyntax-only', str(path)], None if shutil.which(os.environ.get('CXX','g++')) else (None, 'missing-tool')
    if lang=='rust':
        if not shutil.which('cargo'): return None, 'missing-tool'
        crate=SCRATCH/'rust'; (crate/'src').mkdir(parents=True, exist_ok=True); code=path.read_text();
        if 'fn main' not in code: code='fn main() {\n'+code+'\n}\n'
        (crate/'Cargo.toml').write_text('[package]\nname="docsample"\nversion="0.1.0"\nedition="2021"\n')
        (crate/'src/main.rs').write_text(code)
        return ['cargo','check','--quiet'], crate
    if lang=='csharp':
        if not shutil.which('dotnet'): return None, 'missing-tool'
        proj=SCRATCH/'csharp'; proj.mkdir(parents=True, exist_ok=True)
        (proj/'DocSample.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings></PropertyGroup></Project>')
        code=path.read_text();
        if 'class ' not in code and 'static void Main' not in code: code='using System;\nclass Program { static void Main() {\n'+code+'\n} }\n'
        (proj/'Program.cs').write_text(code)
        return ['dotnet','build','--nologo','--verbosity','quiet'], proj
    return None, 'unsupported'
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--quick', action='store_true'); ap.add_argument('--rust', action='store_true', help='include Rust in quick mode'); args=ap.parse_args()
    manifest=OUT/'manifest.json'
    if not manifest.exists():
        print('No extracted samples found; running extractor first.'); subprocess.check_call([sys.executable, 'tests/docs/extract_samples.py'], cwd=ROOT)
    samples=json.loads(manifest.read_text()); rows=[]; failures=[]
    for s in samples:
        if not s.get('compile', True): rows.append((s['language'],s['path'],'skipped','directive')); continue
        if args.quick and s['language']=='rust' and not args.rust: rows.append((s['language'],s['path'],'skipped','quick')); continue
        cmd,cwd_or_reason=command(s,args.quick)
        if cmd is None:
            reason = cwd_or_reason if isinstance(cwd_or_reason, str) else 'skipped'
            rows.append((s['language'],s['path'],'skipped',reason)); continue
        cwd = cwd_or_reason if isinstance(cwd_or_reason, Path) else ROOT
        proc=run(cmd,cwd)
        status='ok' if proc.returncode==0 else 'failed'
        rows.append((s['language'],s['path'],status,''))
        if proc.returncode:
            failures.append((s, proc.stdout + proc.stderr))
            if args.quick and len(failures) >= 10: break
    print('| language | sample | status | note |'); print('|---|---|---|---|')
    for r in rows: print('| '+' | '.join(str(x) for x in r)+' |')
    if failures:
        for s,out in failures[:10]: print(f'\nFAIL {s["path"]}\n{out}', file=sys.stderr)
        return 1
    return 0
if __name__=='__main__': raise SystemExit(main())
