#!/usr/bin/env python3
"""
Struct-Frame Test Runner

A clean, consolidated test runner that:
1. Cleans all generated/copied/built files
2. Generates code using struct-frame library
3. Compiles/builds all languages
4. Runs standard tests (basic message types)
5. Runs extended tests (message IDs > 255)
6. Reports test results with encode/decode matrices

Usage:
    python run_tests.py [--verbose] [--skip-lang LANG] [--only-generate] [--check-tools]
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


# =============================================================================
# Color Output Utilities
# =============================================================================

class Colors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    
    _enabled = True
    
    @classmethod
    def disable(cls):
        """Disable colored output."""
        cls._enabled = False
    
    @classmethod
    def enable(cls):
        """Enable colored output."""
        cls._enabled = True
    
    @classmethod
    def _c(cls, color: str, text: str) -> str:
        """Apply color if enabled."""
        if cls._enabled:
            return f"{color}{text}{cls.RESET}"
        return text
    
    @classmethod
    def red(cls, text: str) -> str:
        return cls._c(cls.RED, text)
    
    @classmethod
    def green(cls, text: str) -> str:
        return cls._c(cls.GREEN, text)
    
    @classmethod
    def yellow(cls, text: str) -> str:
        return cls._c(cls.YELLOW, text)
    
    @classmethod
    def blue(cls, text: str) -> str:
        return cls._c(cls.BLUE, text)
    
    @classmethod
    def cyan(cls, text: str) -> str:
        return cls._c(cls.CYAN, text)
    
    @classmethod
    def bold(cls, text: str) -> str:
        return cls._c(cls.BOLD, text)
    
    @classmethod
    def pass_text(cls) -> str:
        return cls.green("PASS")
    
    @classmethod
    def fail_text(cls) -> str:
        return cls.red("FAIL")
    
    @classmethod
    def ok_tag(cls) -> str:
        return cls.green("[OK]")
    
    @classmethod
    def fail_tag(cls) -> str:
        return cls.red("[FAIL]")
    
    @classmethod
    def warn_tag(cls) -> str:
        return cls.yellow("[WARN]")


def _init_colors():
    """Initialize color support based on terminal capabilities."""
    if sys.platform == "win32":
        # Enable ANSI on Windows
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            Colors.disable()
    
    # Disable colors if not a TTY or NO_COLOR is set
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        Colors.disable()

_init_colors()


# =============================================================================
# Configuration
# =============================================================================

# Proto files to generate code from
PROTO_FILES = [
    "test_messages.proto",
    "pkg_test_messages.proto",
    "extended_messages.proto",
]

# Frame format profiles to test
PROFILES = [
    ("profile_standard", "ProfileStandard"),
    ("profile_sensor", "ProfileSensor"),
    ("profile_ipc", "ProfileIPC"),
    ("profile_bulk", "ProfileBulk"),
    ("profile_network", "ProfileNetwork"),
]

# Extended test profiles (only profiles that support pkg_id)
EXTENDED_PROFILES = [
    ("profile_bulk", "ProfileBulk"),
    ("profile_network", "ProfileNetwork"),
]

# Expected message counts
STANDARD_MESSAGE_COUNT = 17
EXTENDED_MESSAGE_COUNT = 17


# =============================================================================
# Language Definitions
# =============================================================================

@dataclass
class Language:
    """Language configuration."""
    id: str
    name: str
    gen_flag: str
    gen_output_dir: str
    
    # Compilation
    compiler: Optional[str] = None
    compiler_check: Optional[str] = None
    
    # Execution
    interpreter: Optional[str] = None
    
    # Directories
    test_dir: str = ""
    build_dir: str = ""
    script_dir: Optional[str] = None
    
    # File extensions
    source_ext: str = ""
    exe_ext: str = ""
    
    # Flags
    generation_only: bool = False
    file_prefix: Optional[str] = None
    
    def get_prefix(self) -> str:
        return self.file_prefix or self.name.lower()


# =============================================================================
# Timing Utilities
# =============================================================================

class TimedPhase:
    """Context manager for timing test phases."""
    
    def __init__(self, runner: 'TestRunner', phase_name: str):
        self.runner = runner
        self.phase_name = phase_name
        self.start_time: float = 0
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        self.runner.phase_times[self.phase_name] = elapsed
        return False


# =============================================================================
# Test Runner
# =============================================================================

class TestRunner:
    """Main test runner class."""
    
    def __init__(self, verbose: bool = False, quiet: bool = False):
        self.verbose = verbose
        self.quiet = quiet
        self.project_root = Path(__file__).parent.parent
        self.tests_dir = self.project_root / "tests"
        
        self.languages = self._init_languages()
        self.skipped_languages: List[str] = []
        
        # Tool availability cache (populated during check_tools)
        self._tool_cache: Optional[Dict[str, Dict[str, Any]]] = None
        
        # Timing tracking for phases
        self.phase_times: Dict[str, float] = {}
        
        # Failure details for summary
        self.failures: List[Dict[str, Any]] = []
        
        # Results tracking
        self.results = {
            "generation": {},
            "compilation": {},
            "standard_encode": {},
            "standard_validate": {},
            "standard_decode": {},
            "extended_encode": {},
            "extended_validate": {},
            "extended_decode": {},
            "variable_flag_encode": {},
            "variable_flag_validate": {},
            "variable_flag_decode": {},
        }
    
    def _init_languages(self) -> Dict[str, Language]:
        """Initialize language configurations."""
        return {
            "c": Language(
                id="c", name="C",
                gen_flag="--build_c",
                gen_output_dir="tests/generated/c",
                compiler="gcc",
                compiler_check="gcc --version",
                test_dir="tests/c",
                build_dir="tests/c/build",
                source_ext=".c",
                exe_ext=".exe",
            ),
            "cpp": Language(
                id="cpp", name="C++",
                gen_flag="--build_cpp",
                gen_output_dir="tests/generated/cpp",
                compiler="g++",
                compiler_check="g++ --version",
                test_dir="tests/cpp",
                build_dir="tests/cpp/build",
                source_ext=".cpp",
                exe_ext=".exe",
                file_prefix="cpp",
            ),
            "py": Language(
                id="py", name="Python",
                gen_flag="--build_py",
                gen_output_dir="tests/generated/py",
                interpreter="python",
                test_dir="tests/py",
                build_dir="tests/py/build",
                source_ext=".py",
            ),
            "ts": Language(
                id="ts", name="TypeScript",
                gen_flag="--build_ts",
                gen_output_dir="tests/generated/ts",
                compiler="npx tsc",
                compiler_check="npx tsc --version",
                interpreter="node",
                test_dir="tests/ts",
                build_dir="tests/ts/build",
                script_dir="tests/ts/build/ts",
                source_ext=".ts",
            ),
            "js": Language(
                id="js", name="JavaScript",
                gen_flag="--build_js",
                gen_output_dir="tests/generated/js",
                interpreter="node",
                test_dir="tests/js",
                build_dir="tests/js/build",
                source_ext=".js",
            ),
            "gql": Language(
                id="gql", name="GraphQL",
                gen_flag="--build_gql",
                gen_output_dir="tests/generated/gql",
                generation_only=True,
            ),
            "csharp": Language(
                id="csharp", name="C#",
                gen_flag="--build_csharp",
                gen_output_dir="tests/generated/csharp",
                compiler="dotnet",
                compiler_check="dotnet --version",
                interpreter="dotnet",
                test_dir="tests/csharp",
                build_dir="tests/csharp/bin/Release/net10.0",
                source_ext=".cs",
            ),
        }
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def timed_phase(self, phase_name: str) -> 'TimedPhase':
        """Create a context manager for timing a phase."""
        return TimedPhase(self, phase_name)
    
    def add_failure(self, phase: str, language: str, profile: Optional[str], 
                    reason: str, details: Optional[str] = None):
        """Record a test failure for summary."""
        self.failures.append({
            "phase": phase,
            "language": language,
            "profile": profile,
            "reason": reason,
            "details": details,
        })
    
    def run_cmd(self, cmd: str, cwd: Optional[Path] = None, 
                env: Optional[Dict[str, str]] = None, 
                timeout: int = 60) -> Tuple[bool, str, str]:
        """Run a shell command."""
        cmd_env = {**os.environ, **(env or {})}
        try:
            result = subprocess.run(
                cmd, shell=True, cwd=cwd or self.project_root,
                capture_output=True, text=True, timeout=timeout, env=cmd_env
            )
            if self.verbose:
                if result.stdout:
                    print(f"  STDOUT: {result.stdout}")
                if result.stderr:
                    print(f"  STDERR: {result.stderr}")
            elif not self.quiet and result.returncode != 0:
                if result.stderr:
                    print(f"  STDERR: {result.stderr}")
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Timeout"
        except Exception as e:
            return False, "", str(e)
    
    def print_section(self, title: str):
        """Print a section header."""
        print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")
    
    def get_active_languages(self) -> List[Language]:
        """Get languages that are enabled and not skipped."""
        return [lang for lang in self.languages.values() 
                if lang.id not in self.skipped_languages]
    
    def get_testable_languages(self) -> List[Language]:
        """Get languages that can run tests (not generation-only)."""
        return [lang for lang in self.get_active_languages() 
                if not lang.generation_only]
    
    # =========================================================================
    # Phase 1: Clean
    # =========================================================================
    
    def clean(self):
        """Clean all generated, copied, and built files."""
        print("[CLEAN] Deleting tests/generated folder...")
        gen_dir = self.tests_dir / "generated"
        if gen_dir.exists():
            shutil.rmtree(gen_dir)
        print("[CLEAN] Done.")
        
        # Clean TypeScript output
        ts_out = self.tests_dir / "ts" / "ts_out"
        if ts_out.exists():
            print("[CLEAN] Deleting tests/ts/ts_out folder...")
            shutil.rmtree(ts_out)
        
        # Clean build folders
        print("[CLEAN] Cleaning build folders...")
        cleaned = 0
        for lang in self.languages.values():
            if lang.build_dir:
                build_path = self.project_root / lang.build_dir
                if build_path.exists():
                    shutil.rmtree(build_path)
                    cleaned += 1
        
        # Clean any .bin files in test directories
        for lang in self.languages.values():
            if lang.test_dir:
                test_path = self.project_root / lang.test_dir
                for bin_file in test_path.glob("*.bin"):
                    bin_file.unlink()
                    cleaned += 1
            if lang.script_dir:
                script_path = self.project_root / lang.script_dir
                if script_path.exists():
                    for bin_file in script_path.glob("*.bin"):
                        bin_file.unlink()
                        cleaned += 1
        
        print(f"Cleaned {cleaned} items")
        print("[CLEAN] Done.")
    
    # =========================================================================
    # Phase 2: Tool Availability Check
    # =========================================================================
    
    def check_tools(self, use_cache: bool = True) -> Dict[str, Dict[str, Any]]:
        """Check tool availability for all languages.
        
        Args:
            use_cache: If True, return cached results if available.
        """
        # Return cached results if available
        if use_cache and self._tool_cache is not None:
            return self._tool_cache
        
        self.print_section("TOOL AVAILABILITY CHECK")
        
        results = {}
        for lang in self.languages.values():
            if lang.id in self.skipped_languages:
                continue
            
            info = {"name": lang.name, "available": True, "compiler": None, "interpreter": None}
            
            if lang.generation_only:
                info["generation_only"] = True
                results[lang.id] = info
                continue
            
            # Check compiler
            if lang.compiler:
                check_cmd = lang.compiler_check or f"{lang.compiler} --version"
                cwd = self.project_root / lang.test_dir if lang.test_dir else None
                success, stdout, stderr = self.run_cmd(check_cmd, cwd=cwd, timeout=10)
                version = (stdout or stderr).strip().split('\n')[0] if success else ""
                info["compiler"] = {"name": lang.compiler, "available": success, "version": version}
                if not success:
                    info["available"] = False
                    info["reason"] = f"Compiler '{lang.compiler}' not found"
            
            # Check interpreter
            if lang.interpreter and lang.interpreter != lang.compiler:
                success, stdout, stderr = self.run_cmd(f"{lang.interpreter} --version", timeout=10)
                version = (stdout or stderr).strip().split('\n')[0] if success else ""
                info["interpreter"] = {"name": lang.interpreter, "available": success, "version": version}
                if not success:
                    info["available"] = False
                    info["reason"] = f"Interpreter '{lang.interpreter}' not found"
            
            results[lang.id] = info
        
        # Print results
        for lang_id, info in results.items():
            status = Colors.ok_tag() if info["available"] else Colors.fail_tag()
            print(f"\n  {status} {info['name']}")
            
            if info.get("generation_only"):
                print("      (generation only)")
                continue
            
            if info.get("compiler"):
                c = info["compiler"]
                cs = Colors.ok_tag() if c["available"] else Colors.fail_tag()
                ver = f" ({c['version']})" if c["version"] else ""
                print(f"      Compiler:    {cs} {c['name']}{ver}")
            
            if info.get("interpreter"):
                i = info["interpreter"]
                ist = Colors.ok_tag() if i["available"] else Colors.fail_tag()
                ver = f" ({i['version']})" if i["version"] else ""
                print(f"      Interpreter: {ist} {i['name']}{ver}")
        
        print()
        
        # Cache the results
        self._tool_cache = results
        return results
    
    # =========================================================================
    # Phase 3: Code Generation
    # =========================================================================
    
    def generate_code(self) -> bool:
        """Generate code for all proto files."""
        self.print_section("CODE GENERATION")
        
        active = self.get_active_languages()
        lang_names = [l.name for l in active]
        print(f"  Generating code for {len(PROTO_FILES)} proto file(s) in languages: {', '.join(lang_names)}")
        
        all_success = True
        for proto_file in PROTO_FILES:
            proto_path = self.tests_dir / "proto" / proto_file
            if not proto_path.exists():
                print(f"  [WARN] Proto file not found: {proto_file}")
                continue
            
            print(f"  Processing: {proto_file}...")
            
            # Build command - always include --equality flag for test generation
            cmd_parts = [sys.executable, "-m", "struct_frame", str(proto_path), "--equality"]
            for lang in active:
                gen_dir = self.project_root / lang.gen_output_dir
                gen_dir.mkdir(parents=True, exist_ok=True)
                cmd_parts.extend([lang.gen_flag, "--" + lang.gen_flag.lstrip("-").replace("build_", "") + "_path", str(gen_dir)])
            
            # Add --sdk flag if C# is being generated (generates SDK interface)
            if any(l.id == "csharp" for l in active):
                cmd_parts.append("--sdk")
            
            env = {"PYTHONPATH": str(self.project_root / "src")}
            success, _, stderr = self.run_cmd(" ".join(cmd_parts), env=env)
            
            if success:
                for lang in active:
                    self.results["generation"][lang.id] = True
            else:
                print(f"  {Colors.fail_tag()} Code generation failed for {proto_file}")
                self.add_failure("generation", "all", None, f"Proto file: {proto_file}", stderr)
                all_success = False
        
        # Print results
        print()
        for lang in active:
            status = Colors.pass_text() if self.results["generation"].get(lang.id, False) else Colors.fail_text()
            print(f"  {lang.name:>10}: {status}")
        
        return all_success
    
    # =========================================================================
    # Phase 4: Compilation
    # =========================================================================
    
    def compile_all(self, parallel: bool = True) -> bool:
        """Compile code for all languages that need it.
        
        Args:
            parallel: If True, compile languages in parallel using ThreadPoolExecutor.
        """
        self.print_section("COMPILATION (all test files)")
        
        compilable = [l for l in self.get_active_languages() if l.compiler]
        if not compilable:
            print("  No languages require compilation")
            return True
        
        lang_names = [l.name for l in compilable]
        mode = "parallel" if parallel and len(compilable) > 1 else "sequential"
        print(f"  Compiling ({mode}): {', '.join(lang_names)}")
        
        all_success = True
        
        if parallel and len(compilable) > 1:
            # Parallel compilation
            with ThreadPoolExecutor(max_workers=len(compilable)) as executor:
                futures = {
                    executor.submit(self._compile_language, lang): lang 
                    for lang in compilable
                }
                for future in as_completed(futures):
                    lang = futures[future]
                    try:
                        success = future.result()
                        self.results["compilation"][lang.id] = success
                        status = Colors.pass_text() if success else Colors.fail_text()
                        print(f"  {lang.name:>10}: {status}")
                        if not success:
                            all_success = False
                            self.add_failure("compilation", lang.name, None, "Compilation failed")
                    except Exception as e:
                        self.results["compilation"][lang.id] = False
                        print(f"  {lang.name:>10}: {Colors.fail_text()} ({e})")
                        self.add_failure("compilation", lang.name, None, str(e))
                        all_success = False
        else:
            # Sequential compilation
            for lang in compilable:
                print(f"  Building {lang.name}...")
                success = self._compile_language(lang)
                self.results["compilation"][lang.id] = success
                if not success:
                    all_success = False
                    self.add_failure("compilation", lang.name, None, "Compilation failed")
            
            # Print results
            print()
            for lang in compilable:
                status = Colors.pass_text() if self.results["compilation"].get(lang.id, False) else Colors.fail_text()
                print(f"  {lang.name:>10}: {status}")
        
        return all_success
    
    def _compile_language(self, lang: Language) -> bool:
        """Compile a specific language."""
        test_dir = self.project_root / lang.test_dir
        build_dir = self.project_root / lang.build_dir
        gen_dir = self.project_root / lang.gen_output_dir
        
        build_dir.mkdir(parents=True, exist_ok=True)
        
        # C/C++: compile test_standard and test_extended executables
        if lang.id in ("c", "cpp"):
            success = True
            for runner in ["test_standard", "test_extended", "test_variable_flag"]:
                source = test_dir / f"{runner}{lang.source_ext}"
                if not source.exists():
                    continue
                output = build_dir / f"{runner}{lang.exe_ext}"
                
                if lang.id == "c":
                    cmd = f'gcc -I"{gen_dir}" -o "{output}" "{source}" -lm'
                else:
                    cmd = f'g++ -std=c++20 -I"{gen_dir}" -I"{test_dir}" -o "{output}" "{source}"'
                
                ok, _, _ = self.run_cmd(cmd)
                if not ok:
                    success = False
            return success
        
        # TypeScript: compile with tsc
        if lang.id == "ts":
            tsconfig = test_dir / "tsconfig.json"
            if tsconfig.exists():
                cmd = f'npx tsc --project "{tsconfig}"'
                success, _, _ = self.run_cmd(cmd, cwd=test_dir)
                return success
            return False
        
        # C#: build with dotnet
        if lang.id == "csharp":
            csproj = test_dir / "StructFrameTests.csproj"
            if csproj.exists():
                cmd = f'dotnet build "{csproj}" -c Release -o "{build_dir}" --verbosity quiet'
                success, _, _ = self.run_cmd(cmd)
                return success
            return False
        
        return True
    
    # =========================================================================
    # Phase 5 & 6: Test Execution
    # =========================================================================
    
    def run_tests(self, test_name: str, profiles: List[Tuple[str, str]], 
                  expected_count: int, runner_name: str) -> bool:
        """Run encode/decode tests for all profiles and languages."""
        self.print_section(f"{test_name.upper()} TESTS")
        
        testable = self.get_testable_languages()
        lang_names = [l.name for l in testable]
        print(f"  Testing {len(profiles)} profile(s) across {len(testable)} language(s): {', '.join(lang_names)}")
        print(f"  Expected messages per profile: {expected_count}")
        print(f"  Test runner: {runner_name}")
        
        encode_key = f"{test_name}_encode"
        validate_key = f"{test_name}_validate"
        decode_key = f"{test_name}_decode"
        
        # Initialize results structure: {profile: {lang: result}}
        encode_results = {p[1]: {} for p in profiles}
        validate_results = {p[1]: {} for p in profiles}
        decode_results = {p[1]: {} for p in profiles}
        
        # For decode, use C++ as the base language for encoded data
        base_lang = self.languages.get("cpp") or self.languages.get("c")
        cpp_lang = self.languages.get("cpp")
        
        col_width = 12
        
        # Helper to print matrix header
        def print_matrix_header(phase_name: str):
            print(f"\n  {Colors.bold(phase_name)}")
            print(f"  {'Profile':<18}" + "".join(l.name.center(col_width) for l in testable))
            print("  " + "-" * (18 + col_width * len(testable)))
        
        # Helper to colorize and center a cell
        def format_cell(success: bool, text: str) -> str:
            # Center the text first, then apply color
            centered = text.center(col_width)
            return Colors.green(centered) if success else Colors.red(centered)
        
        # =================================================================
        # PHASE 1: ENCODE
        # =================================================================
        print(f"\n  Phase 1: Encoding {len(profiles) * len(testable)} combinations...")
        encode_start = time.time()
        
        encode_tasks = [
            (profile_name, display_name, lang)
            for profile_name, display_name in profiles
            for lang in testable
        ]
        
        with ThreadPoolExecutor(max_workers=min(len(encode_tasks), 12)) as executor:
            encode_futures = {
                executor.submit(self._run_encode, lang, profile_name, runner_name): (display_name, lang)
                for profile_name, display_name, lang in encode_tasks
            }
            for future in as_completed(encode_futures):
                display_name, lang = encode_futures[future]
                try:
                    result = future.result()
                    encode_results[display_name][lang.name] = result
                    self.results[encode_key][f"{lang.id}_{display_name}"] = result["success"]
                    if not result["success"]:
                        self.add_failure(f"{test_name}_encode", lang.name, display_name, "Encode failed")
                except Exception as e:
                    encode_results[display_name][lang.name] = {"success": False, "error": str(e)}
                    self.results[encode_key][f"{lang.id}_{display_name}"] = False
                    self.add_failure(f"{test_name}_encode", lang.name, display_name, str(e))
        
        encode_time = time.time() - encode_start
        
        # Display Phase 1 results
        print_matrix_header(f"Phase 1: Encode ({encode_time:.2f}s)")
        for profile_name, display_name in profiles:
            row = f"  {display_name:<18}"
            for lang in testable:
                enc = encode_results[display_name][lang.name]
                cell = "OK" if enc["success"] else "FAIL"
                row += format_cell(enc["success"], cell)
            print(row)
        
        # =================================================================
        # PHASE 2: VALIDATE (binary compare + C++ decode)
        # =================================================================
        print(f"\n  Phase 2: Validating encoded files...")
        validate_start = time.time()
        
        validate_tasks = []
        for profile_name, display_name in profiles:
            cpp_file = self._get_output_file(cpp_lang, profile_name, runner_name)
            for lang in testable:
                if lang.id == "cpp":
                    validate_results[display_name][lang.name] = {
                        "success": True, "binary_match": True, "cpp_decode": True, "reason": "Reference"
                    }
                    self.results[validate_key][f"{lang.id}_{display_name}"] = True
                else:
                    lang_file = self._get_output_file(lang, profile_name, runner_name)
                    validate_tasks.append((profile_name, display_name, lang, lang_file, cpp_file))
        
        if validate_tasks:
            with ThreadPoolExecutor(max_workers=min(len(validate_tasks), 12)) as executor:
                validate_futures = {
                    executor.submit(
                        self._validate_encoded_file, 
                        lang_file, cpp_file, cpp_lang, profile_name, runner_name, expected_count
                    ): (display_name, lang)
                    for profile_name, display_name, lang, lang_file, cpp_file in validate_tasks
                }
                for future in as_completed(validate_futures):
                    display_name, lang = validate_futures[future]
                    try:
                        result = future.result()
                        validate_results[display_name][lang.name] = result
                        self.results[validate_key][f"{lang.id}_{display_name}"] = result["success"]
                        if not result["success"]:
                            reason = []
                            if not result.get("binary_match"):
                                reason.append("binary mismatch")
                            if not result.get("cpp_decode"):
                                reason.append("C++ decode failed")
                            self.add_failure(f"{test_name}_validate", lang.name, display_name, ", ".join(reason))
                    except Exception as e:
                        validate_results[display_name][lang.name] = {
                            "success": False, "binary_match": False, "cpp_decode": False, "error": str(e)
                        }
                        self.results[validate_key][f"{lang.id}_{display_name}"] = False
                        self.add_failure(f"{test_name}_validate", lang.name, display_name, str(e))
        
        validate_time = time.time() - validate_start
        
        # Display Phase 2 results
        print_matrix_header(f"Phase 2: Validate ({validate_time:.2f}s)")
        for profile_name, display_name in profiles:
            row = f"  {display_name:<18}"
            for lang in testable:
                val = validate_results[display_name][lang.name]
                if val["success"]:
                    cell = "OK"
                elif not val.get("binary_match"):
                    cell = "BIN"
                else:
                    cell = "VAL"
                row += format_cell(val["success"], cell)
            print(row)
        
        # =================================================================
        # PHASE 3: DECODE
        # =================================================================
        print(f"\n  Phase 3: Decoding {len(profiles) * len(testable)} combinations...")
        decode_start = time.time()
        
        decode_tasks = [
            (profile_name, display_name, lang)
            for profile_name, display_name in profiles
            for lang in testable
        ]
        
        with ThreadPoolExecutor(max_workers=min(len(decode_tasks), 12)) as executor:
            decode_futures = {
                executor.submit(self._run_decode, lang, profile_name, runner_name, base_lang, expected_count): (display_name, lang)
                for profile_name, display_name, lang in decode_tasks
            }
            for future in as_completed(decode_futures):
                display_name, lang = decode_futures[future]
                try:
                    result = future.result()
                    decode_results[display_name][lang.name] = result
                    self.results[decode_key][f"{lang.id}_{display_name}"] = result["success"]
                    if not result["success"]:
                        self.add_failure(f"{test_name}_decode", lang.name, display_name, 
                                        f"Decode failed (got {result.get('count', 0)}/{expected_count})")
                except Exception as e:
                    decode_results[display_name][lang.name] = {"success": False, "count": 0, "error": str(e)}
                    self.results[decode_key][f"{lang.id}_{display_name}"] = False
                    self.add_failure(f"{test_name}_decode", lang.name, display_name, str(e))
        
        decode_time = time.time() - decode_start
        
        # Display Phase 3 results
        print_matrix_header(f"Phase 3: Decode ({decode_time:.2f}s)")
        for profile_name, display_name in profiles:
            row = f"  {display_name:<18}"
            for lang in testable:
                dec = decode_results[display_name][lang.name]
                if dec["success"]:
                    cell = f"OK({dec['count']})"
                elif dec.get("count", 0) > 0:
                    cell = f"FAIL({dec['count']})"
                else:
                    cell = "FAIL"
                row += format_cell(dec["success"], cell)
            print(row)
        
        # =================================================================
        # SUMMARY
        # =================================================================
        total = 0
        passed = 0
        for display_name in [p[1] for p in profiles]:
            for lang in testable:
                if encode_results[display_name][lang.name]["success"]:
                    passed += 1
                total += 1
                if validate_results[display_name][lang.name]["success"]:
                    passed += 1
                total += 1
                if decode_results[display_name][lang.name]["success"]:
                    passed += 1
                total += 1
        
        success_str = Colors.green(f"{passed}/{total}") if passed == total else Colors.red(f"{passed}/{total}")
        print(f"\n  Legend: OK=pass, FAIL=fail, BIN=binary mismatch, VAL=C++ decode fail")
        print(f"  Total: {success_str} ({100*passed/total:.1f}%)\n")
        return passed == total
    
    def _run_encode(self, lang: Language, profile_name: str, runner_name: str) -> Dict[str, Any]:
        """Run encode test for a language/profile."""
        output_file = self._get_output_file(lang, profile_name, runner_name)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        success, stdout, _ = self._run_test_runner(lang, "encode", profile_name, output_file, runner_name)
        return {"success": success, "file": output_file if success else None, "stdout": stdout}
    
    def _validate_encoded_file(self, lang_file: Path, cpp_file: Path, 
                                cpp_lang: Language, profile_name: str, 
                                runner_name: str, expected_count: int) -> Dict[str, Any]:
        """Validate an encoded file by comparing to C++ reference and decoding with C++."""
        result = {"success": True, "binary_match": False, "cpp_decode": False}
        
        # Check if both files exist
        if not lang_file.exists():
            return {"success": False, "binary_match": False, "cpp_decode": False, "reason": "Lang file missing"}
        if not cpp_file.exists():
            return {"success": False, "binary_match": False, "cpp_decode": False, "reason": "C++ file missing"}
        
        # Binary comparison
        try:
            with open(lang_file, 'rb') as f1, open(cpp_file, 'rb') as f2:
                lang_data = f1.read()
                cpp_data = f2.read()
                result["binary_match"] = (lang_data == cpp_data)
        except Exception as e:
            result["binary_match"] = False
            result["reason"] = f"Binary compare error: {e}"
        
        # Run C++ decoder on the language's encoded file
        work_dir = self._get_test_work_dir(cpp_lang)
        runner = work_dir / f"{runner_name}{cpp_lang.exe_ext}"
        
        if runner.exists():
            cmd = f'"{runner}" decode {profile_name} "{lang_file}"'
            success, stdout, _ = self.run_cmd(cmd, cwd=work_dir)
            count = self._extract_message_count(stdout)
            result["cpp_decode"] = success and count >= expected_count
            result["cpp_decode_count"] = count
        else:
            result["cpp_decode"] = False
            result["reason"] = "C++ runner not found"
        
        # Overall success requires both binary match AND C++ decode success
        result["success"] = result["binary_match"] and result["cpp_decode"]
        return result
    
    def _run_decode(self, lang: Language, profile_name: str, runner_name: str, 
                    base_lang: Language, expected_count: int) -> Dict[str, Any]:
        """Run decode test for a language/profile using base language's encoded data."""
        # Get the encoded file from base language
        base_file = self._get_output_file(base_lang, profile_name, runner_name)
        if not base_file.exists():
            return {"success": False, "count": 0, "reason": "No encoded data"}
        
        # Get target directory
        target_dir = self._get_test_work_dir(lang)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / base_file.name
        
        # If same file (same language), just use it directly
        if base_file.resolve() == target_file.resolve():
            success, stdout, _ = self._run_test_runner(lang, "decode", profile_name, base_file, runner_name)
            count = self._extract_message_count(stdout)
            full_success = success and count >= expected_count
            return {"success": full_success, "count": count}
        
        # Otherwise copy and clean up
        try:
            shutil.copy2(base_file, target_file)
            success, stdout, _ = self._run_test_runner(lang, "decode", profile_name, target_file, runner_name)
            count = self._extract_message_count(stdout)
            
            # Success requires both runner success AND correct message count
            full_success = success and count >= expected_count
            return {"success": full_success, "count": count}
        finally:
            if target_file.exists() and base_file.resolve() != target_file.resolve():
                target_file.unlink()
    
    def _get_output_file(self, lang: Language, profile_name: str, runner_name: str) -> Path:
        """Get output file path for encoding."""
        prefix = lang.get_prefix()
        # Determine test type from runner name
        if "extended" in runner_name:
            test_type = "extended"
        elif "variable_flag" in runner_name or "variable" in runner_name:
            test_type = "variable_flag"
        else:
            test_type = "standard"
        filename = f"{prefix}_{profile_name}_{test_type}_data.bin"
        return self._get_test_work_dir(lang) / filename
    
    def _get_test_work_dir(self, lang: Language) -> Path:
        """Get the working directory for test execution."""
        if lang.script_dir:
            return self.project_root / lang.script_dir
        return self.project_root / lang.build_dir
    
    def _run_test_runner(self, lang: Language, mode: str, profile_name: str,
                         output_file: Path, runner_name: str) -> Tuple[bool, str, str]:
        """Run the test runner for a language."""
        work_dir = self._get_test_work_dir(lang)
        gen_dir = self.project_root / lang.gen_output_dir
        
        # C/C++: compiled executable
        if lang.exe_ext:
            runner = work_dir / f"{runner_name}{lang.exe_ext}"
            if not runner.exists():
                return False, "", "Runner not found"
            cmd = f'"{runner}" {mode} {profile_name} "{output_file}"'
            return self.run_cmd(cmd, cwd=work_dir)
        
        # C#: run compiled DLL directly (not dotnet run, which causes race conditions)
        if lang.id == "csharp":
            build_dir = self.project_root / lang.build_dir
            dll_path = build_dir / "StructFrameTests.dll"
            if not dll_path.exists():
                return False, "", "DLL not found - was compilation successful?"
            runner_arg = f"--runner {runner_name} " if runner_name != "test_standard" else ""
            cmd = f'dotnet "{dll_path}" {runner_arg}{mode} {profile_name} "{output_file}"'
            return self.run_cmd(cmd, cwd=build_dir)
        
        # TypeScript: compiled to JS
        if lang.script_dir:
            script = work_dir / f"{runner_name}.js"
            if not script.exists():
                return False, "", "Script not found"
            cmd = f'{lang.interpreter} "{script}" {mode} {profile_name} "{output_file}"'
            return self.run_cmd(cmd, cwd=work_dir)
        
        # Python/JavaScript: interpreted
        if lang.interpreter:
            test_dir = self.project_root / lang.test_dir
            script = test_dir / f"{runner_name}{lang.source_ext}"
            if not script.exists():
                return False, "", "Script not found"
            
            # Set up environment for Python
            env = {}
            if lang.id == "py":
                env["PYTHONPATH"] = f"{gen_dir}{os.pathsep}{gen_dir.parent}"
            
            cmd = f'{lang.interpreter} "{script}" {mode} {profile_name} "{output_file}"'
            return self.run_cmd(cmd, cwd=test_dir, env=env if env else None)
        
        return False, "", "Unknown language type"
    
    def _extract_message_count(self, stdout: str) -> int:
        """Extract message count from decoder output."""
        if not stdout:
            return 0
        # First try SUCCESS pattern (full success)
        match = re.search(r'SUCCESS:\s+(\d+)\s+messages?\s+validated', stdout)
        if match:
            return int(match.group(1))
        # Then try FAILED pattern (partial success)
        match = re.search(r'FAILED:\s+(\d+)\s+messages?\s+validated', stdout)
        if match:
            return int(match.group(1))
        return 0
    
    # =========================================================================
    # Phase 7: Standalone Tests
    # =========================================================================
    
    def verify_variable_truncation(self) -> bool:
        """Verify that variable messages are properly truncated by comparing binary file sizes."""
        print(f"\n  {Colors.bold('Verifying Variable Message Truncation...')}")
        
        # Collect all encoded variable_flag files
        encoded_files = {}
        for lang in self.get_testable_languages():
            # Use the same naming pattern as _get_output_file
            encode_file = self._get_output_file(lang, "profile_bulk", "test_variable_flag")
            if encode_file.exists():
                encoded_files[lang.id] = encode_file
        
        if not encoded_files:
            print(f"  {Colors.warn_tag()} No variable flag encoded files found to verify")
            return True
        
        # Read and verify binary content
        first_lang = None
        reference_data = None
        all_match = True
        
        for lang_id, file_path in encoded_files.items():
            with open(file_path, 'rb') as f:
                data = f.read()
            
            if first_lang is None:
                first_lang = lang_id
                reference_data = data
                print(f"  {Colors.blue('[INFO]')} Using {lang_id} as reference ({len(data)} bytes)")
            else:
                if data == reference_data:
                    print(f"  {Colors.ok_tag()} {lang_id}: Binary output matches reference ({len(data)} bytes)")
                else:
                    print(f"  {Colors.fail_tag()} {lang_id}: Binary output DIFFERS from reference")
                    print(f"      Expected {len(reference_data)} bytes, got {len(data)} bytes")
                    
                    # Find first difference
                    min_len = min(len(reference_data), len(data))
                    for i in range(min_len):
                        if reference_data[i] != data[i]:
                            print(f"      First difference at byte {i}: expected 0x{reference_data[i]:02x}, got 0x{data[i]:02x}")
                            break
                    
                    all_match = False
                    self.record_failure("variable_flag_verify", lang_id, "profile_bulk", 
                                      "Binary output does not match reference")
        
        # Verify truncation by checking frame sizes
        # The encoded file should contain 2 frames:
        # Frame 1: Non-variable message (should be full size with 200-byte array allocation)
        # Frame 2: Variable message (should be truncated to only 67 bytes used)
        if reference_data and all_match:
            print(f"\n  {Colors.bold('Analyzing frame sizes for truncation...')}")
            # This is a basic check - we expect the total size to be smaller than
            # if both messages were non-variable
            # Non-variable message size estimate: ~210 bytes (header + 4 + 200 + 2 + frame overhead)
            # Variable message size estimate: ~80 bytes (header + 4 + 67 + 2 + frame overhead)
            # Total should be roughly 290 bytes vs 420 bytes if both were non-variable
            
            total_size = len(reference_data)
            max_expected_if_no_truncation = 450  # Conservative upper bound if no truncation
            expected_with_truncation = 350  # Rough estimate with truncation
            
            if total_size < expected_with_truncation:
                print(f"  {Colors.ok_tag()} Truncation verified: Total size {total_size} bytes < {expected_with_truncation} bytes")
                print(f"      (Expected ~{max_expected_if_no_truncation} bytes if no truncation occurred)")
            else:
                print(f"  {Colors.warn_tag()} Truncation uncertain: Total size {total_size} bytes")
                print(f"      Expected < {expected_with_truncation} bytes with truncation")
        
        return all_match
    
    def run_standalone_tests(self) -> bool:
        """Run standalone Python test scripts."""
        test_scripts = list(self.tests_dir.glob("test_*.py"))
        if not test_scripts:
            return True
        
        print(f"\n  Running {len(test_scripts)} standalone Python test(s)...")
        
        all_success = True
        for script in test_scripts:
            success, stdout, stderr = self.run_cmd(f'python "{script}"', cwd=self.tests_dir, timeout=30)
            if stdout:
                print(stdout)
            if stderr and not success:
                print(stderr)
            if not success:
                all_success = False
        
        return all_success
    
    # =========================================================================
    # Summary
    # =========================================================================
    
    def print_summary(self) -> bool:
        """Print test summary and return success status."""
        self.print_section("TEST RESULTS SUMMARY")
        
        # Count results
        gen_total = len(self.results["generation"])
        gen_passed = sum(1 for v in self.results["generation"].values() if v)
        
        comp_total = len(self.results["compilation"])
        comp_passed = sum(1 for v in self.results["compilation"].values() if v)
        
        # Standard tests
        std_encode_total = len(self.results["standard_encode"])
        std_encode_passed = sum(1 for v in self.results["standard_encode"].values() if v)
        std_validate_total = len(self.results.get("standard_validate", {}))
        std_validate_passed = sum(1 for v in self.results.get("standard_validate", {}).values() if v)
        std_decode_total = len(self.results["standard_decode"])
        std_decode_passed = sum(1 for v in self.results["standard_decode"].values() if v)
        
        # Extended tests
        ext_encode_total = len(self.results["extended_encode"])
        ext_encode_passed = sum(1 for v in self.results["extended_encode"].values() if v)
        ext_validate_total = len(self.results.get("extended_validate", {}))
        ext_validate_passed = sum(1 for v in self.results.get("extended_validate", {}).values() if v)
        ext_decode_total = len(self.results["extended_decode"])
        ext_decode_passed = sum(1 for v in self.results["extended_decode"].values() if v)
        
        # Variable flag tests
        var_encode_total = len(self.results["variable_flag_encode"])
        var_encode_passed = sum(1 for v in self.results["variable_flag_encode"].values() if v)
        var_validate_total = len(self.results.get("variable_flag_validate", {}))
        var_validate_passed = sum(1 for v in self.results.get("variable_flag_validate", {}).values() if v)
        var_decode_total = len(self.results["variable_flag_decode"])
        var_decode_passed = sum(1 for v in self.results["variable_flag_decode"].values() if v)
        
        # Helper to colorize counts
        def colorize_count(passed: int, total: int) -> str:
            if total == 0:
                return "-"
            if passed == total:
                return Colors.green(f"{passed}/{total}")
            return Colors.red(f"{passed}/{total}")
        
        # Print breakdown
        print(f"\n  Code Generation:       {colorize_count(gen_passed, gen_total)}")
        print(f"  Compilation:           {colorize_count(comp_passed, comp_total)}")
        print(f"  Standard Encode:       {colorize_count(std_encode_passed, std_encode_total)}")
        print(f"  Standard Validate:     {colorize_count(std_validate_passed, std_validate_total)}")
        print(f"  Standard Decode:       {colorize_count(std_decode_passed, std_decode_total)}")
        print(f"  Extended Encode:       {colorize_count(ext_encode_passed, ext_encode_total)}")
        print(f"  Extended Validate:     {colorize_count(ext_validate_passed, ext_validate_total)}")
        print(f"  Extended Decode:       {colorize_count(ext_decode_passed, ext_decode_total)}")
        print(f"  Variable Flag Encode:  {colorize_count(var_encode_passed, var_encode_total)}")
        print(f"  Variable Flag Validate:{colorize_count(var_validate_passed, var_validate_total)}")
        print(f"  Variable Flag Decode:  {colorize_count(var_decode_passed, var_decode_total)}")
        
        total = (gen_total + comp_total + 
                 std_encode_total + std_validate_total + std_decode_total + 
                 ext_encode_total + ext_validate_total + ext_decode_total +
                 var_encode_total + var_validate_total + var_decode_total)
        passed = (gen_passed + comp_passed + 
                  std_encode_passed + std_validate_passed + std_decode_passed + 
                  ext_encode_passed + ext_validate_passed + ext_decode_passed +
                  var_encode_passed + var_validate_passed + var_decode_passed)
        
        print(f"\n  Total: {colorize_count(passed, total)} tests passed")
        
        # Print phase timings if available
        if self.phase_times:
            print(f"\n  {Colors.bold('Phase Timings:')}")
            for phase, elapsed in self.phase_times.items():
                print(f"    {phase:<20}: {elapsed:.2f}s")
        
        # Print failure summary if any
        if self.failures:
            print(f"\n  {Colors.bold(Colors.red('Failures:'))}")
            for failure in self.failures[:10]:  # Limit to 10 failures
                profile_str = f" [{failure['profile']}]" if failure['profile'] else ""
                print(f"    - {failure['phase']}: {failure['language']}{profile_str} - {failure['reason']}")
            if len(self.failures) > 10:
                print(f"    ... and {len(self.failures) - 10} more failures")
        
        if passed == total and total > 0:
            print(f"\n  {Colors.green(Colors.bold('SUCCESS: All tests passed'))}")
            return True
        else:
            print(f"\n  {Colors.red(Colors.bold(f'FAILURE: {total - passed} test(s) failed'))}")
            return False
    
    # =========================================================================
    # Main Entry Point
    # =========================================================================
    
    def run(self, generate_only: bool = False, check_tools_only: bool = False,
            compile_only: bool = False, skip_clean: bool = False,
            profile_filter: Optional[List[str]] = None,
            parallel_compile: bool = True) -> bool:
        """Run the complete test suite.
        
        Args:
            generate_only: Stop after code generation.
            check_tools_only: Only check tool availability.
            compile_only: Stop after compilation.
            skip_clean: Skip the clean phase.
            profile_filter: Only test specific profiles (e.g., ['ProfileStandard']).
            parallel_compile: Use parallel compilation (default True).
        """
        print(Colors.bold("Starting struct-frame Test Suite"))
        print(f"Project root: {self.project_root}")
        
        start_time = time.time()
        
        # Filter profiles if requested
        profiles_to_test = PROFILES
        extended_profiles_to_test = EXTENDED_PROFILES
        if profile_filter:
            profiles_to_test = [(p, d) for p, d in PROFILES if d in profile_filter]
            extended_profiles_to_test = [(p, d) for p, d in EXTENDED_PROFILES if d in profile_filter]
            if profiles_to_test or extended_profiles_to_test:
                print(f"Profile filter: {', '.join(profile_filter)}")
            else:
                print(f"{Colors.warn_tag()} No matching profiles found for filter: {profile_filter}")
        
        try:
            # Phase 1: Clean
            if not skip_clean:
                with self.timed_phase("Clean"):
                    self.clean()
            else:
                print(f"\n{Colors.yellow('[SKIP]')} Cleaning (--no-clean)")
            
            # Phase 2: Check tools
            with self.timed_phase("Tool Check"):
                tool_results = self.check_tools()
            available = [lid for lid, info in tool_results.items() if info["available"]]
            
            if check_tools_only:
                return all(info["available"] for info in tool_results.values())
            
            if not available:
                print(f"{Colors.fail_tag()} No languages have all required tools available")
                return False
            
            # Filter to available languages
            self.skipped_languages = [lid for lid in self.languages if lid not in available]
            
            testable = self.get_testable_languages()
            print(f"Testing languages: {', '.join(l.name for l in testable)}")
            
            # Phase 3: Generate code
            with self.timed_phase("Code Generation"):
                if not self.generate_code():
                    print(f"{Colors.fail_tag()} Code generation failed - aborting")
                    return False
            
            if generate_only:
                print(f"{Colors.ok_tag()} Code generation completed successfully")
                return True
            
            # Phase 4: Compile
            with self.timed_phase("Compilation"):
                self.compile_all(parallel=parallel_compile)
            
            if compile_only:
                success = all(self.results["compilation"].values())
                if success:
                    print(f"{Colors.ok_tag()} Compilation completed successfully")
                else:
                    print(f"{Colors.fail_tag()} Compilation failed")
                return success
            
            # Phase 5: Standard tests
            if profiles_to_test:
                with self.timed_phase("Standard Tests"):
                    self.run_tests("standard", profiles_to_test, STANDARD_MESSAGE_COUNT, "test_standard")
            
            # Phase 6: Extended tests
            if extended_profiles_to_test:
                with self.timed_phase("Extended Tests"):
                    self.run_tests("extended", extended_profiles_to_test, EXTENDED_MESSAGE_COUNT, "test_extended")

            # Phase 7: Variable-flag tests (only ProfileBulk, 2 messages)
            with self.timed_phase("Variable Flag Tests"):
                self.run_tests("variable_flag", [("profile_bulk", "ProfileBulk")], 2, "test_variable_flag")
                # Verify truncation by checking binary file sizes
                self.verify_variable_truncation()
            
            # Phase 8: Standalone tests
            with self.timed_phase("Standalone Tests"):
                self.run_standalone_tests()
            
            # Summary
            success = self.print_summary()
            
            print(f"\nTotal test time: {time.time() - start_time:.2f} seconds")
            return success
            
        except KeyboardInterrupt:
            print(f"\n{Colors.warn_tag()} Test run interrupted by user")
            return False
        except Exception as e:
            print(f"\n{Colors.fail_tag()} Test run failed: {e}")
            import traceback
            traceback.print_exc()
            return False


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Run struct-frame tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                      # Run all tests
  python run_tests.py --no-clean           # Skip cleaning (faster iteration)
  python run_tests.py --profile ProfileStandard  # Test only ProfileStandard
  python run_tests.py --only-compile       # Stop after compilation
  python run_tests.py --skip-lang ts       # Skip TypeScript tests
  python run_tests.py --no-color           # Disable colored output
