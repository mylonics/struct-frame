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
import io
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

# Ensure stdout uses UTF-8 on Windows (avoids UnicodeEncodeError for ✓/✗)
if hasattr(sys.stdout, 'buffer') and (sys.stdout.encoding or '').lower() not in ('utf-8', 'utf8'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


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
        except (AttributeError, OSError):
            Colors.disable()
    
    # Disable colors if not a TTY or NO_COLOR is set
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        Colors.disable()

_init_colors()


# =============================================================================
# Table rendering utility
# =============================================================================

def render_results_table(
    rows: Dict[str, Dict[str, Any]],
    languages: List[Any],
    row_label: str = "Test",
    col_width: int = 8,
) -> None:
    """Print a results table: rows = test/package names, columns = languages.

    Status values in the inner dict:
        True        -> green  "OK"
        False       -> red    "FAIL"
        "MISSING"   -> yellow "??"
        None        -> plain  "--"   (not applicable)

    Summary row counts only cells that actually ran (True or False), excluding
    None (N/A) and "MISSING" (ran but couldn't even start).
    """
    if not rows or not languages:
        return

    row_names = list(rows.keys())
    row_w = max(len(row_label), max(len(n) for n in row_names)) + 2

    lang_display = {
        "c": "C", "cpp": "C++", "py": "Py", "ts": "TS",
        "js": "JS", "csharp": "C#", "rust": "Rust",
    }

    def _cell(status: Any) -> str:
        if status is True:
            return Colors.green("OK".center(col_width))
        if status is False:
            return Colors.red("FAIL".center(col_width))
        if status == "MISSING":
            return Colors.yellow("??".center(col_width))
        return "--".center(col_width)

    header = f"  {row_label:<{row_w}}" + "".join(
        lang_display.get(l.id, l.id).center(col_width) for l in languages
    )
    sep = "  " + "-" * (row_w + col_width * len(languages))

    print(header)
    print(sep)
    for name in row_names:
        lang_results = rows[name]
        row = f"  {name:<{row_w}}" + "".join(
            _cell(lang_results.get(l.id)) for l in languages
        )
        print(row)

    # Summary row
    print(sep)
    summary = f"  {'Summary (pass/run)':<{row_w}}"
    for lang in languages:
        lang_results = rows
        total = sum(1 for n in row_names if rows[n].get(lang.id) in (True, False))
        passed = sum(1 for n in row_names if rows[n].get(lang.id) is True)
        if total == 0:
            summary += "--".center(col_width)
        elif passed == total:
            summary += Colors.green(f"{passed}/{total}".center(col_width))
        else:
            summary += Colors.red(f"{passed}/{total}".center(col_width))
    print(summary)
    print()


# =============================================================================
# Compiler env-var resolution (sanitizer / cross-compiler injection)
# =============================================================================

def _cc() -> str:
    """Return the C compiler from $CC, defaulting to gcc."""
    return os.environ.get("CC") or "gcc"


def _cxx() -> str:
    """Return the C++ compiler from $CXX, defaulting to g++."""
    return os.environ.get("CXX") or "g++"


def _cflags() -> str:
    """Extra C flags from $CFLAGS (space-separated; injected as-is)."""
    return os.environ.get("CFLAGS", "")


def _cxxflags() -> str:
    """Extra C++ flags from $CXXFLAGS (space-separated; injected as-is)."""
    return os.environ.get("CXXFLAGS", "")


def _ldflags() -> str:
    """Extra linker flags from $LDFLAGS (space-separated; injected as-is)."""
    return os.environ.get("LDFLAGS", "")


# =============================================================================
# Configuration
# =============================================================================

# Proto files to generate code from
PROTO_FILES = [
    "test_messages.sf",
    "pkg_test_messages.sf",
    "extended_messages.sf",
    "envelope_messages.sf",
    "wire_evolution_messages.sf",
    # Paired schema set for genuine cross-version extension interop: v1 (base
    # only) and v2 (base + extensions) are generated into separate namespaces so
    # each side is truly unaware of the other's extra fields.
    "wire_evolution_v1.sf",
    "wire_evolution_v2.sf",
]

# Frame format profiles to test
PROFILES = [
    ("standard", "ProfileStandard"),
    ("sensor", "ProfileSensor"),
    ("ipc", "ProfileIPC"),
    ("bulk", "ProfileBulk"),
    ("network", "ProfileNetwork"),
]

# Extended test profiles (only profiles that support pkg_id)
EXTENDED_PROFILES = [
    ("bulk", "ProfileBulk"),
    ("network", "ProfileNetwork"),
]

# Expected message counts
STANDARD_MESSAGE_COUNT = 17
EXTENDED_MESSAGE_COUNT = 10


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
    
    def __init__(self, verbose: bool = False, quiet: bool = False,
                 dotnet_framework: Optional[str] = None):
        self.verbose = verbose
        self.quiet = quiet
        self.project_root = Path(__file__).parent.parent
        self.tests_dir = self.project_root / "tests"
        self.dotnet_framework = self._resolve_dotnet_framework(dotnet_framework)
        
        self.languages = self._init_languages()
        self.skipped_languages: List[str] = []
        
        # Tool availability cache (populated during check_tools)
        self._tool_cache: Optional[Dict[str, Dict[str, Any]]] = None
        
        # Timing tracking for phases
        self.phase_times: Dict[str, float] = {}

        # Cached output DLLs for precompiled C# round-trip package runners.
        self._csharp_roundtrip_bins: Dict[str, Path] = {}
        self._csharp_roundtrip_compile_failures: set[str] = set()
        
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
            "variable_encode": {},
            "variable_validate": {},
            "variable_decode": {},
            "negative": {},
            "standalone": {},
        }

    def _resolve_dotnet_framework(self, explicit_framework: Optional[str]) -> str:
        """Resolve the C# framework used by the test runner."""
        tfm = (explicit_framework or os.environ.get("SF_DOTNET_TFM", "")).strip().lower()
        if tfm:
            return tfm
        ok, stdout, _ = self.run_cmd("dotnet --version", timeout=10)
        if ok and stdout:
            major = stdout.strip().split(".")[0]
            if major.isdigit():
                return f"net{major}.0"
        return "net8.0"
    
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
                build_dir=f"tests/csharp/bin/Release/{self.dotnet_framework}",
                source_ext=".cs",
            ),
            "rust": Language(
                id="rust", name="Rust",
                gen_flag="--build_rust",
                gen_output_dir="tests/generated/rust",
                compiler="cargo",
                compiler_check="cargo --version",
                test_dir="tests/rust",
                build_dir="tests/rust/target/debug",
                source_ext=".rs",
                exe_ext=".exe" if sys.platform == "win32" else "",
                file_prefix="rust",
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
        except (OSError, ValueError, subprocess.SubprocessError) as e:
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
            
            # Build command - always include --equality and --force flags for test generation
            # --force ensures regeneration even if hash matches (tests always need fresh generation)
            # --generate_tests emits per-package round-trip test code consumed by the
            # round-trip phase (see run_roundtrip_tests).
            # --sdk ensures the StructFrameSdk boilerplate (struct-frame-sdk/, etc.) is
            # copied alongside generated code so SDK tests can import it.
            cmd_parts = [sys.executable, "-m", "struct_frame", str(proto_path), "--equality", "--force", "--generate_tests", "--sdk"]
            for lang in active:
                gen_dir = self.project_root / lang.gen_output_dir
                gen_dir.mkdir(parents=True, exist_ok=True)
                cmd_parts.extend([lang.gen_flag, "--" + lang.gen_flag.lstrip("-").replace("build_", "") + "_path", str(gen_dir)])
            
            # Write the LSP catalog to the shared generated/ directory
            catalog_dir = self.project_root / "tests" / "generated"
            catalog_dir.mkdir(parents=True, exist_ok=True)
            cmd_parts.extend(["--catalog_path", str(catalog_dir)])

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
                    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as e:
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
            base_runners = ["test_standard", "test_extended", "test_variable_flag", 
                           "test_profiling", "test_profiling_generated", "test_negative",
                           "test_wire_evolution", "test_wire_evolution_interop"]
            sdk_runners = ["test_streaming"] if lang.id == "c" else ["test_sdk_units", "test_sdk_subscribe"]
            
            for runner in base_runners + sdk_runners:
                source = test_dir / f"{runner}{lang.source_ext}"
                if not source.exists():
                    continue
                output = build_dir / f"{runner}{lang.exe_ext}"
                
                if lang.id == "c":
                    cmd = f'{_cc()} {_cflags()} -I"{gen_dir}" -o "{output}" "{source}" {_ldflags()} -lm'
                else:
                    include_dir = test_dir / "include"
                    if runner == "test_sdk_subscribe":
                        # SDK subscribe test needs the C++ SDK boilerplate headers
                        sdk_dir = self.project_root / "src" / "struct_frame" / "boilerplate" / "cpp"
                        cmd = f'{_cxx()} -std=c++20 {_cxxflags()} -I"{gen_dir}" -I"{include_dir}" -I"{sdk_dir}" -o "{output}" "{source}" {_ldflags()}'
                    else:
                        cmd = f'{_cxx()} -std=c++20 {_cxxflags()} -I"{gen_dir}" -I"{include_dir}" -o "{output}" "{source}" {_ldflags()}'
                
                ok, _, _ = self.run_cmd(cmd)
                if not ok:
                    success = False
            return success
        
        # TypeScript: compile with tsc
        if lang.id == "ts":
            tsconfig = test_dir / "tsconfig.json"
            if tsconfig.exists():
                # Ensure local node_modules are installed so the project's own
                # TypeScript version (not a globally installed one) is used.
                pkg_json = test_dir / "package.json"
                node_modules = test_dir / "node_modules"
                if pkg_json.exists() and not node_modules.exists():
                    self.run_cmd("npm install --no-audit", cwd=test_dir, timeout=120)
                # Prefer the locally-installed tsc (respects the project's TS version)
                local_tsc = test_dir / "node_modules" / ".bin" / "tsc"
                tsc_cmd = f'"{local_tsc}"' if local_tsc.exists() else "npx tsc"
                cmd = f'{tsc_cmd} --project "{tsconfig}"'
                success, _, _ = self.run_cmd(cmd, cwd=test_dir)
                return success
            return False
        
        # C#: build with dotnet
        if lang.id == "csharp":
            csproj = test_dir / "StructFrameTests.csproj"
            if csproj.exists():
                cmd = (
                    f'dotnet build "{csproj}" -c Release --framework {self.dotnet_framework} '
                    f'-o "{build_dir}" --verbosity quiet'
                )
                success, _, _ = self.run_cmd(cmd)
                
                # Also verify transport implementations compile
                gen_csproj = gen_dir / "StructFrame.csproj"
                if gen_csproj.exists():
                    transport_build_dir = build_dir / "transport_verify"
                    transport_build_dir.mkdir(parents=True, exist_ok=True)
                    transport_cmd = (
                        f'dotnet build "{gen_csproj}" -c Release --framework {self.dotnet_framework} '
                        f'-o "{transport_build_dir}" -p:IncludeTransports=true --verbosity quiet'
                    )
                    transport_ok, _, _ = self.run_cmd(transport_cmd)
                    if not transport_ok:
                        print(f"  WARNING: Transport compilation verification failed (transport files may have errors)")
                        success = False
                
                return success
            return False
        
        # Rust: build with cargo
        if lang.id == "rust":
            test_dir = self.project_root / lang.test_dir
            if (test_dir / "Cargo.toml").exists():
                cmd = "cargo build"
                success, _, _ = self.run_cmd(cmd, cwd=test_dir)
                return success
            return False
        
        return True

    def precompile_csharp_roundtrip_tests(self) -> bool:
        """Precompile generated C# round-trip package launchers.

        This surfaces package-specific C# compile failures during the main
        compilation phase instead of waiting until round-trip execution.
        """
        cache_key = "csharp_roundtrip"
        self._csharp_roundtrip_bins = {}
        self._csharp_roundtrip_compile_failures = set()

        cs = self.languages.get("csharp")
        if not cs or "csharp" in self.skipped_languages:
            self.results["compilation"][cache_key] = True
            return True

        gen_dir = self.project_root / cs.gen_output_dir
        csproj = gen_dir / "StructFrame.csproj"
        sources = sorted(gen_dir.rglob("test_roundtrip_*.cs"))

        legacy_nested_build = gen_dir / "tests" / "build"
        if legacy_nested_build.exists():
            shutil.rmtree(legacy_nested_build, ignore_errors=True)

        if not csproj.exists() or not sources:
            self.results["compilation"][cache_key] = True
            return True

        print(f"  Precompiling C# round-trip ({len(sources)} packages)...")
        all_ok = True

        for src in sources:
            namespace = None
            class_name = None
            try:
                for line in src.read_text().splitlines():
                    ls = line.strip()
                    if ls.startswith("namespace ") and namespace is None:
                        namespace = ls[len("namespace "):].split("{")[0].strip()
                    elif ls.startswith("public static class ") and class_name is None:
                        class_name = ls[len("public static class "):].split()[0].split("{")[0].strip()
                    if namespace and class_name:
                        break
            except (OSError, UnicodeDecodeError):
                pass

            if not (namespace and class_name):
                print(f"    {Colors.fail_tag()} compile failed: {src.name} (could not parse namespace/class)")
                self.add_failure("compilation", "C#", None, f"compile {src.name}")
                self._csharp_roundtrip_compile_failures.add(src.stem)
                all_ok = False
                continue

            startup = f"{namespace}.{class_name}"
            out_dir = (self.project_root / "tests" / "build" / "csharp_roundtrip" / src.stem).resolve()
            if out_dir.exists():
                shutil.rmtree(out_dir, ignore_errors=True)
            out_dir.mkdir(parents=True, exist_ok=True)

            default_obj = gen_dir / "obj"
            if default_obj.exists():
                shutil.rmtree(default_obj, ignore_errors=True)

            build_cmd = (
                f'dotnet build "{csproj}" -c Release --framework {self.dotnet_framework} '
                f'-p:OutputType=Exe -p:StartupObject={startup} '
                f'-p:GenerateDocumentationFile=false '
                f'-o "{out_dir}" --verbosity quiet'
            )
            ok, _, stderr = self.run_cmd(build_cmd, timeout=180)
            if not ok:
                print(f"    {Colors.fail_tag()} compile failed: {src.name}")
                if stderr:
                    for line in stderr.splitlines():
                        print(f"      {line}")
                self.add_failure("compilation", "C#", None, f"compile {src.name}", stderr)
                self._csharp_roundtrip_compile_failures.add(src.stem)
                all_ok = False
                continue

            dll = out_dir / "StructFrame.dll"
            if not dll.exists():
                dlls = list(out_dir.glob("*.dll"))
                dll = dlls[0] if dlls else dll
            self._csharp_roundtrip_bins[src.stem] = dll

        self.results["compilation"][cache_key] = all_ok
        return all_ok
    
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
                except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as e:
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
                    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as e:
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
                except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as e:
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
        except OSError as e:
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
        elif "variable" in runner_name:
            test_type = "variable"
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
        if lang.exe_ext and lang.id not in ("csharp", "rust"):
            runner = work_dir / f"{runner_name}{lang.exe_ext}"
            if not runner.exists():
                return False, "", "Runner not found"
            cmd = f'"{runner}" {mode} {profile_name} "{output_file}"'
            return self.run_cmd(cmd, cwd=work_dir)
        
        # Rust: use cargo-built binary
        if lang.id == "rust":
            runner = self.project_root / lang.build_dir / f"struct_frame_rust_tests{lang.exe_ext}"
            if not runner.exists():
                return False, "", "Rust runner not found (cargo build needed)"
            cmd = f'"{runner}" {runner_name} {mode} {profile_name} "{output_file}"'
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
        
        # Collect all encoded variable files
        encoded_files = {}
        for lang in self.get_testable_languages():
            # Use the same naming pattern as _get_output_file
            encode_file = self._get_output_file(lang, "bulk", "test_variable_flag")
            if encode_file.exists():
                encoded_files[lang.id] = encode_file
        
        if not encoded_files:
            print(f"  {Colors.warn_tag()} No variable encoded files found to verify")
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
                    self.add_failure("variable_verify", lang_id, "bulk", 
                                      "Binary output does not match reference")
        
        # Verify truncation by checking frame sizes
        # The encoded file contains 7 frames (ProfileBulk, 8 bytes overhead each):
        #   Frame 1: TruncationTestNonVariable         — NOT truncated: 207 + 8 = 215 bytes
        #   Frame 2: TruncationTestVariable            — TRUNCATED:      74 + 8 =  82 bytes
        #   Frame 3: NestedVariableMessage             — TRUNCATED:      92 + 8 = 100 bytes
        #   Frame 4: VariableMultipleArrays            — TRUNCATED:      41 + 8 =  49 bytes
        #   Frame 5: VariableMixedFields               — TRUNCATED:      53 + 8 =  61 bytes
        #   Frame 6: VariableEnvelopeMessage           — fixed oneof:    10 + 8 =  18 bytes
        #   Frame 7: VariableEnvelopeMsgIdMessage      — fixed oneof:    ~N + 8 bytes
        # Total with truncation:  ~600 bytes (generous upper bound)
        # Total without truncation (frames 2-5): much larger
        if reference_data and all_match:
            print(f"\n  {Colors.bold('Analyzing frame sizes for truncation...')}")
            total_size = len(reference_data)
            max_expected_if_no_truncation = 2000  # Conservative upper bound
            expected_with_truncation = 1000       # Generous upper bound with truncation

            if total_size < expected_with_truncation:
                print(f"  {Colors.ok_tag()} Truncation verified: Total size {total_size} bytes < {expected_with_truncation} bytes")
                print(f"      (Expected ~{max_expected_if_no_truncation} bytes if no truncation occurred)")
            else:
                print(f"  {Colors.warn_tag()} Truncation uncertain: Total size {total_size} bytes")
                print(f"      Expected < {expected_with_truncation} bytes with truncation")
        
        return all_match
    
    def run_profiling_tests(self) -> bool:
        """Run all C++ profiling tests (barebones, generic, and generated)."""
        cpp_lang = self.languages.get("cpp")
        if not cpp_lang or "cpp" in self.skipped_languages:
            print("  [SKIP] C++ not available for profiling tests")
            return True
        
        build_dir = self.project_root / cpp_lang.build_dir
        all_success = True
        
        # List of profiling tests to run
        profiling_tests = [
            ("test_profiling", "Struct-Frame-Generic (hardcoded messages with struct-frame)"),
            ("test_profiling_generated", "Struct-Frame-Generated (all StandardMessages)")
        ]
        
        for exe_name, description in profiling_tests:
            exe_path = build_dir / f"{exe_name}{cpp_lang.exe_ext}"
            
            if not exe_path.exists():
                print(f"\n  [SKIP] {description}: executable not found")
                continue
            
            print(f"\n  Running {description}...")
            success, stdout, stderr = self.run_cmd(str(exe_path), timeout=120)
            
            if stdout:
                # Print the profiling output (it's nicely formatted)
                for line in stdout.strip().split('\n'):
                    print(f"  {line}")
            
            if stderr and not success:
                print(f"  {Colors.fail_tag()} Error: {stderr}")
            
            if not success:
                all_success = False
        
        return all_success
    
    def run_standalone_tests(self) -> bool:
        """Run the Python test suite via pytest."""
        print("\n  Running Python test suite with pytest ...")
        # Probe for pytest before launching the full suite so that a missing
        # installation produces a clear skip message rather than a cryptic
        # "No module named pytest" failure buried in stderr.
        probe_ok, _, probe_err = self.run_cmd(
            "python -m pytest --version", cwd=self.project_root, timeout=10
        )
        if not probe_ok:
            print("  SKIP: pytest not installed — run: pip install pytest")
            if probe_err:
                print(f"  ({probe_err.strip()})")
            return True  # not a test failure; treat as skipped
        success, stdout, stderr = self.run_cmd(
            f'python -m pytest "{self.tests_dir}" -q --tb=short',
            cwd=self.project_root,
            timeout=300,
        )
        if stdout:
            print(stdout)
        if stderr and not success:
            print(stderr)
        return success
    
    def run_negative_tests(self) -> bool:
        """Run negative tests (error handling tests) and display results in a matrix."""
        self.print_section("NEGATIVE TESTS")
        
        # Collect results from all languages
        test_results = {}  # {lang_id: {test_name: "PASS"/"FAIL"}}
        all_test_names = set()  # All unique test names across languages
        
        all_success = True
        for lang in self.get_testable_languages():
            test_name = f"{lang.name} negative tests"
            success = False
            stdout = ""
            stderr = ""
            
            if lang.id in ("c", "cpp"):
                # C/C++: run compiled executable
                build_dir = self.project_root / lang.build_dir
                test_exe = build_dir / f"test_negative{lang.exe_ext}"
                
                if not test_exe.exists():
                    continue
                
                success, stdout, stderr = self.run_cmd(str(test_exe), timeout=30)
                
            elif lang.id == "py":
                # Python: run test script directly
                test_script = self.project_root / lang.test_dir / "test_negative.py"
                
                if not test_script.exists():
                    continue
                
                success, stdout, stderr = self.run_cmd(f'python "{test_script}"', timeout=30)
                
            elif lang.id == "ts":
                # TypeScript: run compiled test
                test_script = self.project_root / lang.test_dir / "test_negative.ts"
                
                if not test_script.exists():
                    continue
                
                # TypeScript uses npx ts-node or node with compiled JS
                success, stdout, stderr = self.run_cmd(f'npx ts-node "{test_script}"', 
                                                       cwd=self.project_root / lang.test_dir, timeout=30)
                
            elif lang.id == "js":
                # JavaScript: run test script directly
                test_script = self.project_root / lang.test_dir / "test_negative.js"
                
                if not test_script.exists():
                    continue
                
                success, stdout, stderr = self.run_cmd(f'node "{test_script}"', timeout=30)
                
            elif lang.id == "csharp":
                # C#: compile and run (handled by test runner executable)
                build_dir = self.project_root / lang.build_dir
                # C# test runner handles routing to test_negative
                test_exe = build_dir / "StructFrameTests.exe"
                
                if not test_exe.exists():
                    test_exe = build_dir / "StructFrameTests.dll"
                    if not test_exe.exists():
                        continue
                    success, stdout, stderr = self.run_cmd(f'dotnet "{test_exe}" --runner test_negative', timeout=30)
                else:
                    success, stdout, stderr = self.run_cmd(f'"{test_exe}" --runner test_negative', timeout=30)
            
            elif lang.id == "rust":
                # Rust: run compiled test_negative binary
                build_dir = self.project_root / lang.build_dir
                test_exe = build_dir / f"test_negative{lang.exe_ext}"
                
                if not test_exe.exists():
                    continue
                
                success, stdout, stderr = self.run_cmd(str(test_exe), timeout=30)
            
            else:
                continue
            
            # Parse output to extract individual test results
            lang_tests = {}
            if stdout:
                # Parse the test results from the matrix output
                # Look for lines matching pattern: "Test name ... PASS/FAIL"
                for line in stdout.split('\n'):
                    # Match lines with test results (50 chars test name + result)
                    line = line.strip()
                    if line and not line.startswith('=') and not line.startswith('Test Name') and 'Summary:' not in line:
                        # Try to extract test name and result
                        if 'PASS' in line or 'FAIL' in line:
                            # Split on multiple spaces or find PASS/FAIL at end
                            parts = line.rsplit(maxsplit=1)
                            if len(parts) == 2:
                                test_nm, result = parts
                                test_nm = test_nm.strip()
                                result = result.strip()
                                if result in ('PASS', 'FAIL') and test_nm:
                                    lang_tests[test_nm] = result
                                    all_test_names.add(test_nm)
            
            test_results[lang.id] = lang_tests
            
            # Record result
            self.results["negative"][lang.id] = success
            
            if not success:
                all_success = False
                self.failures.append({
                    "phase": "Negative Tests",
                    "language": lang.name,
                    "profile": "",
                    "reason": "Error handling tests failed"
                })
        
        # Display cross-tabulation matrix
        if test_results and all_test_names:
            print("\nNegative Test Results (tests x languages):\n")
            
            # Get sorted language IDs and test names
            lang_ids = sorted([lang.id for lang in self.get_testable_languages() if lang.id in test_results])
            test_names = sorted(all_test_names)
            
            # Calculate column widths
            test_name_width = max(len(name) for name in test_names) + 2
            lang_col_width = 6  # Width for each language column
            
            # Print header
            header = f"{'Test Name':<{test_name_width}}"
            for lang_id in lang_ids:
                # Use short language names for columns
                lang_display = {"c": "C", "cpp": "C++", "py": "Py", "ts": "TS", "js": "JS", "csharp": "C#", "rust": "Rs"}
                lang_name = lang_display.get(lang_id, lang_id.upper()[:6])
                header += f" {lang_name:^{lang_col_width}}"
            print(header)
            
            # Print separator
            separator = "=" * test_name_width
            for _ in lang_ids:
                separator += " " + "=" * lang_col_width
            print(separator)
            
            # Print each test row
            for test_name in test_names:
                row = f"{test_name:<{test_name_width}}"
                for lang_id in lang_ids:
                    result = test_results.get(lang_id, {}).get(test_name, "-")
                    # Build padded cell: pad first, then apply color so ANSI
                    # codes don't break alignment
                    if result == "PASS":
                        cell = f"{'OK':^{lang_col_width}}"
                        row += " " + Colors.green(cell)
                    elif result == "FAIL":
                        cell = f"{'NO':^{lang_col_width}}"
                        row += " " + Colors.red(cell)
                    else:
                        row += f" {'--':^{lang_col_width}}"
                print(row)
            
            # Print summary row
            print()
            print("=" * (test_name_width + len(lang_ids) * (lang_col_width + 1)))
            summary_row = f"{'Summary (Pass/Total)':<{test_name_width}}"
            for lang_id in lang_ids:
                lang_tests = test_results.get(lang_id, {})
                total = len(lang_tests)
                passed = sum(1 for r in lang_tests.values() if r == "PASS")
                cell = f"{passed}/{total}"
                summary_row += f" {cell:^{lang_col_width}}"
            print(summary_row)
            print()
        
        return all_success

    def run_envelope_sdk_test(self) -> bool:
        """Run the envelope SDK interface test (field_order discriminator naming)."""
        self.print_section("ENVELOPE SDK TESTS")

        all_success = True
        testable = self.get_testable_languages()
        all_lang_ids = [l.id for l in testable]

        ENVELOPE_APPLICABILITY: Dict[str, List[str]] = {
            "test_envelope_sdk":  ["csharp", "rust"],
            "test_oneof_special": ["rust"],
        }

        table_data: Dict[str, Dict[str, Any]] = {
            test_name: {
                lid: ("MISSING" if lid in applicable else None)
                for lid in all_lang_ids
            }
            for test_name, applicable in ENVELOPE_APPLICABILITY.items()
        }
        env_results = self.results.setdefault("envelope_sdk", {})

        def _record(test_name: str, lang_id: str, success: bool,
                    stdout: str, stderr: str, failure_msg: str) -> None:
            table_data[test_name][lang_id] = success
            env_results[f"{lang_id}:{test_name}"] = success
            if not success:
                if stdout:
                    for line in stdout.splitlines():
                        print(f"  {line}")
                if stderr:
                    for line in stderr.splitlines():
                        print(f"  {line}")
                self.add_failure("envelope_sdk", lang_id, None, failure_msg)

        # ---- C# ----
        csharp = self.languages.get("csharp")
        if csharp and self.results["compilation"].get("csharp", False):
            build_dir = self.project_root / csharp.build_dir
            test_exe = build_dir / "StructFrameTests.exe"
            if not test_exe.exists():
                test_exe = build_dir / "StructFrameTests.dll"
                cmd = f'dotnet "{test_exe}" --runner test_envelope_sdk' if test_exe.exists() else None
            else:
                cmd = f'"{test_exe}" --runner test_envelope_sdk'

            if cmd:
                success, stdout, stderr = self.run_cmd(cmd, timeout=30)
                _record("test_envelope_sdk", "csharp", success, stdout, stderr,
                        "Envelope SDK test failed")
                if not success:
                    all_success = False

        # ---- Rust ----
        rust = self.languages.get("rust")
        if rust and self.results["compilation"].get("rust", False):
            rust_runner = self.project_root / rust.build_dir / f"struct_frame_rust_tests{rust.exe_ext}"
            if rust_runner.exists():
                success, stdout, stderr = self.run_cmd(f'"{rust_runner}" test_envelope_sdk', timeout=30)
                _record("test_envelope_sdk", "rust", success, stdout, stderr,
                        "Rust Envelope SDK test failed")
                if not success:
                    all_success = False

                success2, stdout2, stderr2 = self.run_cmd(f'"{rust_runner}" test_oneof_special', timeout=30)
                _record("test_oneof_special", "rust", success2, stdout2, stderr2,
                        "Rust oneof special test failed")
                if not success2:
                    all_success = False

        render_results_table(table_data, testable, row_label="Envelope Test")
        return all_success

    def run_sdk_tests(self) -> bool:
        """Run SDK unit and subscribe/dispatch tests (sections 6.1, 6.2, 6.3)."""
        self.print_section("SDK UNIT & SUBSCRIBE TESTS")

        all_success = True
        results = self.results.setdefault("sdk", {})
        testable = self.get_testable_languages()
        all_lang_ids = [l.id for l in testable]

        # Which lang_ids each test row applies to (others show N/A)
        SDK_APPLICABILITY: Dict[str, List[str]] = {
            "test_streaming":           ["c", "rust"],
            "test_sdk_units":           ["cpp"],
            "test_sdk_subscribe":           ["cpp", "csharp", "rust"],
            "test_sdk":                     ["py", "ts", "js"],
            "test_async_sdk":               ["py"],
            "test_sdk_strict_ordering":     ["csharp"],
            "test_sdk_lifecycle":           ["csharp"],
            "test_sdk_client_wrapper":      ["csharp"],
            "test_sdk_profiles":            ["csharp"],
            "test_base_transport":          ["csharp"],
            "test_request_response_sdk":    ["py", "ts"],
            "test_request_response_async":  ["py"],
            "test_sdk_request_response":    ["csharp"],
            "test_tcp_transport":           ["py"],
        }

        # Initialise table: None = N/A, "MISSING" = applicable but not yet run
        table_data: Dict[str, Dict[str, Any]] = {
            test_name: {
                lid: ("MISSING" if lid in applicable else None)
                for lid in all_lang_ids
            }
            for test_name, applicable in SDK_APPLICABILITY.items()
        }

        def _record(test_name: str, lang_id: str, success: bool,
                    stdout: str, stderr: str, phase_key: str, failure_msg: str) -> None:
            table_data[test_name][lang_id] = success
            results[phase_key] = success
            if not success:
                if stdout:
                    for line in stdout.splitlines():
                        print(f"  {line}")
                if stderr:
                    for line in stderr.splitlines():
                        print(f"  {line}")
                self.add_failure("sdk", lang_id, None, failure_msg)

        # ---- C: test_streaming (section 6.2 – push_byte positive cases) ----
        c_lang = self.languages.get("c")
        if c_lang and self.results["compilation"].get("c", False):
            build_dir = self.project_root / c_lang.build_dir
            exe = build_dir / f"test_streaming{c_lang.exe_ext}"
            if exe.exists():
                success, stdout, stderr = self.run_cmd(str(exe), timeout=30)
                _record("test_streaming", "c", success, stdout, stderr,
                        "c:streaming", "test_streaming failed")
                if not success:
                    all_success = False

        # ---- C++: test_sdk_units + test_sdk_subscribe (sections 6.1 + 6.2) ----
        cpp_lang = self.languages.get("cpp")
        if cpp_lang and self.results["compilation"].get("cpp", False):
            build_dir = self.project_root / cpp_lang.build_dir
            for runner, test_row in [
                ("test_sdk_units",     "test_sdk_units"),
                ("test_sdk_subscribe", "test_sdk_subscribe"),
            ]:
                exe = build_dir / f"{runner}{cpp_lang.exe_ext}"
                if exe.exists():
                    success, stdout, stderr = self.run_cmd(str(exe), timeout=30)
                    _record(test_row, "cpp", success, stdout, stderr,
                            f"cpp:{runner}", f"{runner} failed")
                    if not success:
                        all_success = False

        # ---- Python: test_sdk.py (section 6.3) ----
        py_lang = self.languages.get("py")
        if py_lang:
            script = self.project_root / py_lang.test_dir / "test_sdk.py"
            if script.exists():
                success, stdout, stderr = self.run_cmd(f'python "{script}"', timeout=30)
                _record("test_sdk", "py", success, stdout, stderr,
                        "py:sdk", "test_sdk.py failed")
                if not success:
                    all_success = False

        # ---- Python: test_async_sdk.py (section 6.3 – AsyncStructFrameSdk) ----
        if py_lang:
            script = self.project_root / py_lang.test_dir / "test_async_sdk.py"
            if script.exists():
                success, stdout, stderr = self.run_cmd(f'python "{script}"', timeout=30)
                _record("test_async_sdk", "py", success, stdout, stderr,
                        "py:async_sdk", "test_async_sdk.py failed")
                if not success:
                    all_success = False

        # ---- Python: test_request_response_sdk.py ----
        if py_lang:
            script = self.project_root / py_lang.test_dir / "test_request_response_sdk.py"
            if script.exists():
                success, stdout, stderr = self.run_cmd(f'python "{script}"', timeout=30)
                _record("test_request_response_sdk", "py", success, stdout, stderr,
                        "py:request_response_sdk", "test_request_response_sdk.py failed")
                if not success:
                    all_success = False

        # ---- Python: test_request_response_async_sdk.py ----
        if py_lang:
            script = self.project_root / py_lang.test_dir / "test_request_response_async_sdk.py"
            if script.exists():
                success, stdout, stderr = self.run_cmd(f'python "{script}"', timeout=30)
                _record("test_request_response_async", "py", success, stdout, stderr,
                        "py:request_response_async", "test_request_response_async_sdk.py failed")
                if not success:
                    all_success = False

        # ---- Python: test_tcp_transport.py (concrete TcpTransport over loopback) ----
        if py_lang:
            script = self.project_root / py_lang.test_dir / "test_tcp_transport.py"
            if script.exists():
                success, stdout, stderr = self.run_cmd(f'python "{script}"', timeout=30)
                _record("test_tcp_transport", "py", success, stdout, stderr,
                        "py:tcp_transport", "test_tcp_transport.py failed")
                if not success:
                    all_success = False

        # ---- TypeScript: test_sdk.ts (section 6.3) ----
        ts_lang = self.languages.get("ts")
        if ts_lang and self.results["compilation"].get("ts", False):
            ts_dir = self.project_root / ts_lang.test_dir
            script = ts_dir / "test_sdk.ts"
            if script.exists():
                success, stdout, stderr = self.run_cmd(
                    f'npx ts-node "{script}"', cwd=ts_dir, timeout=60
                )
                _record("test_sdk", "ts", success, stdout, stderr,
                        "ts:sdk", "test_sdk.ts failed")
                if not success:
                    all_success = False

        # ---- TypeScript: test_request_response_sdk.ts ----
        if ts_lang and self.results["compilation"].get("ts", False):
            ts_dir = self.project_root / ts_lang.test_dir
            script = ts_dir / "test_request_response_sdk.ts"
            if script.exists():
                success, stdout, stderr = self.run_cmd(
                    f'npx ts-node "{script}"', cwd=ts_dir, timeout=60
                )
                _record("test_request_response_sdk", "ts", success, stdout, stderr,
                        "ts:request_response_sdk", "test_request_response_sdk.ts failed")
                if not success:
                    all_success = False

        # ---- JavaScript: test_sdk.js (section 6.3) ----
        js_lang = self.languages.get("js")
        if js_lang and "js" not in self.skipped_languages:
            js_dir = self.project_root / js_lang.test_dir
            script = js_dir / "test_sdk.js"
            if script.exists():
                success, stdout, stderr = self.run_cmd(
                    f'node "{script}"', cwd=js_dir, timeout=30
                )
                _record("test_sdk", "js", success, stdout, stderr,
                        "js:sdk", "test_sdk.js failed")
                if not success:
                    all_success = False

        # ---- C#: SDK test suites (subscribe + Magnum-review additions) ----
        csharp_lang = self.languages.get("csharp")
        if csharp_lang and self.results["compilation"].get("csharp", False):
            build_dir = self.project_root / csharp_lang.build_dir
            test_exe = build_dir / "StructFrameTests.exe"
            if not test_exe.exists():
                test_exe = build_dir / "StructFrameTests.dll"
                cmd_prefix = f'dotnet "{test_exe}"'
            else:
                cmd_prefix = f'"{test_exe}"'

            if test_exe.exists():
                for runner_arg in [
                    "test_sdk_subscribe",
                    "test_sdk_strict_ordering",
                    "test_sdk_lifecycle",
                    "test_sdk_client_wrapper",
                    "test_sdk_profiles",
                    "test_base_transport",
                    "test_sdk_request_response",
                ]:
                    cmd = f'{cmd_prefix} --runner {runner_arg}'
                    success, stdout, stderr = self.run_cmd(cmd, timeout=60)
                    _record(runner_arg, "csharp", success, stdout, stderr,
                            f"csharp:{runner_arg}", f"{runner_arg} failed")
                    if not success:
                        all_success = False

        # ---- Rust: test_streaming + test_sdk_subscribe (sections 6.2, 6.3) ----
        rust_lang = self.languages.get("rust")
        if rust_lang and self.results["compilation"].get("rust", False):
            rust_runner = self.project_root / rust_lang.build_dir / f"struct_frame_rust_tests{rust_lang.exe_ext}"
            if rust_runner.exists():
                for runner_arg, test_row in [
                    ("test_streaming",    "test_streaming"),
                    ("test_sdk_subscribe","test_sdk_subscribe"),
                ]:
                    success, stdout, stderr = self.run_cmd(f'"{rust_runner}" {runner_arg}', timeout=30)
                    _record(test_row, "rust", success, stdout, stderr,
                            f"rust:{runner_arg}", f"{runner_arg} failed")
                    if not success:
                        all_success = False

        render_results_table(table_data, testable, row_label="SDK Test")
        return all_success

    def run_wire_evolution_tests(self) -> bool:
        """Run wire-evolution extension-field tests for C, C++, TypeScript, JavaScript, C#."""
        self.print_section("WIRE EVOLUTION TESTS")

        all_success = True
        results = self.results.setdefault("wire_evolution", {})
        testable = self.get_testable_languages()
        all_lang_ids = [l.id for l in testable]

        WIRE_APPLICABILITY: Dict[str, List[str]] = {
            # Base wire-evolution has no C runner by design (C is covered by the
            # interop suite + the top-level Python orchestrator); see tests/README.md.
            "test_wire_evolution":        ["cpp", "ts", "js", "csharp"],
            "test_wire_evolution_interop": ["c", "cpp", "ts", "js", "csharp", "rust"],
        }

        table_data: Dict[str, Dict[str, Any]] = {
            test_name: {
                lid: ("MISSING" if lid in applicable else None)
                for lid in all_lang_ids
            }
            for test_name, applicable in WIRE_APPLICABILITY.items()
        }

        def _record(test_name: str, lang_id: str, success: bool,
                    stdout: str, stderr: str, failure_msg: str) -> None:
            table_data[test_name][lang_id] = success
            results[f"{lang_id}:{test_name}"] = success
            if not success:
                if stdout:
                    for line in stdout.splitlines():
                        print(f"  {line}")
                if stderr:
                    for line in stderr.splitlines():
                        print(f"  {line}")
                self.add_failure("wire_evolution", lang_id, None, failure_msg)

        # ---- C ----
        c_lang = self.languages.get("c")
        if c_lang and "c" not in self.skipped_languages and self.results["compilation"].get("c", False):
            build_dir = self.project_root / c_lang.build_dir
            # C ships only the interop wire-evolution runner (no base test_wire_evolution.c).
            for test_name in ("test_wire_evolution_interop",):
                exe = build_dir / f"{test_name}{c_lang.exe_ext}"
                if exe.exists():
                    success, stdout, stderr = self.run_cmd(str(exe), timeout=30)
                    _record(test_name, "c", success, stdout, stderr, f"C {test_name} failed")
                    if not success:
                        all_success = False

        # ---- C++ ----
        cpp_lang = self.languages.get("cpp")
        if cpp_lang and "cpp" not in self.skipped_languages and self.results["compilation"].get("cpp", False):
            build_dir = self.project_root / cpp_lang.build_dir
            for test_name in ("test_wire_evolution", "test_wire_evolution_interop"):
                exe = build_dir / f"{test_name}{cpp_lang.exe_ext}"
                if exe.exists():
                    success, stdout, stderr = self.run_cmd(str(exe), timeout=30)
                    _record(test_name, "cpp", success, stdout, stderr, f"C++ {test_name} failed")
                    if not success:
                        all_success = False

        # ---- TypeScript ----
        ts_lang = self.languages.get("ts")
        if ts_lang and "ts" not in self.skipped_languages and self.results["compilation"].get("ts", False):
            ts_build = self.project_root / ts_lang.build_dir / "ts"
            for test_name in ("test_wire_evolution", "test_wire_evolution_interop"):
                js_out = ts_build / f"{test_name}.js"
                if js_out.exists():
                    success, stdout, stderr = self.run_cmd(f'node "{js_out}"', timeout=30)
                    _record(test_name, "ts", success, stdout, stderr, f"TypeScript {test_name} failed")
                    if not success:
                        all_success = False

        # ---- JavaScript ----
        js_lang = self.languages.get("js")
        if js_lang and "js" not in self.skipped_languages and self.results["compilation"].get("js", True):
            js_dir = self.project_root / js_lang.test_dir
            for test_name in ("test_wire_evolution", "test_wire_evolution_interop"):
                js_script = js_dir / f"{test_name}.js"
                if js_script.exists():
                    success, stdout, stderr = self.run_cmd(f'node "{js_script}"', timeout=30)
                    _record(test_name, "js", success, stdout, stderr, f"JavaScript {test_name} failed")
                    if not success:
                        all_success = False

        # ---- C# ----
        csharp_lang = self.languages.get("csharp")
        if csharp_lang and "csharp" not in self.skipped_languages and self.results["compilation"].get("csharp", False):
            build_dir = self.project_root / csharp_lang.build_dir
            test_exe = build_dir / "StructFrameTests.exe"
            if not test_exe.exists():
                test_exe = build_dir / "StructFrameTests.dll"
                cmd_prefix = f'dotnet "{test_exe}"'
            else:
                cmd_prefix = f'"{test_exe}"'
            if test_exe.exists():
                for test_name in ("test_wire_evolution", "test_wire_evolution_interop"):
                    cmd = f'{cmd_prefix} --runner {test_name}'
                    success, stdout, stderr = self.run_cmd(cmd, timeout=30)
                    _record(test_name, "csharp", success, stdout, stderr, f"C# {test_name} failed")
                    if not success:
                        all_success = False

        # ---- Rust (interop only) ----
        rust_lang = self.languages.get("rust")
        if rust_lang and "rust" not in self.skipped_languages and self.results["compilation"].get("rust", False):
            rust_runner = self.project_root / rust_lang.build_dir / f"struct_frame_rust_tests{rust_lang.exe_ext}"
            if rust_runner.exists():
                success, stdout, stderr = self.run_cmd(
                    f'"{rust_runner}" test_wire_evolution_interop', timeout=30
                )
                _record("test_wire_evolution_interop", "rust", success, stdout, stderr,
                        "Rust test_wire_evolution_interop failed")
                if not success:
                    all_success = False

        render_results_table(table_data, testable, row_label="Wire Evolution Test")
        return all_success

    def _run_wire_evolution_interop(self, results: dict) -> bool:
        """Deprecated stub — interop tests are now run inside run_wire_evolution_tests()."""
        return True

    def run_roundtrip_tests(self) -> bool:
        """Phase: round-trip tests for every message across all 5 frame profiles.

        For each ``.sf`` file the generator emits ``test_roundtrip_<pkg>``
        launchers (one per package) for every supported language
        (C, C++, Python, TypeScript, JavaScript, C#, Rust). Each launcher
        populates every message with deterministic dummy values, encodes them
        via the language's BufferWriter equivalent, decodes via the
        AccumulatingReader equivalent and compares field-by-field. This phase
        compiles (when needed) and executes those binaries.
        """
        self.print_section("ROUND-TRIP TESTS (all messages, all 5 profiles)")

        results = self.results.setdefault("roundtrip", {})
        all_success = True
        testable = self.get_testable_languages()
        all_lang_ids = [l.id for l in testable]

        # Accumulated table: {pkg_stem: {lang_id: True/False/None}}
        # Populated as each language finishes its tests.
        table_data: Dict[str, Dict[str, Any]] = {}

        def _rt_set(pkg_stem: str, lang_id: str, status: Any) -> None:
            if pkg_stem not in table_data:
                table_data[pkg_stem] = {lid: None for lid in all_lang_ids}
            table_data[pkg_stem][lang_id] = status
            results[f"{lang_id}:{pkg_stem}"] = status

        def _rt_run(lang_tag: str, lang_id: str, src_stem: str, run_fn: Callable) -> None:
            """Run one package's test, record result; print only on failure."""
            nonlocal all_success
            ok, stdout, stderr = run_fn()
            _rt_set(src_stem, lang_id, ok)
            if not ok:
                print(f"    {Colors.fail_tag()} {src_stem}")
                if stdout:
                    for line in stdout.splitlines():
                        print(f"      {line}")
                if stderr:
                    for line in stderr.splitlines():
                        print(f"      {line}")
                all_success = False

        # ---- C++ ----
        cpp = self.languages.get("cpp")
        if cpp and "cpp" not in self.skipped_languages and self.results["compilation"].get("cpp", False):
            gen_dir = self.project_root / cpp.gen_output_dir
            sources = sorted(gen_dir.glob("test_roundtrip_*.cpp"))
            if not sources:
                print("  [C++] No test_roundtrip_*.cpp files found - skipping")
            else:
                print(f"  Running C++ ({len(sources)} packages)...")
                build_dir = gen_dir / "roundtrip_bin"
                build_dir.mkdir(parents=True, exist_ok=True)
                for src in sources:
                    exe = build_dir / src.stem
                    compile_cmd = f'{_cxx()} -std=c++20 -O0 {_cxxflags()} -I"{gen_dir}" -o "{exe}" "{src}" {_ldflags()}'
                    ok, _, stderr = self.run_cmd(compile_cmd, timeout=120)
                    if not ok:
                        print(f"    {Colors.fail_tag()} compile failed: {src.name}")
                        if stderr:
                            for line in stderr.splitlines():
                                print(f"      {line}")
                        _rt_set(src.stem, "cpp", False)
                        self.add_failure("roundtrip", "C++", None, f"compile {src.name}", stderr)
                        all_success = False
                        continue
                    _rt_run("C++", "cpp", src.stem,
                            lambda e=exe: self.run_cmd(f'"{e}"', timeout=60))
                    if not results.get(f"cpp:{src.stem}"):
                        self.add_failure("roundtrip", "C++", None, f"run {src.name}")
        else:
            print("  [C++] Skipped (compilation failed or unavailable)")

        # ---- Python ----
        py = self.languages.get("py")
        if py and "py" not in self.skipped_languages:
            gen_dir = self.project_root / py.gen_output_dir
            sources = sorted(gen_dir.glob("test_roundtrip_*.py"))
            if not sources:
                print("  [Python] No test_roundtrip_*.py files found - skipping")
            else:
                print(f"  Running Python ({len(sources)} packages)...")
                env = {"PYTHONPATH": str(gen_dir)}
                for src in sources:
                    _rt_run("Python", "py", src.stem,
                            lambda s=src: self.run_cmd(f'{sys.executable} "{s}"', env=env, timeout=60))
                    if not results.get(f"py:{src.stem}"):
                        self.add_failure("roundtrip", "Python", None, f"run {src.name}")
        else:
            print("  [Python] Skipped")

        # ---- C ----
        c_lang = self.languages.get("c")
        if c_lang and "c" not in self.skipped_languages and self.results["compilation"].get("c", False):
            gen_dir = self.project_root / c_lang.gen_output_dir
            sources = sorted(gen_dir.glob("test_roundtrip_*.c"))
            if not sources:
                print("  [C] No test_roundtrip_*.c files found - skipping")
            else:
                print(f"  Running C ({len(sources)} packages)...")
                build_dir = gen_dir / "roundtrip_bin"
                build_dir.mkdir(parents=True, exist_ok=True)
                for src in sources:
                    exe = build_dir / src.stem
                    compile_cmd = f'{_cc()} -O0 {_cflags()} -I"{gen_dir}" -o "{exe}" "{src}" {_ldflags()} -lm'
                    ok, _, stderr = self.run_cmd(compile_cmd, timeout=120)
                    if not ok:
                        print(f"    {Colors.fail_tag()} compile failed: {src.name}")
                        if stderr:
                            for line in stderr.splitlines():
                                print(f"      {line}")
                        _rt_set(src.stem, "c", False)
                        self.add_failure("roundtrip", "C", None, f"compile {src.name}", stderr)
                        all_success = False
                        continue
                    _rt_run("C", "c", src.stem,
                            lambda e=exe: self.run_cmd(f'"{e}"', timeout=60))
                    if not results.get(f"c:{src.stem}"):
                        self.add_failure("roundtrip", "C", None, f"run {src.name}")
        else:
            print("  [C] Skipped (compilation failed or unavailable)")

        # ---- TypeScript ----
        ts = self.languages.get("ts")
        if ts and "ts" not in self.skipped_languages:
            gen_dir = self.project_root / ts.gen_output_dir
            sources = sorted(gen_dir.glob("test_roundtrip_*.ts"))
            if not sources:
                print("  [TS] No test_roundtrip_*.ts files found - skipping")
            else:
                build_dir = gen_dir / "roundtrip_bin"
                build_dir.mkdir(parents=True, exist_ok=True)
                ts_test_dir = self.project_root / ts.test_dir
                local_tsc = ts_test_dir / "node_modules" / ".bin" / "tsc"
                tsc_cmd = f'"{local_tsc}"' if local_tsc.exists() else "npx tsc"
                ts_inputs = ' '.join(f'"{p}"' for p in sorted(gen_dir.glob("*.ts")))
                compile_cmd = (
                    f'{tsc_cmd} --target es2020 --module commonjs --esModuleInterop '
                    f'--moduleResolution node --skipLibCheck --lib es2020,dom '
                    f'--types node --typeRoots "{ts_test_dir / "node_modules" / "@types"}" '
                    f'--outDir "{build_dir}" {ts_inputs}'
                )
                print(f"  Running TypeScript ({len(sources)} packages)...")
                compile_ok, _, compile_err = self.run_cmd(compile_cmd, cwd=ts_test_dir, timeout=180)
                if not compile_ok:
                    print(f"    {Colors.fail_tag()} compile failed")
                    if compile_err:
                        for line in compile_err.splitlines():
                            print(f"      {line}")
                    self.add_failure("roundtrip", "TypeScript", None, "tsc compile", compile_err)
                    for src in sources:
                        _rt_set(src.stem, "ts", False)
                    all_success = False
                else:
                    for src in sources:
                        js_file = build_dir / f"{src.stem}.js"
                        if not js_file.exists():
                            print(f"    {Colors.fail_tag()} {src.stem} (no js output)")
                            _rt_set(src.stem, "ts", False)
                            all_success = False
                            continue
                        _rt_run("TS", "ts", src.stem,
                                lambda j=js_file: self.run_cmd(f'node "{j}"', timeout=60))
                        if not results.get(f"ts:{src.stem}"):
                            self.add_failure("roundtrip", "TypeScript", None, f"run {src.name}")
        else:
            print("  [TS] Skipped")

        # ---- JavaScript ----
        js = self.languages.get("js")
        if js and "js" not in self.skipped_languages:
            gen_dir = self.project_root / js.gen_output_dir
            sources = sorted(gen_dir.glob("test_roundtrip_*.js"))
            if not sources:
                print("  [JS] No test_roundtrip_*.js files found - skipping")
            else:
                print(f"  Running JavaScript ({len(sources)} packages)...")
                for src in sources:
                    _rt_run("JS", "js", src.stem,
                            lambda s=src: self.run_cmd(f'node "{s}"', timeout=60))
                    if not results.get(f"js:{src.stem}"):
                        self.add_failure("roundtrip", "JavaScript", None, f"run {src.name}")
        else:
            print("  [JS] Skipped")

        # ---- C# ----
        cs = self.languages.get("csharp")
        if cs and "csharp" not in self.skipped_languages:
            gen_dir = self.project_root / cs.gen_output_dir
            sources = sorted(gen_dir.rglob("test_roundtrip_*.cs"))
            csproj = gen_dir / "StructFrame.csproj"
            legacy_nested_build = gen_dir / "tests" / "build"
            if legacy_nested_build.exists():
                shutil.rmtree(legacy_nested_build, ignore_errors=True)
            if not sources or not csproj.exists():
                print("  [C#] No test_roundtrip_*.cs files found - skipping")
            else:
                print(f"  Running C# ({len(sources)} packages)...")
                for src in sources:
                    if src.stem in self._csharp_roundtrip_compile_failures:
                        _rt_set(src.stem, "csharp", False)
                        all_success = False
                        continue

                    prebuilt_dll = self._csharp_roundtrip_bins.get(src.stem)
                    if prebuilt_dll and prebuilt_dll.exists():
                        _rt_run("C#", "csharp", src.stem,
                                lambda d=prebuilt_dll: self.run_cmd(f'dotnet "{d}"', timeout=60))
                        if not results.get(f"csharp:{src.stem}"):
                            self.add_failure("roundtrip", "C#", None, f"run {src.name}")
                        continue

                    namespace = None
                    class_name = None
                    try:
                        for line in src.read_text().splitlines():
                            ls = line.strip()
                            if ls.startswith("namespace ") and namespace is None:
                                namespace = ls[len("namespace "):].split("{")[0].strip()
                            elif ls.startswith("public static class ") and class_name is None:
                                class_name = ls[len("public static class "):].split()[0].split("{")[0].strip()
                            if namespace and class_name:
                                break
                    except (OSError, UnicodeDecodeError):
                        pass
                    if not (namespace and class_name):
                        print(f"    {Colors.fail_tag()} {src.stem} (could not parse namespace/class)")
                        _rt_set(src.stem, "csharp", False)
                        all_success = False
                        continue
                    startup = f"{namespace}.{class_name}"
                    out_dir = (self.project_root / "tests" / "build" / "csharp_roundtrip" / src.stem).resolve()
                    if out_dir.exists():
                        shutil.rmtree(out_dir, ignore_errors=True)
                    out_dir.mkdir(parents=True, exist_ok=True)
                    default_obj = gen_dir / "obj"
                    if default_obj.exists():
                        shutil.rmtree(default_obj, ignore_errors=True)
                    build_cmd = (
                        f'dotnet build "{csproj}" -c Release --framework {self.dotnet_framework} '
                        f'-p:OutputType=Exe -p:StartupObject={startup} '
                        f'-p:GenerateDocumentationFile=false '
                        f'-o "{out_dir}" --verbosity quiet'
                    )
                    ok, _, stderr = self.run_cmd(build_cmd, timeout=180)
                    if not ok:
                        print(f"    {Colors.fail_tag()} compile failed: {src.name}")
                        if stderr:
                            for line in stderr.splitlines():
                                print(f"      {line}")
                        _rt_set(src.stem, "csharp", False)
                        self.add_failure("roundtrip", "C#", None, f"compile {src.name}", stderr)
                        all_success = False
                        continue
                    dll = out_dir / "StructFrame.dll"
                    if not dll.exists():
                        dlls = list(out_dir.glob("*.dll"))
                        dll = dlls[0] if dlls else dll
                    _rt_run("C#", "csharp", src.stem,
                            lambda d=dll: self.run_cmd(f'dotnet "{d}"', timeout=60))
                    if not results.get(f"csharp:{src.stem}"):
                        self.add_failure("roundtrip", "C#", None, f"run {src.name}")
        else:
            print("  [C#] Skipped")

        # ---- Rust ----
        rust = self.languages.get("rust")
        if rust and "rust" not in self.skipped_languages:
            gen_dir = self.project_root / rust.gen_output_dir
            sources = sorted(gen_dir.glob("test_roundtrip_*.rs"))
            cargo_toml = gen_dir / "Cargo.toml"
            if not sources or not cargo_toml.exists():
                print("  [Rust] No test_roundtrip_*.rs files found - skipping")
            else:
                print(f"  Running Rust ({len(sources)} packages)...")
                for src in sources:
                    bin_name = src.stem
                    build_cmd = f'cargo build --release --bin {bin_name} --quiet'
                    ok, _, stderr = self.run_cmd(build_cmd, cwd=gen_dir, timeout=300)
                    if not ok:
                        print(f"    {Colors.fail_tag()} compile failed: {bin_name}")
                        if stderr:
                            for line in stderr.splitlines():
                                print(f"      {line}")
                        _rt_set(bin_name, "rust", False)
                        self.add_failure("roundtrip", "Rust", None, f"compile {src.name}", stderr)
                        all_success = False
                        continue
                    exe_ext = ".exe" if sys.platform == "win32" else ""
                    exe = gen_dir / "target" / "release" / f"{bin_name}{exe_ext}"
                    _rt_run("Rust", "rust", bin_name,
                            lambda e=exe: self.run_cmd(f'"{e}"', timeout=60))
                    if not results.get(f"rust:{bin_name}"):
                        self.add_failure("roundtrip", "Rust", None, f"run {src.name}")
        else:
            print("  [Rust] Skipped")

        if table_data:
            print()
            render_results_table(table_data, testable, row_label="Package")

        return all_success

    
    
    # =========================================================================
    # Summary
    # =========================================================================

    def _print_summary_matrices(self) -> None:
        """Print compact summary matrices at end-of-run."""

        lang_order = ["c", "cpp", "py", "ts", "js", "csharp", "rust"]
        lang_display = {"c": "C", "cpp": "C++", "py": "Py", "ts": "TS", "js": "JS", "csharp": "C#", "rust": "Rs"}

        # Detect which languages actually participated
        all_lang_ids = [lid for lid in lang_order if lid in self.results.get("compilation", {})]
        if not all_lang_ids:
            return

        col_w = 6
        ok_cell  = lambda: Colors.green("OK".center(col_w))
        fail_cell = lambda: Colors.red("FAIL".center(col_w))
        skip_cell = lambda: "-".center(col_w)

        def cell(success, present=True):
            if not present:
                return skip_cell()
            return ok_cell() if success else fail_cell()

        # ------------------------------------------------------------------
        # Matrix 1: Compilation × language
        # ------------------------------------------------------------------
        comp = self.results.get("compilation", {})
        if comp:
            header = f"  {'':22}" + "".join(lang_display.get(lid, lid).center(col_w) for lid in all_lang_ids)
            print(f"\n  {Colors.bold('Matrix 1: Compilation')}")
            print(header)
            row = f"  {'Compilation':<22}"
            for lid in all_lang_ids:
                row += cell(comp.get(lid, False), lid in comp)
            print(row)

        # ------------------------------------------------------------------
        # Matrix 2: Encode/Decode compatibility (test-phase × language)
        # Aggregates all standard+extended+variable phases for each language.
        # Cells show fraction of phases that passed (or OK / FAIL).
        # ------------------------------------------------------------------
        phase_keys = [
            ("standard_encode",  "Std Encode"),
            ("standard_validate","Std Validate"),
            ("standard_decode",  "Std Decode"),
            ("extended_encode",  "Ext Encode"),
            ("extended_validate","Ext Validate"),
            ("extended_decode",  "Ext Decode"),
        ]
        # Only include phases that have data
        active_phases = [(rk, label) for rk, label in phase_keys if self.results.get(rk)]
        if active_phases:
            header = f"  {'Phase':<22}" + "".join(lang_display.get(lid, lid).center(col_w) for lid in all_lang_ids)
            print(f"\n  {Colors.bold('Matrix 2: Encode/Decode phase summary (lang × phase)')}")
            print(header)
            for result_key, label in active_phases:
                phase_data = self.results[result_key]
                row = f"  {label:<22}"
                for lid in all_lang_ids:
                    # Key format is "{lang_id}_{ProfileName}" — aggregate all profiles for this lang
                    lang_entries = {k: v for k, v in phase_data.items() if k.startswith(lid + "_")}
                    if not lang_entries:
                        row += skip_cell()
                    elif all(lang_entries.values()):
                        row += ok_cell()
                    else:
                        passed_n = sum(1 for v in lang_entries.values() if v)
                        total_n  = len(lang_entries)
                        row += Colors.red(f"{passed_n}/{total_n}".center(col_w))
                print(row)

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
        
        # Variable tests
        var_encode_total = len(self.results["variable_encode"])
        var_encode_passed = sum(1 for v in self.results["variable_encode"].values() if v)
        var_validate_total = len(self.results.get("variable_validate", {}))
        var_validate_passed = sum(1 for v in self.results.get("variable_validate", {}).values() if v)
        var_decode_total = len(self.results["variable_decode"])
        var_decode_passed = sum(1 for v in self.results["variable_decode"].values() if v)
        
        # Negative tests
        neg_total = len(self.results.get("negative", {}))
        neg_passed = sum(1 for v in self.results.get("negative", {}).values() if v)

        # Round-trip tests (per-package, all 5 profiles)
        rt_total = len(self.results.get("roundtrip", {}))
        rt_passed = sum(1 for v in self.results.get("roundtrip", {}).values() if v)

        # Standalone pytest suite
        st_total = len(self.results.get("standalone", {}))
        st_passed = sum(1 for v in self.results.get("standalone", {}).values() if v)

        # Helper to colorize counts
        def colorize_count(passed: int, total: int) -> str:
            if total == 0:
                return "-"
            if passed == total:
                return Colors.green(f"{passed}/{total}")
            return Colors.red(f"{passed}/{total}")

        # Print breakdown
        label_w = 24
        def fmt(label: str, p: int, t: int) -> str:
            return f"  {(label + ':'):<{label_w}} {colorize_count(p, t)}"
        print()
        print(fmt('Code Generation',        gen_passed,          gen_total))
        print(fmt('Compilation',            comp_passed,         comp_total))
        print(fmt('Standard Encode',        std_encode_passed,   std_encode_total))
        print(fmt('Standard Validate',      std_validate_passed, std_validate_total))
        print(fmt('Standard Decode',        std_decode_passed,   std_decode_total))
        print(fmt('Extended Encode',        ext_encode_passed,   ext_encode_total))
        print(fmt('Extended Validate',      ext_validate_passed, ext_validate_total))
        print(fmt('Extended Decode',        ext_decode_passed,   ext_decode_total))
        print(fmt('Variable Flag Encode',   var_encode_passed,   var_encode_total))
        print(fmt('Variable Flag Validate', var_validate_passed, var_validate_total))
        print(fmt('Variable Flag Decode',   var_decode_passed,   var_decode_total))
        print(fmt('Negative Tests',         neg_passed,          neg_total))
        print(fmt('Round-trip Tests',       rt_passed,           rt_total))
        print(fmt('Standalone Tests',       st_passed,           st_total))

        total = (gen_total + comp_total +
                 std_encode_total + std_validate_total + std_decode_total +
                 ext_encode_total + ext_validate_total + ext_decode_total +
                 var_encode_total + var_validate_total + var_decode_total +
                 neg_total + rt_total + st_total)
        passed = (gen_passed + comp_passed +
                  std_encode_passed + std_validate_passed + std_decode_passed +
                  ext_encode_passed + ext_validate_passed + ext_decode_passed +
                  var_encode_passed + var_validate_passed + var_decode_passed +
                  neg_passed + rt_passed + st_passed)
        
        print(f"\n  Total: {colorize_count(passed, total)} tests passed")
        
        # Print phase timings if available
        if self.phase_times:
            print(f"\n  {Colors.bold('Phase Timings:')}")
            for phase, elapsed in self.phase_times.items():
                print(f"    {phase:<20}: {elapsed:.2f}s")
        
        # Print three summary matrices
        self._print_summary_matrices()
        
        # Print failure summary if any
        if self.failures:
            print(f"\n  {Colors.bold(Colors.red('Failures:'))}")
            for failure in self.failures:
                profile_str = f" [{failure['profile']}]" if failure['profile'] else ""
                print(f"    - {failure['phase']}: {failure['language']}{profile_str} - {failure['reason']}")
        
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
            parallel_compile: bool = True,
            profiling_only: bool = False,
            require_langs: Optional[List[str]] = None) -> bool:
        """Run the complete test suite.

        Args:
            generate_only: Stop after code generation.
            check_tools_only: Only check tool availability.
            compile_only: Stop after compilation.
            skip_clean: Skip the clean phase.
            profile_filter: Only test specific profiles (e.g., ['ProfileStandard']).
            parallel_compile: Use parallel compilation (default True).
            profiling_only: Only run profiling tests (skips standard/extended/variable tests).
            require_langs: Languages that MUST have their toolchain available; if
                any is missing the run fails instead of silently skipping it
                (use in CI to guarantee the full matrix actually executed).
        """
        print(Colors.bold("Starting struct-frame Test Suite"))
        print(f"Project root: {self.project_root}")
        print(f"C# target framework: {self.dotnet_framework}")
        
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

            # L5: in CI, guarantee the requested languages actually run instead of
            # being silently skipped because a toolchain is missing.
            if require_langs:
                missing = [lid for lid in require_langs if lid not in available]
                if missing:
                    print(f"{Colors.fail_tag()} Required languages missing toolchains "
                          f"(would be silently skipped): {', '.join(missing)}")
                    print("  Refusing to report success without them (--require-langs).")
                    return False

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
                if not profiling_only:
                    self.precompile_csharp_roundtrip_tests()
            
            if compile_only:
                success = all(self.results["compilation"].values())
                if success:
                    print(f"{Colors.ok_tag()} Compilation completed successfully")
                else:
                    print(f"{Colors.fail_tag()} Compilation failed")
                return success
            
            # Phase 5: Standard tests
            if not profiling_only and profiles_to_test:
                with self.timed_phase("Standard Tests"):
                    self.run_tests("standard", profiles_to_test, STANDARD_MESSAGE_COUNT, "test_standard")
            elif profiling_only:
                print(f"\n{Colors.yellow('[SKIP]')} Standard tests (--profiling)")
            
            # Phase 6: Extended tests
            if not profiling_only and extended_profiles_to_test:
                with self.timed_phase("Extended Tests"):
                    self.run_tests("extended", extended_profiles_to_test, EXTENDED_MESSAGE_COUNT, "test_extended")
            elif profiling_only:
                print(f"\n{Colors.yellow('[SKIP]')} Extended tests (--profiling)")

            # Phase 7: Variable tests (only ProfileBulk, 7 messages)
            if not profiling_only:
                with self.timed_phase("Variable Tests"):
                    self.run_tests("variable", [("bulk", "ProfileBulk")], 7, "test_variable_flag")
                    # Verify truncation by checking binary file sizes
                    self.verify_variable_truncation()
            else:
                print(f"\n{Colors.yellow('[SKIP]')} Variable tests (--profiling)")
            
            # Phase 8: Profiling tests (packed vs unpacked performance)
            with self.timed_phase("Profiling Tests"):
                self.run_profiling_tests()
            
            # Phase 9: Negative tests (error handling)
            if not profiling_only:
                with self.timed_phase("Negative Tests"):
                    self.run_negative_tests()
            else:
                print(f"\n{Colors.yellow('[SKIP]')} Negative tests (--profiling)")

            # Phase 10: Envelope SDK tests (C# field_order discriminator naming)
            if not profiling_only:
                with self.timed_phase("Envelope SDK Tests"):
                    self.run_envelope_sdk_test()
            else:
                print(f"\n{Colors.yellow('[SKIP]')} Envelope SDK tests (--profiling)")

            # Phase 10b: SDK unit & subscribe/dispatch tests (sections 6.1, 6.2, 6.3)
            if not profiling_only:
                with self.timed_phase("SDK Unit & Subscribe Tests"):
                    self.run_sdk_tests()
            else:
                print(f"\n{Colors.yellow('[SKIP]')} SDK unit & subscribe tests (--profiling)")

            # Phase 10c: Wire evolution tests
            if not profiling_only:
                with self.timed_phase("Wire Evolution Tests"):
                    self.run_wire_evolution_tests()
            else:
                print(f"\n{Colors.yellow('[SKIP]')} Wire evolution tests (--profiling)")
            
            # Phase 11: Standalone tests
            if not profiling_only:
                with self.timed_phase("Standalone Tests"):
                    pytest_ok = self.run_standalone_tests()
                    self.results["standalone"]["pytest"] = pytest_ok
                    if not pytest_ok:
                        self.failures.append({
                            "phase": "Standalone Tests",
                            "language": "Python",
                            "profile": "",
                            "reason": "pytest failed",
                        })
            else:
                print(f"\n{Colors.yellow('[SKIP]')} Standalone tests (--profiling)")

            # Phase 12: Round-trip tests (every message, all 5 profiles)
            if not profiling_only:
                with self.timed_phase("Round-trip Tests"):
                    self.run_roundtrip_tests()
            else:
                print(f"\n{Colors.yellow('[SKIP]')} Round-trip tests (--profiling)")
            
            # Summary
            success = self.print_summary()
            
            print(f"\nTotal test time: {time.time() - start_time:.2f} seconds")
            return success
            
        except KeyboardInterrupt:
            print(f"\n{Colors.warn_tag()} Test run interrupted by user")
            return False
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as e:
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
  python run_tests.py --profiling          # Run only profiling tests
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
    parser.add_argument("--profiling", action="store_true", 
                        help="Run only time profiling tests (skips standard/extended/variable tests)")
    parser.add_argument("--dotnet-framework", default=None,
                        help="C# target framework moniker (e.g., net8.0, net10.0). Overrides SF_DOTNET_TFM.")
    parser.add_argument("--require-langs", default=None, metavar="LANG[,LANG...]",
                        help="Comma-separated languages that MUST have toolchains available; "
                             "fail (rather than silently skip) if any is missing. Use in CI to "
                             "guarantee the full matrix ran, e.g. --require-langs c,cpp,py,ts,js,csharp,rust")

    args = parser.parse_args()
    
    # Handle color settings
    if args.no_color:
        Colors.disable()
    
    # Validate skip_languages - 'cpp' cannot be skipped as it's the base encoder
    skip_languages = args.skip_languages or []
    if "cpp" in skip_languages:
        print(f"{Colors.warn_tag()} Cannot skip 'cpp' - it is required as the base encoder for decode tests")
        skip_languages = [lang for lang in skip_languages if lang != "cpp"]
    
    runner = TestRunner(
        verbose=args.verbose,
        quiet=args.quiet,
        dotnet_framework=args.dotnet_framework,
    )
    if skip_languages:
        runner.skipped_languages = skip_languages
    
    require_langs = None
    if args.require_langs:
        require_langs = [l.strip() for l in args.require_langs.split(",") if l.strip()]

    success = runner.run(
        generate_only=args.only_generate,
        check_tools_only=args.check_tools,
        compile_only=args.only_compile,
        skip_clean=args.no_clean,
        profile_filter=args.profiles,
        parallel_compile=not args.no_parallel,
        profiling_only=args.profiling,
        require_langs=require_langs,
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
