"""
Consolidated Test Runner for struct-frame Project.

This module combines base utilities, code generation, compilation,
test execution, and output formatting into a single, simplified runner.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from languages import Language


class TestRunner:
    """
    Configuration-driven test runner for struct-frame.

    Handles code generation, compilation, test execution, and result formatting.
    """

    def __init__(self, config_path: str, verbose: bool = False,
                 verbose_failure: bool = False):
        self.verbose = verbose
        self.verbose_failure = verbose_failure
        self.project_root = Path(__file__).parent.parent
        self.tests_dir = self.project_root / "tests"
        self.config = self._load_config(Path(config_path))
        self.skipped_languages: List[str] = []

        # Cache language instances
        self._languages: Dict[str, 'Language'] = {}
        
        # Cache tool availability (expensive to compute)
        self._tool_availability: Optional[Dict[str, Dict[str, Any]]] = None

        # Results tracking
        self.generation_results: Dict[str, bool] = {}
        self.compilation_results: Dict[str, bool] = {}
        self.test_results: Dict[str, Dict[str, bool]] = {}
        self.cross_platform_results: Dict[str, Dict[str, Any]] = {}

        # Output files from test suites (for cross-platform tests)
        self._output_files: Dict[str, Dict[str, Path]] = {}

    # =========================================================================
    # Configuration Loading
    # =========================================================================

    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """Load the test configuration from JSON file(s)."""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except FileNotFoundError:
            print(f"[ERROR] Configuration file not found: {config_path}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON in configuration file: {e}")
            sys.exit(1)

        config_dir = config_path.parent

        # Load language IDs from languages.py module
        from languages import get_all_language_ids, BASE_LANGUAGE
        config['language_ids'] = get_all_language_ids()
        config['base_language'] = BASE_LANGUAGE

        # Load and merge test suites file if specified
        if 'test_suites_file' in config:
            suites_path = config_dir / config['test_suites_file']
            try:
                with open(suites_path, 'r') as f:
                    suites_config = json.load(f)
                    if 'test_suites' in suites_config:
                        config['test_suites'] = suites_config['test_suites']
            except FileNotFoundError:
                print(f"[ERROR] Test suites file not found: {suites_path}")
                sys.exit(1)
            except json.JSONDecodeError as e:
                print(f"[ERROR] Invalid JSON in test suites file: {e}")
                sys.exit(1)

        return config

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def log(self, message: str, level: str = "INFO"):
        """Log a message with optional verbose output."""
        if level in ("ERROR", "SUCCESS") or self.verbose:
            prefix = {"INFO": "[INFO] ", "ERROR": "[ERROR]",
                      "SUCCESS": "[OK]", "WARNING": "[WARN] "}.get(level, "  ")
            print(f"{prefix} {message}")

    def run_command(self, command: str, cwd: Optional[Path] = None,
                    env: Optional[Dict[str, str]] = None, timeout: int = 30) -> Tuple[bool, str, str]:
        """Run a shell command and return (success, stdout, stderr)."""
        cmd_env = {**os.environ, **(env or {})}
        try:
            result = subprocess.run(
                command, shell=True, cwd=cwd or self.project_root,
                capture_output=True, text=True, timeout=timeout, env=cmd_env
            )
            success = result.returncode == 0
            if self.verbose:
                if result.stdout:
                    print(f"  STDOUT: {result.stdout}")
                if result.stderr:
                    print(f"  STDERR: {result.stderr}")
            elif self.verbose_failure and not success:
                if result.stdout:
                    print(f"  STDOUT: {result.stdout}")
                if result.stderr:
                    print(f"  STDERR: {result.stderr}")
            return success, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            self.log(f"Command timed out after {timeout}s", "ERROR")
            return False, "", "Timeout"
        except Exception as e:
            self.log(f"Command execution failed: {e}", "ERROR")
            return False, "", str(e)

    @contextmanager
    def temp_copy(self, src: Path, dst: Path):
        """Context manager to temporarily copy a file and clean up."""
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

    def get_lang(self, lang_id: str) -> Optional['Language']:
        """Get a Language instance for the given language ID."""
        if lang_id not in self._languages:
            from languages import get_language
            lang = get_language(lang_id, self.project_root)
            if lang:
                lang.verbose = self.verbose
                lang.verbose_failure = self.verbose_failure
                self._languages[lang_id] = lang
        return self._languages.get(lang_id)

    def get_active_languages(self) -> List[str]:
        """Get list of enabled languages that are not skipped."""
        return [lang_id for lang_id in self.config['language_ids']
                if self.get_lang(lang_id) and self.get_lang(lang_id).enabled
                and lang_id not in self.skipped_languages]

    def get_testable_languages(self) -> List[str]:
        """Get list of enabled languages that can run tests (excludes generation_only)."""
        result = []
        for lang_id in self.config['language_ids']:
            lang = self.get_lang(lang_id)
            if lang and lang.enabled and not lang.generation_only and lang_id not in self.skipped_languages:
                result.append(lang_id)
        return result

    # =========================================================================
    # Output Formatting
    # =========================================================================

    def print_section(self, title: str):
        """Print a section header."""
        print(f"\n{'='*60}\n{title}\n{'='*60}")

    def print_lang_results(self, languages: List[str], results: Dict[str, bool]):
        """Print results for each language."""
        print()
        for lang_id in languages:
            lang = self.get_lang(lang_id)
            name = lang.name if lang else lang_id
            status = "PASS" if results.get(lang_id, False) else "FAIL"
            print(f"  {name:>10}: {status}")

    # =========================================================================
    # Tool Checking
    # =========================================================================

    def check_tool_availability(self) -> Dict[str, Dict[str, Any]]:
        """Check which compilers/interpreters are available for each language.
        
        Results are cached since tool availability doesn't change during a test run.
        """
        if self._tool_availability is not None:
            return self._tool_availability
            
        results = {}
        for lang_id in self.config['language_ids']:
            lang = self.get_lang(lang_id)
            if not lang or not lang.enabled:
                continue
            results[lang_id] = lang.check_tools()
        
        self._tool_availability = results
        return results

    def print_tool_availability(self) -> bool:
        """Print a summary of available tools and return True if all available."""
        self.print_section("TOOL AVAILABILITY CHECK")
        availability = self.check_tool_availability()
        all_available = True

        for lang_id, info in availability.items():
            status = "[OK]" if info['available'] else "[FAIL]"
            print(f"\n  {status} {info['name']}")

            if info.get('generation_only'):
                print(f"      (generation only)")
                continue

            if info.get('compiler'):
                comp = info['compiler']
                comp_status = "[OK]" if comp['available'] else "[FAIL]"
                version_str = f" ({comp['version']})" if comp['version'] else ""
                print(
                    f"      Compiler:    {comp_status} {comp['name']}{version_str}")

            if info.get('interpreter'):
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

    # =========================================================================
    # Code Generation
    # =========================================================================

    def generate_code(self) -> bool:
        """Generate code for all proto files and enabled languages."""
        self.print_section("CODE GENERATION")
        active = self.get_active_languages()
        all_success = True
        
        proto_files = self.config.get('proto_files', [])
        lang_names = [self.get_lang(l).name for l in active if self.get_lang(l)]
        print(f"  Generating code for {len(proto_files)} proto file(s) in languages: {', '.join(lang_names)}")

        for proto_file in proto_files:
            proto_path = self.tests_dir / "proto" / proto_file
            if not proto_path.exists():
                self.log(f"Proto file not found: {proto_file}", "WARNING")
                continue
            
            print(f"  Processing: {proto_file}...")

            # Build generation command
            cmd_parts = [sys.executable, "-m", "struct_frame", str(proto_path)]
            for lang_id in active:
                lang = self.get_lang(lang_id)
                if lang:
                    cmd_parts += [lang.gen_flag, lang.gen_output_path_flag,
                                  str(self.project_root / lang.gen_output_dir)]

            env = {"PYTHONPATH": str(self.project_root / "src")}
            success, _, _ = self.run_command(" ".join(cmd_parts), env=env)

            if success:
                for lang_id in active:
                    self.generation_results[lang_id] = True
            else:
                self.log(f"Code generation failed for {proto_file}", "ERROR")
                all_success = False

        self.print_lang_results(active, self.generation_results)
        return all_success

    # =========================================================================
    # Compilation
    # =========================================================================

    def compile_all(self) -> bool:
        """Compile code for all languages that require compilation."""
        self.print_section("COMPILATION (all test files)")

        # Copy JS test files first (no compilation needed but files must be in place)
        self._copy_js_test_files()

        compiled = [l for l in self.get_active_languages()
                    if self.get_lang(l) and self.get_lang(l).compiler]

        if not compiled:
            print("  No languages require compilation")
            return True
        
        lang_names = [self.get_lang(l).name for l in compiled if self.get_lang(l)]
        print(f"  Compiling: {', '.join(lang_names)}")

        for lang_id in compiled:
            lang = self.get_lang(lang_id)
            print(f"  Building {lang.name if lang else lang_id}...")
            self._compile_language(lang_id)

        self.print_lang_results(compiled, self.compilation_results)
        return all(self.compilation_results.get(l, False) for l in compiled)

    def _copy_js_test_files(self):
        """Copy JavaScript test files to the generated JS directory."""
        lang = self.get_lang('js')
        if not lang or not lang.enabled:
            return

        test_dir = lang.get_test_dir()
        script_dir = lang.get_script_dir()

        if script_dir:
            script_dir.mkdir(parents=True, exist_ok=True)
            for filename in ['test_runner.js', 'test_codec.js']:
                source_file = test_dir / filename
                if source_file.exists():
                    shutil.copy2(source_file, script_dir / filename)

    def _compile_language(self, lang_id: str) -> bool:
        """Compile code for a specific language."""
        lang = self.get_lang(lang_id)
        if not lang:
            return False

        compiler_info = lang.check_compiler()
        if not compiler_info['available']:
            self.log(f"{lang.name} compiler not found - skipping", "WARNING")
            return True

        test_dir = lang.get_test_dir()
        build_dir = lang.get_build_dir()
        gen_dir = lang.get_gen_dir()
        all_success = True

        build_dir.mkdir(parents=True, exist_ok=True)

        # Compile unified test_runner with test_codec for C/C++
        source_ext = lang.source_extension
        exe_ext = lang.executable_extension

        if exe_ext and source_ext in ['.c', '.cpp']:
            runner_source = test_dir / f"test_runner{source_ext}"
            codec_source = test_dir / f"test_codec{source_ext}"
            runner_output = build_dir / f"test_runner{exe_ext}"

            sources = [runner_source, codec_source]
            
            # Add cJSON.c for C language
            if source_ext == '.c':
                cjson_source = test_dir / "cJSON.c"
                if cjson_source.exists():
                    sources.append(cjson_source)

            if runner_source.exists() and codec_source.exists():
                if not lang.compile(sources, runner_output, gen_dir):
                    all_success = False

        # Project-based compilation (TypeScript, C#)
        if lang.compile_command and source_ext:
            if source_ext == '.ts':
                for source_file in test_dir.glob(f"*{source_ext}"):
                    shutil.copy2(source_file, gen_dir / source_file.name)

                # Create tsconfig.json in generated dir
                tsconfig_path = gen_dir / 'tsconfig.json'
                if not tsconfig_path.exists():
                    tsconfig = {
                        "extends": "../../ts/tsconfig.json",
                        "compilerOptions": {
                            "rootDir": ".",
                            "outDir": "./js",
                            "baseUrl": "../../ts",
                            "paths": {
                                "typed-struct": ["node_modules/typed-struct"],
                                "*": ["node_modules/*", "node_modules/@types/*"]
                            },
                            "types": ["node"],
                            "typeRoots": ["../../ts/node_modules/@types"]
                        },
                        "include": [f"./*{source_ext}"]
                    }
                    tsconfig_path.write_text(json.dumps(tsconfig, indent=2))

            if not lang.compile_project(test_dir, build_dir, gen_dir):
                all_success = False

        self.compilation_results[lang_id] = all_success
        return all_success

    # =========================================================================
    # Test Execution
    # =========================================================================

    def run_standalone_tests(self):
        """Run standalone test scripts (e.g., test_packaging.py)."""
        # Find all test_*.py files in the tests directory
        test_scripts = list(self.tests_dir.glob("test_*.py"))
        
        if not test_scripts:
            return
        
        print(f"\n  Running {len(test_scripts)} standalone Python test(s)...")
        
        for test_script in test_scripts:
            script_name = test_script.name
            self.log(f"Running {script_name}...", "INFO")
            
            # Run the test script
            success, stdout, stderr = self.run_command(
                f'python "{test_script}"',
                cwd=self.tests_dir,
                timeout=30
            )
            
            # Always show output from standalone tests
            if stdout:
                print(stdout)
            if stderr and not success:
                print(stderr)
            
            # Track result
            test_name = script_name.replace('test_', '').replace('.py', '')
            if 'python' not in self.test_results:
                self.test_results['python'] = {}
            self.test_results['python'][f"standalone_{test_name}"] = success

    def run_test_suites(self):
        """Run all test suites using appropriate plugins."""
        from plugins import get_plugin

        self.print_section("TEST EXECUTION")
        
        test_suites = self.config.get('test_suites', [])
        print(f"  Running {len(test_suites)} test suite(s)...")

        for suite in test_suites:
            print(f"\n  Starting test suite: {suite.get('name', 'unnamed')}")
            plugin_type = suite.get('plugin', 'standard')
            if 'input_from' in suite and plugin_type == 'standard':
                plugin_type = 'cross_platform_matrix'

            plugin = get_plugin(plugin_type, self)
            result = plugin.run(suite)

            # Merge results
            for lang_id, lang_results in result.get('results', {}).items():
                if lang_id not in self.test_results:
                    self.test_results[lang_id] = {}
                self.test_results[lang_id].update(lang_results)

            # Store output files if produced
            if result.get('output_files'):
                self._output_files[suite['name']] = result['output_files']

            # Store cross-platform matrix if produced
            if result.get('matrix'):
                self.cross_platform_results = result['matrix']

    def get_output_files(self, suite_name: str) -> Dict[str, Path]:
        """Get output files produced by a suite."""
        return self._output_files.get(suite_name, {})

    def run_test_runner(self, lang_id: str, mode: str, format_name: str,
                        output_file: Path) -> tuple[bool, int]:
        """Run the unified test_runner for a language.
        
        Returns:
            (success, message_count): success status and number of messages decoded (for decode mode)
        """
        lang = self.get_lang(lang_id)
        if not lang:
            return False, 0

        build_dir = lang.get_build_dir()
        build_dir.mkdir(parents=True, exist_ok=True)

        # Compiled executable (C, C++)
        if lang.executable_extension:
            runner_path = build_dir / f"test_runner{lang.executable_extension}"
            if not runner_path.exists():
                return False, 0
            cmd = f'"{runner_path}" {mode} {format_name} "{output_file}"'
            success, stdout, stderr = self.run_command(cmd, cwd=build_dir)
            message_count = self._extract_message_count(stdout, mode)
            return success, message_count

        # C# (dotnet run)
        if lang.execution_type == 'dotnet':
            test_dir = lang.get_test_dir()
            csproj_path = test_dir / 'StructFrameTests.csproj'
            if not csproj_path.exists():
                return False, 0
            cmd = f'dotnet run --project "{csproj_path}" --verbosity quiet -- {mode} {format_name} "{output_file}"'
            success, stdout, stderr = self.run_command(cmd, cwd=test_dir)
            message_count = self._extract_message_count(stdout, mode)
            return success, message_count

        # TypeScript (compiles to JS)
        if lang.compiled_extension:
            script_dir = lang.get_script_dir()
            if not script_dir:
                return False, 0
            runner_path = script_dir / 'test_runner.js'
            if not runner_path.exists():
                return False, 0
            interpreter = lang.interpreter or 'node'
            cmd = f'{interpreter} "{runner_path}" {mode} {format_name} "{output_file}"'
            success, stdout, stderr = self.run_command(cmd, cwd=script_dir)
            message_count = self._extract_message_count(stdout, mode)
            return success, message_count

        # Interpreted languages (Python, JavaScript)
        if lang.interpreter:
            script_dir = lang.get_script_dir()
            if script_dir:
                runner_path = script_dir / 'test_runner.js'
            else:
                test_dir = lang.get_test_dir()
                source_ext = lang.source_extension or '.py'
                runner_path = test_dir / f'test_runner{source_ext}'

            if not runner_path.exists():
                return False, 0

            cwd = runner_path.parent
            env_prefix = ''
            if lang.env_vars:
                gen_dir = lang.get_gen_dir()
                for key, val in lang.env_vars.items():
                    val = val.replace('{generated_dir}', str(gen_dir))
                    val = val.replace(
                        '{generated_parent_dir}', str(gen_dir.parent))
                    val = val.replace(':', os.pathsep)
                    env_prefix = f'set {key}={val} && ' if os.name == 'nt' else f'{key}={val} '

            cmd = f'{env_prefix}{lang.interpreter} "{runner_path}" {mode} {format_name} "{output_file}"'
            success, stdout, stderr = self.run_command(cmd, cwd=cwd)
            message_count = self._extract_message_count(stdout, mode)
            return success, message_count

        return False, 0
    
    def _extract_message_count(self, stdout: str, mode: str) -> int:
        """Extract message count from test runner stdout.
        
        Looks for pattern: "[DECODE] SUCCESS: N messages validated correctly"
        
        Returns:
            Number of messages decoded, or 0 if not found or not decode mode
        """
        if mode != 'decode' or not stdout:
            return 0
        
        import re
        # Match patterns like "5 messages validated" or "1 message validated"
        match = re.search(r'SUCCESS:\s+(\d+)\s+messages?\s+validated', stdout)
        if match:
            return int(match.group(1))
        return 0

    # =========================================================================
    # Summary
    # =========================================================================

    def print_summary(self) -> bool:
        """Print summary of all test results."""
        self.print_section("TEST RESULTS SUMMARY")

        active_languages = [l for l in self.get_active_languages()
                            if l in self.get_available_languages()]
        passed = total = 0

        # Generation
        for lang_id in active_languages:
            total += 1
            passed += self.generation_results.get(lang_id, False)

        # Compilation
        for lang_id in active_languages:
            lang = self.get_lang(lang_id)
            if lang and lang.compiler:
                total += 1
                passed += self.compilation_results.get(lang_id, False)

        # Tests
        for lang_id in active_languages:
            for result in self.test_results.get(lang_id, {}).values():
                if result is not None and isinstance(result, bool):
                    total += 1
                    passed += result

        # Cross-platform
        for decoders in self.cross_platform_results.values():
            for result in decoders.values():
                if result is None:
                    continue
                if isinstance(result, dict):
                    encode_ok = result.get('encode')
                    decode_ok = result.get('decode')
                    if encode_ok is not None:
                        total += 1
                        passed += encode_ok
                    if decode_ok is not None:
                        total += 1
                        passed += decode_ok
                elif isinstance(result, bool):
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

    # =========================================================================
    # Main Entry Point
    # =========================================================================

    def run_all_tests(self, generate_only: bool = False) -> bool:
        """Run the complete test suite."""
        print("Starting struct-frame Test Suite")
        print(f"Project root: {self.project_root}")

        self.print_tool_availability()
        available_langs = self.get_available_languages()

        if not available_langs:
            print("[ERROR] No languages have all required tools available")
            return False

        active = [l for l in self.get_active_languages()
                  if l in available_langs]
        lang_names = [self.get_lang(l).name for l in active]
        print(f"Testing languages: {', '.join(lang_names)}")

        start_time = time.time()

        try:
            # Create output directories
            for lang_id in self.config['language_ids']:
                lang = self.get_lang(lang_id)
                if lang and lang.enabled:
                    (self.project_root /
                     lang.gen_output_dir).mkdir(parents=True, exist_ok=True)

            if not self.generate_code():
                print("[ERROR] Code generation failed - aborting remaining tests")
                return False

            if generate_only:
                print("[OK] Code generation completed successfully")
                return True

            self.compile_all()
            self.run_test_suites()
            self.run_standalone_tests()
            success = self.print_summary()

            print(f"\nTotal test time: {time.time() - start_time:.2f} seconds")
            return success

        except KeyboardInterrupt:
            print("\n[WARN] Test run interrupted by user")
            return False
        except Exception as e:
            print(f"\n[ERROR] Test run failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False
