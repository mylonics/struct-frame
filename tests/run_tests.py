#!/usr/bin/env python3
"""
Generic Test Suite Runner for struct-frame Project

This script is completely configuration-driven. It reads test_config.json
and executes all tests without any hardcoded knowledge of what tests exist.

Usage:
    python run_tests.py [--config CONFIG] [--verbose] [--skip-lang LANG] [--only-generate]
"""

import argparse
import json
import os
import sys
import subprocess
import shutil
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from contextlib import contextmanager


class ConfigDrivenTestRunner:
    """A completely generic test runner driven by JSON configuration"""

    def __init__(self, config_path: str, verbose: bool = False):
        self.verbose = verbose
        self.project_root = Path(__file__).parent.parent
        self.tests_dir = self.project_root / "tests"
        self.config = self._load_config(Path(config_path))
        self.skipped_languages = []

        # Initialize results tracking
        self.results = {k: {} for k in [
            'generation', 'compilation', 'tests', 'cross_platform']}
        for lang_id in self.config['languages']:
            self.results['generation'][lang_id] = False
            self.results['compilation'][lang_id] = False
            self.results['tests'][lang_id] = {}

    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """Load the test configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self._log(f"Configuration file not found: {config_path}", "ERROR")
            sys.exit(1)
        except json.JSONDecodeError as e:
            self._log(f"Invalid JSON in configuration file: {e}", "ERROR")
            sys.exit(1)

    def _log(self, message: str, level: str = "INFO"):
        """Log a message with optional verbose output"""
        if level in ("ERROR", "SUCCESS") or self.verbose:
            prefix = {"INFO": "[INFO] ", "ERROR": "[ERROR]",
                      "SUCCESS": "[OK]", "WARNING": "[WARN] "}.get(level, "  ")
            print(f"{prefix} {message}")

    def _run_command(self, command: str, cwd: Optional[Path] = None,
                     env: Optional[Dict[str, str]] = None, timeout: int = 30) -> Tuple[bool, str, str]:
        """Run a shell command and return (success, stdout, stderr)"""
        cmd_env = {**os.environ, **(env or {})}
        try:
            result = subprocess.run(
                command, shell=True, cwd=cwd or self.project_root,
                capture_output=True, text=True, timeout=timeout, env=cmd_env
            )
            if self.verbose:
                if result.stdout:
                    print(f"  STDOUT: {result.stdout}")
                if result.stderr:
                    print(f"  STDERR: {result.stderr}")
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            self._log(f"Command timed out after {timeout}s", "ERROR")
            return False, "", "Timeout"
        except Exception as e:
            self._log(f"Command execution failed: {e}", "ERROR")
            return False, "", str(e)

    def _get_lang_env(self, lang_id: str) -> Dict[str, str]:
        """Get environment variables for a language"""
        lang_config = self.config['languages'][lang_id]
        execution = lang_config.get('execution', {})
        env = {}
        if 'env' in execution:
            gen_dir = str(self.project_root /
                          lang_config['code_generation']['output_dir'])
            env = {k: v.replace('{generated_dir}', gen_dir)
                   for k, v in execution['env'].items()}
        return env

    def _get_active_languages(self) -> List[str]:
        """Get list of enabled languages that are not skipped"""
        return [lang_id for lang_id, cfg in self.config['languages'].items()
                if cfg.get('enabled', True) and lang_id not in self.skipped_languages]

    def check_tool_availability(self) -> Dict[str, Dict[str, Any]]:
        """Check which compilers/interpreters are available for each language.

        Returns a dict mapping lang_id to availability info:
        {
            'lang_id': {
                'name': 'Language Name',
                'available': True/False,
                'compiler': {'name': 'gcc', 'available': True, 'version': '...'},
                'interpreter': {'name': 'python', 'available': True, 'version': '...'},
                'reason': 'why unavailable' (only if not available)
            }
        }
        """
        results = {}

        for lang_id, lang_config in self.config['languages'].items():
            if not lang_config.get('enabled', True):
                continue

            info = {
                'name': lang_config['name'],
                'available': True,
                'compiler': None,
                'interpreter': None,
            }

            # Check compiler if compilation is enabled
            comp = lang_config.get('compilation', {})
            if comp.get('enabled'):
                compiler = comp.get('compiler', '')
                check_cmd = comp.get('compiler_check', f"{compiler} --version")
                success, stdout, stderr = self._run_command(
                    check_cmd, timeout=5)

                version = ""
                if success:
                    # Extract first line of version output
                    output = stdout or stderr
                    version = output.strip().split('\n')[0] if output else ""

                info['compiler'] = {
                    'name': compiler,
                    'available': success,
                    'version': version
                }

                if not success:
                    info['available'] = False
                    info['reason'] = f"Compiler '{compiler}' not found"

            # Check interpreter if execution config exists
            execution = lang_config.get('execution', {})
            if execution.get('interpreter'):
                interpreter = execution['interpreter']
                success, stdout, stderr = self._run_command(
                    f"{interpreter} --version", timeout=5)

                version = ""
                if success:
                    output = stdout or stderr
                    version = output.strip().split('\n')[0] if output else ""

                info['interpreter'] = {
                    'name': interpreter,
                    'available': success,
                    'version': version
                }

                if not success:
                    info['available'] = False
                    info['reason'] = f"Interpreter '{interpreter}' not found"

            results[lang_id] = info

        return results

    def print_tool_availability(self) -> bool:
        """Print a summary of available tools and return True if all tools available."""
        self._print_section("TOOL AVAILABILITY CHECK")

        availability = self.check_tool_availability()
        all_available = True

        for lang_id, info in availability.items():
            status = "[OK]" if info['available'] else "[FAIL]"
            print(f"\n  {status} {info['name']}")

            if info['compiler']:
                comp = info['compiler']
                comp_status = "[OK]" if comp['available'] else "[FAIL]"
                version_str = f" ({comp['version']})" if comp['version'] else ""
                print(
                    f"      Compiler:    {comp_status} {comp['name']}{version_str}")

            if info['interpreter']:
                interp = info['interpreter']
                interp_status = "[OK]" if interp['available'] else "[FAIL]"
                version_str = f" ({interp['version']})" if interp['version'] else ""
                print(
                    f"      Interpreter: {interp_status} {interp['name']}{version_str}")

            if not info['available']:
                all_available = False
                print(f"      [WARN] {info.get('reason', 'Unknown issue')}")

        print()
        return all_available

    def get_available_languages(self) -> List[str]:
        """Get list of languages that have all required tools available."""
        availability = self.check_tool_availability()
        return [lang_id for lang_id, info in availability.items()
                if info['available'] and lang_id not in self.skipped_languages]

    @contextmanager
    def _temp_copy(self, src: Path, dst: Path):
        """Context manager to temporarily copy a file and clean up"""
        copied = False
        try:
            if src.resolve() != dst.resolve():
                shutil.copy2(src, dst)
                copied = True
            yield
        finally:
            if copied and dst.exists():
                try:
                    dst.unlink()
                except:
                    pass

    def _run_test_script(self, lang_id: str, test_config: Dict[str, Any],
                         test_dir: Path = None) -> bool:
        """Run a test script for any language - unified execution logic"""
        lang_config = self.config['languages'][lang_id]
        test_dir = test_dir or (self.project_root / lang_config['test_dir'])
        execution = lang_config.get('execution', {})

        # Compiled executable
        if 'executable' in test_config:
            exe_path = test_dir / test_config['executable']
            return exe_path.exists() and self._run_command(str(exe_path), cwd=test_dir)[0]

        # TypeScript (runs compiled JS)
        if lang_id == 'ts' and 'compiled_file' in test_config:
            script_dir = self.project_root / execution.get('script_dir', '')
            script_path = script_dir / test_config['compiled_file']
            if not script_path.exists():
                return False
            return self._run_command(
                f"{execution['interpreter']} {script_path.name}", cwd=script_dir)[0]

        # Interpreted language (Python, etc.)
        if 'source_file' in test_config:
            source_path = test_dir / test_config['source_file']
            if not source_path.exists():
                return False
            interpreter = execution.get('interpreter')
            if not interpreter:
                return False
            return self._run_command(
                f"{interpreter} {source_path.name}",
                cwd=test_dir, env=self._get_lang_env(lang_id))[0]

        return False

    # ─────────────────────────────────────────────────────────────────────────
    # Code Generation
    # ─────────────────────────────────────────────────────────────────────────

    def generate_code(self) -> bool:
        """Generate code for all proto files and enabled languages"""
        self._print_section("CODE GENERATION")

        active = self._get_active_languages()
        all_success = True

        for proto_file in self.config.get('proto_files', []):
            proto_path = self.tests_dir / "proto" / proto_file
            if not proto_path.exists():
                self._log(f"Proto file not found: {proto_file}", "WARNING")
                continue

            # Build generation command
            cmd_parts = [sys.executable, "-m", "struct_frame", str(proto_path)]
            for lang_id in active:
                gen = self.config['languages'][lang_id]['code_generation']
                cmd_parts += [gen['flag'], gen['output_path_flag'],
                              str(self.project_root / gen['output_dir'])]

            env = {"PYTHONPATH": str(self.project_root / "src")}
            success, _, _ = self._run_command(" ".join(cmd_parts), env=env)

            if success:
                for lang_id in active:
                    self.results['generation'][lang_id] = True
            else:
                self._log(f"Code generation failed for {proto_file}", "ERROR")
                all_success = False

        self._print_lang_results(active, self.results['generation'])
        return all_success

    # ─────────────────────────────────────────────────────────────────────────
    # Compilation
    # ─────────────────────────────────────────────────────────────────────────

    def compile_all(self) -> bool:
        """Compile code for all languages that require compilation"""
        self._print_section("COMPILATION")

        compiled = [l for l in self._get_active_languages()
                    if self.config['languages'][l].get('compilation', {}).get('enabled')]

        if not compiled:
            print("  No languages require compilation")
            return True

        for lang_id in compiled:
            self._compile_language(lang_id)

        self._print_lang_results(compiled, self.results['compilation'])
        return all(self.results['compilation'].get(l, False) for l in compiled)

    def _compile_language(self, lang_id: str) -> bool:
        """Compile code for a specific language"""
        lang_config = self.config['languages'][lang_id]
        comp = lang_config.get('compilation', {})

        # Check compiler availability
        if comp.get('compiler_check'):
            if not self._run_command(comp['compiler_check'])[0]:
                self._log(
                    f"{lang_config['name']} compiler not found - skipping", "WARNING")
                return True

        test_dir = self.project_root / lang_config['test_dir']
        gen_dir = self.project_root / \
            lang_config['code_generation']['output_dir']
        all_success = True

        # Compile test files from suites
        for suite in self.config['test_suites']:
            tests = suite.get('tests', {}).get(lang_id, {})
            for key in ['', 'encode', 'decode']:
                cfg = tests.get(key, tests) if key else tests
                if isinstance(cfg, dict) and 'source_file' in cfg and 'executable' in cfg:
                    if not self._compile_file(lang_id, test_dir / cfg['source_file'],
                                              test_dir / cfg['executable'], gen_dir):
                        all_success = False

        # TypeScript special handling
        if lang_id == 'ts' and comp.get('command'):
            for ts_file in test_dir.glob("*.ts"):
                shutil.copy2(ts_file, gen_dir / ts_file.name)
            output_dir = self.project_root / comp['output_dir']
            cmd = comp['command'].format(
                output_dir=output_dir, generated_dir=gen_dir)
            all_success = self._run_command(cmd)[0] and all_success

        self.results['compilation'][lang_id] = all_success
        return all_success

    def _compile_file(self, lang_id: str, source: Path, output: Path, gen_dir: Path) -> bool:
        """Compile a single source file"""
        if not source.exists():
            return False
        comp = self.config['languages'][lang_id]['compilation']
        flags = [f.replace('{generated_dir}', str(gen_dir))
                  .replace('{output}', str(output))
                  .replace('{source}', str(source)) for f in comp.get('flags', [])]
        return self._run_command(f"{comp['compiler']} {' '.join(flags)}")[0]

    # ─────────────────────────────────────────────────────────────────────────
    # Test Execution
    # ─────────────────────────────────────────────────────────────────────────

    def run_test_suites(self):
        """Run all non-cross-platform test suites"""
        for suite in self.config['test_suites']:
            if suite['name'] == 'cross_platform':
                continue
            print(f"\n[TEST] {suite['description']}")

            for lang_id in self._get_active_languages():
                test_config = suite.get('tests', {}).get(lang_id)
                if test_config:
                    result = self._run_test_script(lang_id, test_config)
                    self.results['tests'][lang_id][suite['name']] = result

            self._print_lang_results(
                self._get_active_languages(),
                {l: self.results['tests'][l].get(suite['name'], False)
                 for l in self._get_active_languages()}
            )

    def run_cross_platform_tests(self) -> bool:
        """Run cross-platform encode/decode tests"""
        self._print_section("CROSS-PLATFORM COMPATIBILITY")

        suite = next(
            (s for s in self.config['test_suites'] if s['name'] == 'cross_platform'), None)
        if not suite:
            self._log("No cross-platform test suite configured", "WARNING")
            return True

        active = self._get_active_languages()

        # Step 1: Generate test data from all encoders
        print("Generating test data files...")
        encoded_files = {}
        for lang_id in active:
            encode_cfg = suite.get('tests', {}).get(lang_id, {}).get('encode')
            if not encode_cfg:
                continue

            lang_config = self.config['languages'][lang_id]
            test_dir = self.project_root / lang_config['test_dir']

            if self._run_test_script(lang_id, encode_cfg, test_dir):
                output_file = encode_cfg.get('output_file')
                if output_file:
                    # TypeScript outputs to JS directory
                    if lang_id == 'ts':
                        script_dir = self.project_root / \
                            lang_config['execution'].get('script_dir', '')
                        output_path = script_dir / output_file
                    else:
                        output_path = test_dir / output_file

                    if output_path.exists():
                        encoded_files[lang_id] = output_path

        # Step 2: Run decoders on all encoded files
        print("Testing cross-platform deserialization...")
        matrix = {}

        for enc_lang, data_file in encoded_files.items():
            enc_name = self.config['languages'][enc_lang]['name']
            matrix[enc_name] = {}

            for dec_lang in active:
                dec_name = self.config['languages'][dec_lang]['name']
                decode_cfg = suite.get('tests', {}).get(
                    dec_lang, {}).get('decode')
                if not decode_cfg:
                    continue

                lang_config = self.config['languages'][dec_lang]
                test_dir = self.project_root / lang_config['test_dir']
                target_file = test_dir / data_file.name

                try:
                    with self._temp_copy(data_file, target_file):
                        # TypeScript needs file in JS directory too
                        if dec_lang == 'ts' and 'compiled_file' in decode_cfg:
                            script_dir = self.project_root / \
                                lang_config['execution'].get('script_dir', '')
                            ts_target = script_dir / data_file.name
                            with self._temp_copy(data_file, ts_target):
                                matrix[enc_name][dec_name] = self._run_test_script(
                                    dec_lang, decode_cfg, test_dir)
                        else:
                            matrix[enc_name][dec_name] = self._run_test_script(
                                dec_lang, decode_cfg, test_dir)
                except Exception as e:
                    if self.verbose:
                        self._log(
                            f"{dec_name} decode of {enc_name} failed: {e}", "WARNING")
                    matrix[enc_name][dec_name] = False

        self._print_compatibility_matrix(matrix)
        self.results['cross_platform'] = matrix
        return sum(sum(d.values()) for d in matrix.values()) > 0

    # ─────────────────────────────────────────────────────────────────────────
    # Output Formatting
    # ─────────────────────────────────────────────────────────────────────────

    def _print_section(self, title: str):
        print(f"\n{'='*60}\n{title}\n{'='*60}")

    def _print_lang_results(self, languages: List[str], results: Dict[str, bool]):
        print()
        for lang_id in languages:
            name = self.config['languages'][lang_id]['name']
            status = "PASS" if results.get(lang_id, False) else "FAIL"
            print(f"  {name:>10}: {status}")

    def _print_compatibility_matrix(self, matrix: Dict[str, Dict[str, bool]]):
        if not matrix:
            return

        all_langs = sorted(set(matrix.keys()) | set().union(
            *[set(d.keys()) for d in matrix.values()]))

        print("\nCompatibility Matrix:")
        header = "Encoder\\Decoder".ljust(
            18) + "".join(l[:8].ljust(10) for l in all_langs)
        print(header)
        print("-" * len(header))

        for encoder in all_langs:
            if encoder in matrix:
                row = encoder.ljust(18)
                row += "".join((" OK " if matrix[encoder].get(d) else " FAIL " if d in matrix[encoder] else "  --  ").rjust(10)
                               for d in all_langs)
                print(row)

        total = sum(len(d) for d in matrix.values())
        success = sum(sum(d.values()) for d in matrix.values())
        if total:
            print(
                f"\nSuccess rate: {success}/{total} ({100*success/total:.0f}%)\n")

    def print_summary(self) -> bool:
        """Print summary of all test results"""
        self._print_section("TEST RESULTS SUMMARY")

        active = self._get_active_languages()

        # Count all results
        passed = total = 0

        # Generation
        for lang_id in active:
            total += 1
            passed += self.results['generation'][lang_id]

        # Compilation
        for lang_id in active:
            if self.config['languages'][lang_id].get('compilation', {}).get('enabled'):
                total += 1
                passed += self.results['compilation'][lang_id]

        # Tests
        for lang_id in active:
            for result in self.results['tests'][lang_id].values():
                total += 1
                passed += result

        # Cross-platform
        for decoders in self.results['cross_platform'].values():
            for result in decoders.values():
                total += 1
                passed += result

        print(f"\n{passed}/{total} tests passed")

        if total == 0:
            return False

        rate = 100 * passed / total
        if rate >= 80:
            print(f"SUCCESS: {rate:.1f}% pass rate")
            return True
        elif rate >= 50:
            print(f"PARTIAL SUCCESS: {rate:.1f}% pass rate")
            return True
        else:
            print(f"NEEDS WORK: {rate:.1f}% pass rate")
            return False

    # ─────────────────────────────────────────────────────────────────────────
    # Main Entry Point
    # ─────────────────────────────────────────────────────────────────────────

    def run_all_tests(self, generate_only: bool = False) -> bool:
        """Run the complete test suite"""
        print("Starting struct-frame Test Suite")
        print(f"Project root: {self.project_root}")

        # Check tool availability first
        self.print_tool_availability()
        available_langs = self.get_available_languages()

        if not available_langs:
            print("[ERROR] No languages have all required tools available")
            return False

        # Filter to only available languages
        active = [l for l in self._get_active_languages()
                  if l in available_langs]
        lang_names = [self.config['languages'][l]['name'] for l in active]
        print(f"Testing languages: {', '.join(lang_names)}")

        start_time = time.time()

        try:
            # Create output directories
            for lang_id, cfg in self.config['languages'].items():
                if cfg.get('enabled', True):
                    (self.project_root / cfg['code_generation']
                     ['output_dir']).mkdir(parents=True, exist_ok=True)

            if not self.generate_code():
                print("[ERROR] Code generation failed - aborting remaining tests")
                return False

            if generate_only:
                print("[OK] Code generation completed successfully")
                return True

            self.compile_all()
            self.run_test_suites()
            self.run_cross_platform_tests()
            success = self.print_summary()

            print(
                f"\nTotal test time: {time.time() - start_time:.2f} seconds")
            return success

        except KeyboardInterrupt:
            print("\n[WARN] Test run interrupted by user")
            return False
        except Exception as e:
            print(f"\n[ERROR] Test run failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Run configuration-driven tests for struct-frame")
    parser.add_argument("--config", default="tests/test_config.json",
                        help="Path to test configuration file")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose output")
    parser.add_argument("--skip-lang", action="append",
                        dest="skip_languages", help="Skip specific language")
    parser.add_argument("--only-generate", action="store_true",
                        help="Only run code generation")
    parser.add_argument("--check-tools", action="store_true",
                        help="Only check tool availability, don't run tests")

    args = parser.parse_args()
    runner = ConfigDrivenTestRunner(args.config, verbose=args.verbose)
    runner.skipped_languages = args.skip_languages or []

    if args.check_tools:
        all_available = runner.print_tool_availability()
        sys.exit(0 if all_available else 1)

    sys.exit(0 if runner.run_all_tests(
        generate_only=args.only_generate) else 1)


if __name__ == "__main__":
    main()
