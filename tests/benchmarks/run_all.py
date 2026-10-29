#!/usr/bin/env python3
"""Run the struct-frame benchmarks for every available language.

Each language's benchmark runs the code generated from ``schema/bench.sf`` together with that
language's real runtime (encoder, parser and generated serialize/deserialize). This script
generates the code into ``generated/<lang>``, builds the benchmark (optimised: -O2 for C/C++,
Release for C#, --release for Rust), runs it, and validates the JSON it writes against
``schema.json``. Results go to ``results/<lang>.json`` plus ``results/summary.{json,md}``.
"""
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / 'tests' / 'benchmarks'
RESULTS = BENCH / 'results'
GEN = BENCH / 'generated'
SCHEMA = BENCH / 'schema' / 'bench.sf'
LANGS = ['python', 'c', 'cpp', 'ts', 'js', 'csharp', 'rust']
EXE = '.exe' if os.name == 'nt' else ''
TSC = ROOT / 'tests' / 'ts' / 'node_modules' / '.bin' / ('tsc.cmd' if os.name == 'nt' else 'tsc')

# language -> (generator build flag, path flag, output sub-directory)
GENERATE = {
    'python': ('--build_py', '--py_path', 'py'),
    'c': ('--build_c', '--c_path', 'c'),
    'cpp': ('--build_cpp', '--cpp_path', 'cpp'),
    'ts': ('--build_ts', '--ts_path', 'ts'),
    'js': ('--build_js', '--js_path', 'js'),
    'csharp': ('--build_csharp', '--csharp_path', 'csharp'),
    'rust': ('--build_rust', '--rust_path', 'rust'),
}


def run(cmd, cwd=ROOT, env=None):
    print('+', ' '.join(map(str, cmd)), flush=True)
    return subprocess.run([str(c) for c in cmd], cwd=cwd, env=env or os.environ.copy(), text=True)


def available(lang):
    return {
        'python': True,
        'c': shutil.which(os.environ.get('CC', 'gcc')),
        'cpp': shutil.which(os.environ.get('CXX', 'g++')),
        'ts': shutil.which('node') and TSC.exists(),
        'js': shutil.which('node'),
        'csharp': shutil.which('dotnet'),
        'rust': shutil.which('cargo'),
    }[lang]


def generate(lang):
    flag, path_flag, sub = GENERATE[lang]
    env = os.environ.copy()
    env['PYTHONPATH'] = str(ROOT / 'src') + os.pathsep + env.get('PYTHONPATH', '')
    out = GEN / sub
    shutil.rmtree(out, ignore_errors=True)
    return run([sys.executable, '-m', 'struct_frame', SCHEMA, flag, path_flag, out, '--force'], env=env).returncode == 0


def build(lang):
    """Compile the benchmark if the language needs it. Returns True on success."""
    if lang == 'c':
        cc = os.environ.get('CC', 'gcc')
        return run([cc, '-O2', '-std=c11', '-I', GEN / 'c', BENCH / 'c' / 'bench.c',
                    '-o', BENCH / 'c' / f'bench{EXE}']).returncode == 0
    if lang == 'cpp':
        cxx = os.environ.get('CXX', 'g++')
        return run([cxx, '-O2', '-std=c++20', '-I', GEN / 'cpp', BENCH / 'cpp' / 'bench.cpp',
                    '-o', BENCH / 'cpp' / f'bench{EXE}']).returncode == 0
    if lang == 'ts':
        dist = BENCH / 'ts' / 'dist'
        shutil.rmtree(dist, ignore_errors=True)
        # noEmitOnError is off, so type errors in optional SDK modules do not stop the emit;
        # the run below fails if the benchmark itself did not compile.
        run([TSC, BENCH / 'ts' / 'bench.ts', '--rootDir', BENCH, '--outDir', dist, '--module', 'commonjs',
             '--target', 'es2020', '--types', 'node', '--typeRoots', ROOT / 'tests' / 'ts' / 'node_modules' / '@types',
             '--moduleResolution', 'node', '--esModuleInterop', '--skipLibCheck'])
        return (dist / 'ts' / 'bench.js').exists()
    return True


