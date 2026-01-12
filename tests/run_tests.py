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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


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
STANDARD_MESSAGE_COUNT = 11
EXTENDED_MESSAGE_COUNT = 12


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
        
        # Results tracking
        self.results = {
            "generation": {},
            "compilation": {},
            "standard_encode": {},
            "standard_decode": {},
            "extended_encode": {},
            "extended_decode": {},
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
    
    def check_tools(self) -> Dict[str, Dict[str, Any]]:
        """Check tool availability for all languages."""
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
            status = "[OK]" if info["available"] else "[FAIL]"
            print(f"\n  {status} {info['name']}")
            
            if info.get("generation_only"):
                print("      (generation only)")
                continue
            
            if info.get("compiler"):
                c = info["compiler"]
                cs = "[OK]" if c["available"] else "[FAIL]"
                ver = f" ({c['version']})" if c["version"] else ""
                print(f"      Compiler:    {cs} {c['name']}{ver}")
            
            if info.get("interpreter"):
                i = info["interpreter"]
                ist = "[OK]" if i["available"] else "[FAIL]"
                ver = f" ({i['version']})" if i["version"] else ""
                print(f"      Interpreter: {ist} {i['name']}{ver}")
        
        print()
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
            
            # Build command
            cmd_parts = [sys.executable, "-m", "struct_frame", str(proto_path)]
            for lang in active:
                gen_dir = self.project_root / lang.gen_output_dir
                gen_dir.mkdir(parents=True, exist_ok=True)
                cmd_parts.extend([lang.gen_flag, "--" + lang.gen_flag.lstrip("-").replace("build_", "") + "_path", str(gen_dir)])
            
            env = {"PYTHONPATH": str(self.project_root / "src")}
            success, _, _ = self.run_cmd(" ".join(cmd_parts), env=env)
            
            if success:
                for lang in active:
                    self.results["generation"][lang.id] = True
            else:
                print(f"  [ERROR] Code generation failed for {proto_file}")
                all_success = False
        
        # Print results
        print()
        for lang in active:
            status = "PASS" if self.results["generation"].get(lang.id, False) else "FAIL"
            print(f"  {lang.name:>10}: {status}")
        
        return all_success
    
    # =========================================================================
    # Phase 4: Compilation
    # =========================================================================
    
    def compile_all(self) -> bool:
        """Compile code for all languages that need it."""
        self.print_section("COMPILATION (all test files)")
        
        compilable = [l for l in self.get_active_languages() if l.compiler]
        if not compilable:
            print("  No languages require compilation")
            return True
        
        lang_names = [l.name for l in compilable]
        print(f"  Compiling: {', '.join(lang_names)}")
        
        all_success = True
        for lang in compilable:
            print(f"  Building {lang.name}...")
            success = self._compile_language(lang)
            self.results["compilation"][lang.id] = success
            if not success:
                all_success = False
        
        # Print results
        print()
        for lang in compilable:
            status = "PASS" if self.results["compilation"].get(lang.id, False) else "FAIL"
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
            for runner in ["test_standard", "test_extended"]:
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
        decode_key = f"{test_name}_decode"
        
        # Initialize results structure: {profile: {lang: result}}
        encode_results = {p[1]: {} for p in profiles}
        decode_results = {p[1]: {} for p in profiles}
        
        # For decode, use C++ as the base language for encoded data
        base_lang = self.languages.get("cpp") or self.languages.get("c")
        
        # Print matrix header
        col_width = 12
        print(f"\n{'Profile':<20}" + "".join(l.name.center(col_width) for l in testable))
        print("-" * (20 + col_width * len(testable)))
        
        # Run tests profile-by-profile, showing results as we go
        for profile_name, display_name in profiles:
            row = f"{display_name:<20}"
            
            # Run encode for all languages for this profile
            for lang in testable:
                result = self._run_encode(lang, profile_name, runner_name)
                encode_results[display_name][lang.name] = result
                self.results[encode_key][f"{lang.id}_{display_name}"] = result["success"]
            
            # Run decode for all languages for this profile
            for lang in testable:
                result = self._run_decode(lang, profile_name, runner_name, base_lang, expected_count)
                decode_results[display_name][lang.name] = result
                self.results[decode_key][f"{lang.id}_{display_name}"] = result["success"]
            
            # Print row with encode/decode results combined
            for lang in testable:
                enc = encode_results[display_name][lang.name]
                dec = decode_results[display_name][lang.name]
                
                if enc["success"] and dec["success"]:
                    cell = f"OK({dec['count']})"
                elif enc["success"] and not dec["success"]:
                    if dec.get("count", 0) > 0:
                        cell = f"DEC({dec['count']})"
                    else:
                        cell = "DEC"
                elif not enc["success"]:
                    cell = "ENC"
                else:
                    cell = "FAIL"
                row += cell.center(col_width)
            
            print(row)
        
        # Calculate success rate
        total = 0
        passed = 0
        for display_name in [p[1] for p in profiles]:
            for lang in testable:
                # Encode
                if encode_results[display_name][lang.name]["success"]:
                    passed += 1
                total += 1
                # Decode
                if decode_results[display_name][lang.name]["success"]:
                    passed += 1
                total += 1
        
        print(f"\nLegend: OK(N)=encode+decode pass, ENC=encode fail, DEC=decode fail")
        print(f"Success rate: {passed}/{total} ({100*passed/total:.1f}%)\n")
        return passed == total
    
    def _run_encode(self, lang: Language, profile_name: str, runner_name: str) -> Dict[str, Any]:
        """Run encode test for a language/profile."""
        output_file = self._get_output_file(lang, profile_name, runner_name)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        success, stdout, _ = self._run_test_runner(lang, "encode", profile_name, output_file, runner_name)
        return {"success": success, "file": output_file if success else None}
    
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
        test_type = "extended" if "extended" in runner_name else "standard"
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
        
        # C#: dotnet run
        if lang.id == "csharp":
            test_dir = self.project_root / lang.test_dir
            csproj = test_dir / "StructFrameTests.csproj"
            runner_arg = f"--runner {runner_name}" if runner_name != "test_standard" else ""
            cmd = f'dotnet run --project "{csproj}" --verbosity quiet -- {mode} {profile_name} "{output_file}" {runner_arg}'
            return self.run_cmd(cmd, cwd=test_dir)
        
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
        match = re.search(r'SUCCESS:\s+(\d+)\s+messages?\s+validated', stdout)
        return int(match.group(1)) if match else 0
    
    # =========================================================================
    # Phase 7: Standalone Tests
    # =========================================================================
    
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
        std_decode_total = len(self.results["standard_decode"])
        std_decode_passed = sum(1 for v in self.results["standard_decode"].values() if v)
        
        # Extended tests
        ext_encode_total = len(self.results["extended_encode"])
        ext_encode_passed = sum(1 for v in self.results["extended_encode"].values() if v)
        ext_decode_total = len(self.results["extended_decode"])
        ext_decode_passed = sum(1 for v in self.results["extended_decode"].values() if v)
        
        # Print breakdown
        print(f"\n  Code Generation:    {gen_passed}/{gen_total}")
        print(f"  Compilation:        {comp_passed}/{comp_total}")
        print(f"  Standard Encode:    {std_encode_passed}/{std_encode_total}")
        print(f"  Standard Decode:    {std_decode_passed}/{std_decode_total}")
        print(f"  Extended Encode:    {ext_encode_passed}/{ext_encode_total}")
        print(f"  Extended Decode:    {ext_decode_passed}/{ext_decode_total}")
        
        total = gen_total + comp_total + std_encode_total + std_decode_total + ext_encode_total + ext_decode_total
        passed = gen_passed + comp_passed + std_encode_passed + std_decode_passed + ext_encode_passed + ext_decode_passed
        
        print(f"\n  Total: {passed}/{total} tests passed")
        
        if passed == total and total > 0:
            print("  SUCCESS: All tests passed")
            return True
        else:
            print(f"  FAILURE: {total - passed} test(s) failed")
            return False
    
    # =========================================================================
    # Main Entry Point
    # =========================================================================
    
    def run(self, generate_only: bool = False, check_tools_only: bool = False) -> bool:
        """Run the complete test suite."""
        print("Starting struct-frame Test Suite")
        print(f"Project root: {self.project_root}")
        
        start_time = time.time()
        
        try:
            # Phase 1: Clean
            self.clean()
            
            # Phase 2: Check tools
            tool_results = self.check_tools()
            available = [lid for lid, info in tool_results.items() if info["available"]]
            
            if check_tools_only:
                return all(info["available"] for info in tool_results.values())
            
            if not available:
                print("[ERROR] No languages have all required tools available")
                return False
            
            # Filter to available languages
            self.skipped_languages = [lid for lid in self.languages if lid not in available]
            
            testable = self.get_testable_languages()
            print(f"Testing languages: {', '.join(l.name for l in testable)}")
            
            # Phase 3: Generate code
            if not self.generate_code():
                print("[ERROR] Code generation failed - aborting")
                return False
            
            if generate_only:
                print("[OK] Code generation completed successfully")
                return True
            
            # Phase 4: Compile
            self.compile_all()
            
            # Phase 5: Standard tests
            self.run_tests("standard", PROFILES, STANDARD_MESSAGE_COUNT, "test_standard")
            
            # Phase 6: Extended tests
            self.run_tests("extended", EXTENDED_PROFILES, EXTENDED_MESSAGE_COUNT, "test_extended")
            
            # Phase 7: Standalone tests
            self.run_standalone_tests()
            
            # Summary
            success = self.print_summary()
            
            print(f"\nTotal test time: {time.time() - start_time:.2f} seconds")
            return success
            
        except KeyboardInterrupt:
            print("\n[WARN] Test run interrupted by user")
            return False
        except Exception as e:
            print(f"\n[ERROR] Test run failed: {e}")
            import traceback
            traceback.print_exc()
            return False


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Run struct-frame tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress failure output")
    parser.add_argument("--skip-lang", action="append", dest="skip_languages", 
                        help="Skip a language (can be repeated)")
    parser.add_argument("--only-generate", action="store_true", help="Only generate code")
    parser.add_argument("--check-tools", action="store_true", help="Only check tool availability")
    
    args = parser.parse_args()
    
    runner = TestRunner(verbose=args.verbose, quiet=args.quiet)
    if args.skip_languages:
        runner.skipped_languages = args.skip_languages
    
    success = runner.run(
        generate_only=args.only_generate,
        check_tools_only=args.check_tools
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