"""
    )
    
    parser.add_argument("--verbose", "-v", action="store_true", 
                        help="Verbose output (show stdout/stderr)")
    parser.add_argument("--quiet", "-q", action="store_true", 
                        help="Suppress failure output")
    parser.add_argument("--skip-lang", action="append", dest="skip_languages", 
                        metavar="LANG", help="Skip a language (can be repeated). Note: 'cpp' cannot be skipped as it's the base encoder.")
    parser.add_argument("--only-generate", action="store_true", 
                        help="Only generate code, don't compile or test")
    parser.add_argument("--only-compile", action="store_true", 
                        help="Stop after compilation, don't run tests")
    parser.add_argument("--check-tools", action="store_true", 
                        help="Only check tool availability")
    parser.add_argument("--no-clean", action="store_true", 
                        help="Skip cleaning generated files (faster iteration)")
    parser.add_argument("--profile", action="append", dest="profiles", 
                        metavar="NAME", help="Only test specific profile(s)")
    parser.add_argument("--no-parallel", action="store_true", 
                        help="Disable parallel compilation")
    parser.add_argument("--no-color", action="store_true", 
                        help="Disable colored output")
    
    args = parser.parse_args()
    
    # Handle color settings
    if args.no_color:
        Colors.disable()
    
    # Validate skip_languages - 'cpp' cannot be skipped as it's the base encoder
    skip_languages = args.skip_languages or []
    if "cpp" in skip_languages:
        print(f"{Colors.warn_tag()} Cannot skip 'cpp' - it is required as the base encoder for decode tests")
        skip_languages = [lang for lang in skip_languages if lang != "cpp"]
    
    runner = TestRunner(verbose=args.verbose, quiet=args.quiet)
    if skip_languages:
        runner.skipped_languages = skip_languages
    
    success = runner.run(
        generate_only=args.only_generate,
        check_tools_only=args.check_tools,
        compile_only=args.only_compile,
        skip_clean=args.no_clean,
        profile_filter=args.profiles,
        parallel_compile=not args.no_parallel
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
