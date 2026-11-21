"""python -m struct_frame.builtin --write | --check"""

import argparse
import sys

from struct_frame import builtin


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m struct_frame.builtin",
                                 description="Regenerate the built-in schemas committed into the runtimes.")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="regenerate the committed files")
    mode.add_argument("--check", action="store_true", help="exit 1 when the committed files are stale")
    args = ap.parse_args(argv)
    if args.write:
        for path in builtin.write():
            print(f"wrote boilerplate/{path}")
        print("Now recompile the JavaScript runtime: npx tsc -p src/struct_frame/boilerplate/ts/tsconfig.cjs.json")
        return 0
    stale = builtin.stale()
    if stale:
        print("The built-in schema code in boilerplate/ is stale:", file=sys.stderr)
        for path in stale:
            print(f"  {path}", file=sys.stderr)
        print("Run: python -m struct_frame.builtin --write", file=sys.stderr)
        return 1
    print("built-in schema code is up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
