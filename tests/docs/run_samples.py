#!/usr/bin/env python3
"""Compile the code samples extracted from the documentation.

Samples are compiled against code freshly generated from the schemas in ``tests/docs/schemas``
(the schemas the examples are written against), so a sample may include generated headers or
import generated modules:

* C / C++: compiled with the generated directory on the include path; statements that are not
  inside a function are wrapped in ``main`` (``#include`` and ``using`` lines stay at file scope).
* TypeScript: type-checked from inside the generated directory, so ``./<pkg>.structframe``
  imports resolve.
* C#: built as top-level statements in a project that references the generated library.
* Rust: built in a crate that depends on the generated crate.
* Python: byte-compiled. JavaScript: syntax-checked.

Blocks marked ``no-compile`` (or ``skip``) in their code fence, and blocks that look like
fragments, are skipped. ``--quick`` skips C, C++, TypeScript, Rust and C#.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'tests/docs/_samples'
SCRATCH = ROOT / 'tests/docs/_scratch'
SCHEMAS = ROOT / 'tests/docs/schemas'
GEN = SCRATCH / 'gen'
GEN_FLAGS = {
    'c': ('--build_c', '--c_path'), 'cpp': ('--build_cpp', '--cpp_path'), 'ts': ('--build_ts', '--ts_path'),
    'js': ('--build_js', '--js_path'), 'python': ('--build_py', '--py_path'),
    'csharp': ('--build_csharp', '--csharp_path'), 'rust': ('--build_rust', '--rust_path'),
}


def run(cmd, cwd=ROOT):
    return subprocess.run([str(c) for c in cmd], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, encoding='utf-8', errors='replace')


def env_skip(lang):
    return os.getenv(f'DOCSAMPLES_SKIP_{lang.upper()}') == '1'


def looks_like_fragment(path):
    s = path.read_text(errors='ignore')
    markers = ['...', '<your', 'TODO', 'Generated', '$ ', 'python -m ', 'npm ']
    lines = [line for line in s.splitlines() if line.strip()]
    indented_fragment = bool(lines and (lines[0].startswith(' ') or lines[0].startswith('\t')))
    return indented_fragment or any(m in s for m in markers)


def generate_doc_code():
    """Generate every docs schema for every language into tests/docs/_scratch/gen/<lang>."""
    shutil.rmtree(GEN, ignore_errors=True)
    env = os.environ.copy()
    env['PYTHONPATH'] = str(ROOT / 'src') + os.pathsep + env.get('PYTHONPATH', '')
    for schema in sorted(SCHEMAS.glob('*.sf')):
        cmd = [sys.executable, '-m', 'struct_frame', str(schema), '--force']
        for lang, (build, path_flag) in GEN_FLAGS.items():
            cmd += [build, path_flag, str(GEN / lang)]
        r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f'generating {schema.name} failed:\n{r.stdout}\n{r.stderr}')
    # TypeScript samples import './generated/<x>' or './generated/ts/<x>'; provide both layouts
    # next to the sample.
    ts_root = SCRATCH / 'tsroot'
    shutil.rmtree(ts_root, ignore_errors=True)
    shutil.copytree(GEN / 'ts', ts_root / 'generated')
    shutil.copytree(GEN / 'ts', ts_root / 'generated' / 'ts')


def wrap_c_like(code, lang_cpp=False):
    """Put statements that are not inside a function into main()."""
    if re.search(r'\bmain\s*\(', code):
        return code
    head, body = [], []
    for line in code.splitlines():
        stripped = line.strip()
        if not body and (stripped.startswith('#') or stripped.startswith('using ') or not stripped):
            head.append(line)
        else:
            body.append(line)
    nl = chr(10)
    prelude = nl.join(['#include <stdio.h>', '#include <stdint.h>', '#include <string.h>']) + nl
    if lang_cpp:
        prelude += '#include <iostream>' + nl
    return prelude + nl.join(head) + nl + 'int main(void) {' + nl + nl.join(body) + nl + 'return 0;' + nl + '}' + nl


def command(sample, quick):
    lang = sample['language']
    path = ROOT / sample['path']
    if env_skip(lang):
        return None, 'env-skip'
    if quick and lang in {'c', 'cpp', 'ts', 'rust', 'csharp'}:
        return None, 'quick-skip'
    if looks_like_fragment(path):
        return None, 'fragment-skip'
    code = path.read_text(encoding='utf-8')
    if lang == 'python':
        return [sys.executable, '-m', 'py_compile', str(path)], None
    if lang == 'js':
        if not shutil.which('node'):
            return None, 'missing-tool'
        return ['node', '--check', str(path)], None
    if lang == 'ts':
        tsc = ROOT / 'tests/ts/node_modules/.bin' / ('tsc.cmd' if os.name == 'nt' else 'tsc')
        if not tsc.exists():
            return None, 'missing-tool'
        # Next to the generated code, so './<pkg>.structframe' and './generated/...' both resolve.
        target = (SCRATCH / 'tsroot' if "'./generated" in code else GEN / 'ts') / 'doc_sample.ts'
        if 'import ' not in code and 'export ' not in code:
            code += '\nexport {};\n'  # make it a module so top-level await is allowed
        target.write_text(code, encoding='utf-8')
        return [tsc, '--noEmit', '--target', 'es2022', '--module', 'esnext', '--moduleResolution', 'node',
                '--esModuleInterop', '--skipLibCheck', '--types', 'node', '--typeRoots',
                ROOT / 'tests/ts/node_modules/@types', target], None
    if lang in ('c', 'cpp'):
        compiler = os.environ.get('CC', 'gcc') if lang == 'c' else os.environ.get('CXX', 'g++')
        if not shutil.which(compiler):
            return None, 'missing-tool'
        ext = 'c' if lang == 'c' else 'cpp'
        target = SCRATCH / f'doc_sample.{ext}'
        target.write_text(wrap_c_like(code, lang == "cpp"), encoding='utf-8')
        std = ['-std=c11'] if lang == 'c' else ['-std=c++20']
        return [compiler, *std, '-fsyntax-only', '-I', GEN / lang, target], None
    if lang == 'rust':
        if not shutil.which('cargo'):
            return None, 'missing-tool'
        crate = SCRATCH / 'rust'
        (crate / 'src').mkdir(parents=True, exist_ok=True)
        if 'fn main' not in code:
            # Keep `use` statements (which may span lines) at crate level; the rest goes in main.
            uses, rest, in_use = [], [], False
            for line in code.splitlines():
                if in_use or line.strip().startswith('use '):
                    uses.append(line)
                    in_use = not line.rstrip().endswith(';')
                else:
                    rest.append(line)
            code = '\n'.join(uses) + '\nfn main() {\n' + '\n'.join(rest) + '\n}\n'
        dep = (GEN / 'rust').as_posix()
        (crate / 'Cargo.toml').write_text(
            '[package]\nname="docsample"\nversion="0.1.0"\nedition="2021"\n\n[workspace]\n\n'
            f'[dependencies]\nstruct_frame_sdk = {{ path = "{dep}" }}\n')
        (crate / 'src/main.rs').write_text(code)
        return ['cargo', 'check', '--quiet'], crate
    if lang == 'csharp':
        if not shutil.which('dotnet'):
            return None, 'missing-tool'
        proj = SCRATCH / 'csharp'
        proj.mkdir(parents=True, exist_ok=True)
        lib = (GEN / 'csharp' / 'StructFrame.csproj').resolve()
        (proj / 'DocSample.csproj').write_text(
            '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType>'
            '<TargetFramework>net8.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings>'
            '<Nullable>enable</Nullable></PropertyGroup>'
            # Build the generated library with its optional transports (NetCoreServer, System.IO.Ports).
            f'<ItemGroup><ProjectReference Include="{lib}" '
            'AdditionalProperties="IncludeNetCoreServer=true;IncludeSerialTransport=true" /></ItemGroup></Project>')
        (proj / 'Program.cs').write_text(code)
        return ['dotnet', 'build', '--nologo', '--verbosity', 'quiet',
                '-p:IncludeNetCoreServer=true', '-p:IncludeSerialTransport=true'], proj
    return None, 'unsupported'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--rust', action='store_true', help='include Rust in quick mode')
    args = ap.parse_args()
    manifest = OUT / 'manifest.json'
    if not manifest.exists():
        print('No extracted samples found; running extractor first.')
        subprocess.check_call([sys.executable, 'tests/docs/extract_samples.py'], cwd=ROOT)
    samples = json.loads(manifest.read_text())
    SCRATCH.mkdir(parents=True, exist_ok=True)
    if not args.quick:
        generate_doc_code()
    rows, failures = [], []
    for s in samples:
        if not s.get('compile', True):
            rows.append((s['language'], s['path'], 'skipped', 'directive'))
            continue
        if args.quick and s['language'] == 'rust' and not args.rust:
            rows.append((s['language'], s['path'], 'skipped', 'quick'))
            continue
        cmd, cwd_or_reason = command(s, args.quick)
        if cmd is None:
            reason = cwd_or_reason if isinstance(cwd_or_reason, str) else 'skipped'
            rows.append((s['language'], s['path'], 'skipped', reason))
            continue
        cwd = cwd_or_reason if isinstance(cwd_or_reason, Path) else ROOT
        proc = run(cmd, cwd)
        status = 'ok' if proc.returncode == 0 else 'failed'
        rows.append((s['language'], s['path'], status, ''))
        if proc.returncode:
            failures.append((s, proc.stdout + proc.stderr))
            if args.quick and len(failures) >= 10:
                break
    print('| language | sample | status | note |')
    print('|---|---|---|---|')
    for r in rows:
        print('| ' + ' | '.join(str(x) for x in r) + ' |')
    if failures:
        for s, out in (failures[:10] if args.quick else failures):
            print(f'\nFAIL {s["path"]}\n{out}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