def command(lang, iterations, out):
    common = ['--iterations', str(iterations), '--output', out]
    if lang == 'python':
        return [sys.executable, BENCH / 'python' / 'bench.py', *common, '--gen-dir', GEN / 'py']
    if lang == 'js':
        return ['node', BENCH / 'js' / 'bench.mjs', *common, '--gen-dir', GEN / 'js']
    if lang == 'ts':
        return ['node', BENCH / 'ts' / 'dist' / 'ts' / 'bench.js', *common]
    if lang in ('c', 'cpp'):
        return [BENCH / lang / f'bench{EXE}', *common]
    if lang == 'csharp':
        return ['dotnet', 'run', '-c', 'Release', '--project', BENCH / 'csharp' / 'Bench.csproj', '--', *common]
    if lang == 'rust':
        return ['cargo', 'run', '--release', '--quiet', '--manifest-path', BENCH / 'rust' / 'Cargo.toml', '--', *common]
    raise KeyError(lang)


def validate(path, lang):
    data = json.loads(path.read_text())
    required = {'schema_version', 'language', 'runner_version', 'timestamp', 'host', 'scenarios'}
    if not required <= data.keys():
        raise ValueError(f'{path}: missing {required - data.keys()}')
    if data['schema_version'] != '1' or data['language'] != lang:
        raise ValueError(f'{path}: wrong schema/lang')
    for s in data['scenarios']:
        for k in ['name', 'profile', 'operation', 'msg_count', 'bytes_total', 'duration_s', 'msg_per_sec',
                  'mb_per_sec', 'latency_ns']:
            if k not in s:
                raise ValueError(f'{path}: scenario missing {k}')
        for k in ['p50', 'p95', 'p99', 'max']:
            if k not in s['latency_ns']:
                raise ValueError(f'{path}: latency missing {k}')
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lang', action='append', choices=LANGS)
    ap.add_argument('--skip-lang', action='append', default=[], choices=LANGS)
    ap.add_argument('--quick', action='store_true', help='100 iterations per scenario (smoke test)')
    args = ap.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)
    iterations = 100 if args.quick else int(os.getenv('BENCH_ITERATIONS', '50000'))
    selected = [lang for lang in (args.lang or LANGS) if lang not in args.skip_lang]
    all_data, failures = [], []
    for lang in selected:
        if not available(lang):
            print(f'::warning::{lang} toolchain unavailable; skipping')
            continue
        if not generate(lang):
            failures.append((lang, 'code generation failed'))
            continue
        if not build(lang):
            failures.append((lang, 'build failed'))
            continue
        out = RESULTS / f'{lang}.json'
        rc = run(command(lang, iterations, out)).returncode
        if rc:
            failures.append((lang, f'exit {rc}'))
            continue
        try:
            all_data.append(validate(out, lang))
        except (OSError, json.JSONDecodeError, ValueError) as e:
            failures.append((lang, str(e)))
    summary = {'schema_version': '1', 'host': {'os': platform.system(), 'arch': platform.machine()},
               'languages': all_data}
    (RESULTS / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    lines = ['| language | scenario | msg/sec | MB/sec | p99 ns |', '|---|---:|---:|---:|---:|']
    for data in all_data:
        for s in data['scenarios']:
            lines.append(f"| {data['language']} | {s['name']} | {s['msg_per_sec']:.1f} | "
                         f"{s['mb_per_sec']:.2f} | {s['latency_ns']['p99']} |")
    (RESULTS / 'summary.md').write_text('\n'.join(lines) + '\n')
    if failures:
        for lang, msg in failures:
            print(f'FAILED {lang}: {msg}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
