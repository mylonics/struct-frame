#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
LANGS=['python','c','cpp','ts','js','csharp','rust']
def scenarios(data): return {s['name']:s for s in data.get('scenarios',[])}
def pct(old,new): return (new-old)/old*100 if old else 0.0
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--lang', action='append', choices=LANGS); ap.add_argument('--allow-missing-baseline', action='store_true'); args=ap.parse_args()
    cfg=json.loads((ROOT/'thresholds.json').read_text()); failures=[]; langs=args.lang or LANGS
    for lang in langs:
        base=ROOT/'baselines'/f'{lang}.json'; cur=ROOT/'results'/f'{lang}.json'
        if not cur.exists(): print(f'::warning::{lang}: missing current result; skipping'); continue
        if not base.exists():
            msg=f'{lang}: missing baseline {base}'
            if args.allow_missing_baseline: print('::warning::'+msg); continue
            failures.append((lang,'<all>','missing baseline','','')); continue
        base_data=json.loads(base.read_text())
        if base_data.get('runner_version')=='placeholder-baseline':
            print(f'::warning::{lang}: baseline is a placeholder; skipping regression check (refresh baselines per tests/benchmarks/README.md)'); continue
        b=scenarios(base_data); c=scenarios(json.loads(cur.read_text())); th=cfg.get('languages',{}).get(lang,cfg['default'])
        for name,cs in c.items():
            if name not in b:
                if args.allow_missing_baseline: print(f'::warning::{lang}/{name}: no baseline scenario'); continue
                failures.append((lang,name,'missing scenario','','')); continue
            bs=b[name]
            drop_msg=-pct(bs['msg_per_sec'], cs['msg_per_sec']); drop_mb=-pct(bs['mb_per_sec'], cs['mb_per_sec']); inc_p99=pct(bs['latency_ns']['p99'], cs['latency_ns']['p99'])
            if drop_msg > th['throughput_drop_pct']: failures.append((lang,name,'msg/sec drop',f'{drop_msg:.1f}%',f">{th['throughput_drop_pct']}%"))
            if drop_mb > th['mb_per_sec_drop_pct']: failures.append((lang,name,'MB/sec drop',f'{drop_mb:.1f}%',f">{th['mb_per_sec_drop_pct']}%"))
            if inc_p99 > th['p99_increase_pct']: failures.append((lang,name,'p99 increase',f'{inc_p99:.1f}%',f">{th['p99_increase_pct']}%"))
    if failures:
        print('| language | scenario | metric | observed | threshold |'); print('|---|---|---|---:|---:|')
        for row in failures: print('| '+' | '.join(row)+' |')
        return 1
    print('No benchmark regressions detected.')
    return 0
if __name__=='__main__': raise SystemExit(main())
