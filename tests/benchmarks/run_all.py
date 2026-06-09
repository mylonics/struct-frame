#!/usr/bin/env python3
import argparse, json, os, platform, shutil, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / 'tests' / 'benchmarks'
RESULTS = BENCH / 'results'
LANGS = ['python','c','cpp','ts','js','csharp','rust']

def run(cmd, cwd=ROOT, env=None):
    print('+', ' '.join(map(str, cmd)))
    return subprocess.run(cmd, cwd=cwd, env=env or os.environ.copy(), text=True)

def available(lang):
    return {'python': shutil.which('python3') or shutil.which('python'), 'c': shutil.which(os.environ.get('CC','gcc')), 'cpp': shutil.which(os.environ.get('CXX','g++')), 'ts': shutil.which('node') and (ROOT/'tests/ts/node_modules/.bin/tsc').exists(), 'js': shutil.which('node'), 'csharp': shutil.which('dotnet'), 'rust': shutil.which('cargo')}[lang]

def validate(path, lang):
    data=json.loads(path.read_text())
    required={'schema_version','language','runner_version','timestamp','host','scenarios'}
    if not required <= data.keys(): raise ValueError(f'{path}: missing {required-data.keys()}')
    if data['schema_version']!='1' or data['language']!=lang: raise ValueError(f'{path}: wrong schema/lang')
    for s in data['scenarios']:
        for k in ['name','profile','operation','msg_count','bytes_total','duration_s','msg_per_sec','mb_per_sec','latency_ns']:
            if k not in s: raise ValueError(f'{path}: scenario missing {k}')
        for k in ['p50','p95','p99','max']:
            if k not in s['latency_ns']: raise ValueError(f'{path}: latency missing {k}')
    return data

def command(lang, iterations, out):
    py=sys.executable
    if lang=='python': return [py, 'tests/benchmarks/python/bench.py', '--iterations', str(iterations), '--output', str(out)]
    if lang=='js': return ['node', 'tests/benchmarks/js/bench.mjs', '--iterations', str(iterations), '--output', str(out)]
    if lang=='ts':
        js=Path('tests/benchmarks/ts/dist/bench.js')
        return ['bash','-lc', f'cd tests/benchmarks/ts && ../../ts/node_modules/.bin/tsc bench.ts --outDir dist --module commonjs --target es2020 --types node --typeRoots ../../ts/node_modules/@types --moduleResolution node --esModuleInterop --skipLibCheck && cd ../../.. && node {js} --iterations {iterations} --output {out}']
    if lang=='c':
        exe=BENCH/'c/bench'
        cc=os.environ.get('CC','gcc')
        return ['bash','-lc', f'{cc} -O2 -std=c11 tests/benchmarks/c/bench.c -o {exe} && {exe} --iterations {iterations} --output {out}']
    if lang=='cpp':
        exe=BENCH/'cpp/bench'
        cxx=os.environ.get('CXX','g++')
        return ['bash','-lc', f'{cxx} -O2 -std=c++17 tests/benchmarks/cpp/bench.cpp -o {exe} && {exe} --iterations {iterations} --output {out}']
    if lang=='csharp': return ['dotnet','run','--project','tests/benchmarks/csharp/Bench.csproj','--','--iterations',str(iterations),'--output',str(out)]
    if lang=='rust': return ['cargo','run','--quiet','--manifest-path','tests/benchmarks/rust/Cargo.toml','--','--iterations',str(iterations),'--output',str(out)]
    raise KeyError(lang)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--lang', action='append', choices=LANGS); ap.add_argument('--skip-lang', action='append', default=[], choices=LANGS); ap.add_argument('--quick', action='store_true')
    args=ap.parse_args(); RESULTS.mkdir(parents=True, exist_ok=True); iterations=100 if args.quick else int(os.getenv('BENCH_ITERATIONS','50000'))
    selected=args.lang or LANGS; selected=[l for l in selected if l not in args.skip_lang]
    all_data=[]; failures=[]
    for lang in selected:
        if not available(lang): print(f'::warning::{lang} toolchain unavailable; skipping'); continue
        out=Path('tests/benchmarks/results')/f'{lang}.json'; rc=run(command(lang, iterations, out)).returncode
        if rc: failures.append((lang, f'exit {rc}')); continue
        try:
            all_data.append(validate(ROOT/out, lang))
        except (OSError, json.JSONDecodeError, ValueError) as e:
            failures.append((lang, str(e)))
    summary={'schema_version':'1','host':{'os':platform.system(),'arch':platform.machine()},'languages':all_data}
    (RESULTS/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    lines=['| language | scenario | msg/sec | MB/sec | p99 ns |','|---|---:|---:|---:|---:|']
    for data in all_data:
        for s in data['scenarios']:
            lines.append(f"| {data['language']} | {s['name']} | {s['msg_per_sec']:.1f} | {s['mb_per_sec']:.2f} | {s['latency_ns']['p99']} |")
    (RESULTS/'summary.md').write_text('\n'.join(lines)+'\n')
    if failures:
        for lang,msg in failures: print(f'FAILED {lang}: {msg}', file=sys.stderr)
        return 1
    return 0
if __name__=='__main__': raise SystemExit(main())
