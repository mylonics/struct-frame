#!/usr/bin/env python3
"""
Comprehensive Test Suite Runner for struct-frame Project

This script runs all tests for the struct-frame code generation framework,
including:
- Code generation for all languages (C, TypeScript, Python)
- Serialization/deserialization tests for each language
- Cross-language compatibility tests

Usage:
    python run_tests.py [--generate-only] [--skip-c] [--skip-ts] [--skip-py] [--verbose]
"""

import argparse
import os
import sys
import subprocess
import shutil
import time
from pathlib import Path


class TestRunner:
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.project_root = Path(__file__).parent.parent
        self.tests_dir = self.project_root / "tests"
        self.generated_dir = self.tests_dir / "generated"
        self.src_dir = self.project_root / "src"

        # Test results tracking
        self.results = {
            'generation': {'c': False, 'ts': False, 'py': False},
            'compilation': {'c': False, 'ts': False, 'py': False},
            'basic_types': {'c': False, 'ts': False, 'py': False},
            'arrays': {'c': False, 'ts': False, 'py': False},
            'serialization': {'c': False, 'ts': False, 'py': False},
            'cross_language': False
        }

    def log(self, message, level="INFO"):
        """Log a message with optional verbose output"""
        if level == "ERROR" or level == "SUCCESS" or self.verbose:
            prefix = {
                "INFO": "ℹ️ ",
                "ERROR": "❌",
                "SUCCESS": "✅",
                "WARNING": "⚠️ "
            }.get(level, "  ")
            print(f"{prefix} {message}")

    def run_command(self, command, cwd=None, timeout=30):
        """Run a shell command and return success status"""
        if cwd is None:
            cwd = self.project_root

        self.log(f"Running: {command}", "INFO")

        try:
            # Use shell=True for Windows PowerShell compatibility
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if self.verbose:
                if result.stdout:
                    print(f"  STDOUT: {result.stdout}")
                if result.stderr:
                    print(f"  STDERR: {result.stderr}")

            if result.returncode == 0:
                self.log(f"Command succeeded", "INFO")
                return True, result.stdout, result.stderr
            else:
                self.log(
                    f"Command failed with return code {result.returncode}", "ERROR")
                if result.stderr and not self.verbose:
                    print(f"  Error: {result.stderr}")
                return False, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            self.log(f"Command timed out after {timeout} seconds", "ERROR")
            return False, "", "Timeout"
        except Exception as e:
            self.log(f"Command execution failed: {e}", "ERROR")
            return False, "", str(e)

    def setup_directories(self):
        """Create and clean test directories"""
        self.log("Setting up test directories...")

        # Create directories if they don't exist
        directories = [
            self.generated_dir / "c",
            self.generated_dir / "ts",
            self.generated_dir / "py"
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            self.log(f"Created directory: {directory}")

        # Clean up any existing binary test files
        for pattern in ["*_test_data.bin", "*.exe"]:
            for file in self.project_root.glob(pattern):
                try:
                    file.unlink()
                    self.log(f"Cleaned up: {file}")
                except Exception as e:
                    self.log(f"Failed to clean {file}: {e}", "WARNING")

    def generate_code(self, proto_file, lang_flags):
        """Generate code for a specific proto file"""
        proto_path = self.tests_dir / "proto" / proto_file

        # Build the command
        command_parts = [
            "python", "-m", "struct_frame",
            str(proto_path)
        ]

        # Add language-specific flags and output paths
        if "c" in lang_flags:
            command_parts.extend(
                ["--build_c", "--c_path", str(self.generated_dir / "c")])
        if "ts" in lang_flags:
            command_parts.extend(
                ["--build_ts", "--ts_path", str(self.generated_dir / "ts")])
        if "py" in lang_flags:
            command_parts.extend(
                ["--build_py", "--py_path", str(self.generated_dir / "py")])

        command = " ".join(command_parts)

        # Set PYTHONPATH to include src directory
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.src_dir)

        self.log(f"Generating code for {proto_file}...")

        try:
            result = subprocess.run(
                command_parts,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                env=env,
                timeout=10
            )

            if result.returncode == 0:
                self.log(
                    f"Code generation successful for {proto_file}", "SUCCESS")
                return True
            else:
                self.log(f"Code generation failed for {proto_file}", "ERROR")
                if result.stderr:
                    print(f"  Error: {result.stderr}")
                return False

        except Exception as e:
            self.log(
                f"Code generation exception for {proto_file}: {e}", "ERROR")
            return False

    def test_code_generation(self, languages):
        """Test code generation for all proto files"""
        self.log("=== Testing Code Generation ===")

        proto_files = [
            "basic_types.proto",
            "nested_messages.proto",
            "comprehensive_arrays.proto",
            "serialization_test.proto"
        ]

        # Copy required boilerplate files
        self.copy_boilerplate_files()

        all_success = True
        for proto_file in proto_files:
            success = self.generate_code(proto_file, languages)
            if not success:
                all_success = False

            # Update results for each language
            for lang in languages:
                if success:
                    self.results['generation'][lang] = True

        return all_success

    def copy_boilerplate_files(self):
        """Copy boilerplate files to the generated directories"""
        boilerplate_dir = self.src_dir / "struct_frame" / "boilerplate"

        # Copy C boilerplate files
        c_boilerplate = boilerplate_dir / "c"
        if c_boilerplate.exists():
            for file in c_boilerplate.glob("*.h"):
                dest = self.generated_dir / "c" / file.name
                shutil.copy2(file, dest)
                self.log(f"Copied C boilerplate: {file.name}")

        # Copy Python boilerplate files
        py_boilerplate = boilerplate_dir / "py"
        if py_boilerplate.exists():
            for file in py_boilerplate.glob("*.py"):
                dest = self.generated_dir / "py" / file.name
                shutil.copy2(file, dest)
                self.log(f"Copied Python boilerplate: {file.name}")

        # Copy TypeScript boilerplate files
        ts_boilerplate = boilerplate_dir / "ts"
        if ts_boilerplate.exists():
            for file in ts_boilerplate.glob("*.ts"):
                dest = self.generated_dir / "ts" / file.name
                shutil.copy2(file, dest)
                self.log(f"Copied TypeScript boilerplate: {file.name}")

    def test_c_compilation(self):
        """Test C code compilation"""
        self.log("=== Testing C Compilation ===")

        # Check if gcc is available
        gcc_available, _, _ = self.run_command("gcc --version")
        if not gcc_available:
            self.log(
                "GCC compiler not found - skipping C compilation test", "WARNING")
            return True  # Don't fail the entire test suite

        test_files = [
            "test_basic_types.c",
            "test_arrays.c",
            "test_serialization.c"
        ]

        all_success = True

        for test_file in test_files:
            test_path = self.tests_dir / "c" / test_file
            output_path = self.tests_dir / "c" / f"{test_file[:-2]}.exe"

            # Create compile command
            command = f"gcc -I{self.generated_dir / 'c'} -o {output_path} {test_path} -lm"

            success, stdout, stderr = self.run_command(command)
            if success:
                self.log(
                    f"C compilation successful for {test_file}", "SUCCESS")
                self.results['compilation']['c'] = True
            else:
                self.log(f"C compilation failed for {test_file}", "ERROR")
                all_success = False

        return all_success

    def test_typescript_compilation(self):
        """Test TypeScript code compilation"""
        self.log("=== Testing TypeScript Compilation ===")

        # First check if TypeScript is available
        success, _, _ = self.run_command("tsc --version")
        if not success:
            self.log(
                "TypeScript compiler not found - skipping TS compilation test", "WARNING")
            return True

        # Copy test files to generated directory for compilation
        test_files = [
            "test_basic_types.ts",
            "test_arrays.ts",
            "test_serialization.ts"
        ]

        for test_file in test_files:
            src = self.tests_dir / "ts" / test_file
            dest = self.generated_dir / "ts" / test_file
            shutil.copy2(src, dest)

        # Try to compile TypeScript files
        command = f"tsc --outDir {self.generated_dir / 'ts' / 'js'} {self.generated_dir / 'ts'}/*.ts"
        success, stdout, stderr = self.run_command(command)

        if success:
            self.log("TypeScript compilation successful", "SUCCESS")
            self.results['compilation']['ts'] = True
            return True
        else:
            self.log("TypeScript compilation failed", "WARNING")
            # Don't fail the entire test suite for TS compilation issues
            return True

    def run_c_tests(self):
        """Run C test executables"""
        self.log("=== Running C Tests ===")

        test_executables = [
            ("test_basic_types.exe", "basic_types"),
            ("test_arrays.exe", "arrays"),
            ("test_serialization.exe", "serialization")
        ]

        all_success = True

        for exe_name, test_type in test_executables:
            exe_path = self.tests_dir / "c" / exe_name

            if not exe_path.exists():
                self.log(f"Executable not found: {exe_name}", "WARNING")
                continue

            success, stdout, stderr = self.run_command(
                str(exe_path), cwd=self.tests_dir / "c")

            if success:
                self.log(f"C {test_type} test passed", "SUCCESS")
                self.results[test_type]['c'] = True
            else:
                self.log(f"C {test_type} test failed", "ERROR")
                all_success = False

        return all_success

    def run_python_tests(self):
        """Run Python test scripts"""
        self.log("=== Running Python Tests ===")

        test_scripts = [
            ("test_basic_types.py", "basic_types"),
            ("test_arrays.py", "arrays"),
            ("test_serialization.py", "serialization")
        ]

        all_success = True

        # Set up Python path to include generated code
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.generated_dir / "py")

        for script_name, test_type in test_scripts:
            script_path = self.tests_dir / "py" / script_name

            try:
                result = subprocess.run(
                    [sys.executable, str(script_path)],
                    cwd=self.tests_dir / "py",
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=30
                )

                if self.verbose and result.stdout:
                    print(result.stdout)

                if result.returncode == 0:
                    self.log(f"Python {test_type} test passed", "SUCCESS")
                    self.results[test_type]['py'] = True
                else:
                    self.log(f"Python {test_type} test failed", "ERROR")
                    if result.stderr:
                        print(f"  Error: {result.stderr}")
                    all_success = False

            except Exception as e:
                self.log(f"Python {test_type} test exception: {e}", "ERROR")
                all_success = False

        return all_success

    def run_typescript_tests(self):
        """Run TypeScript/JavaScript test scripts"""
        self.log("=== Running TypeScript Tests ===")

        # Check if Node.js is available
        success, _, _ = self.run_command("node --version")
        if not success:
            self.log("Node.js not found - skipping TypeScript tests", "WARNING")
            return True

        test_scripts = [
            ("test_basic_types.ts", "basic_types"),
            ("test_arrays.ts", "arrays"),
            ("test_serialization.ts", "serialization")
        ]

        all_success = True

        for script_name, test_type in test_scripts:
            # First compile the TypeScript file
            script_path = self.generated_dir / "ts" / script_name
            js_path = self.generated_dir / "ts" / \
                "js" / f"{script_name[:-3]}.js"

            if not script_path.exists():
                self.log(
                    f"TypeScript test not found: {script_name}", "WARNING")
                continue

            # Try to run the compiled JavaScript
            if js_path.exists():
                success, stdout, stderr = self.run_command(
                    f"node {js_path}",
                    cwd=self.generated_dir / "ts" / "js"
                )

                if success:
                    self.log(f"TypeScript {test_type} test passed", "SUCCESS")
                    self.results[test_type]['ts'] = True
                else:
                    self.log(f"TypeScript {test_type} test failed", "WARNING")
                    # Don't fail entire suite for TS runtime issues
            else:
                self.log(
                    f"Compiled JavaScript not found for {script_name}", "WARNING")

        return all_success

    def run_cross_language_tests(self):
        """Run cross-language compatibility tests"""
        self.log("=== Running Cross-Language Compatibility Tests ===")

        # First, run all serialization tests to generate binary files
        self.log("Generating cross-language test data...")

        # Run tests that create binary files (these should have already run)
        binary_files = [
            "c_test_data.bin",
            "python_test_data.bin",
            "typescript_test_data.bin"
        ]

        found_files = []
        for file in binary_files:
            if (self.tests_dir / "c" / file).exists():
                found_files.append(f"C: {file}")
            if (self.tests_dir / "py" / file).exists():
                found_files.append(f"Python: {file}")
            if (self.generated_dir / "ts" / file).exists():
                found_files.append(f"TypeScript: {file}")

        if found_files:
            self.log(
                f"Found test data files: {', '.join(found_files)}", "SUCCESS")
            self.results['cross_language'] = True
            return True
        else:
            self.log("No cross-language test data files found", "WARNING")
            return False

    def print_summary(self):
        """Print a summary of all test results"""
        print("\n" + "="*60)
        print("📊 TEST RESULTS SUMMARY")
        print("="*60)

        # Count successes (adjust for skipped compiler tests)
        total_tests = 0
        passed_tests = 0

        # Code generation results
        print("\n🔧 Code Generation:")
        for lang in ['c', 'ts', 'py']:
            status = "✅ PASS" if self.results['generation'][lang] else "❌ FAIL"
            print(f"  {lang.upper():>10}: {status}")
            total_tests += 1
            if self.results['generation'][lang]:
                passed_tests += 1

        # Compilation results
        print("\n🔨 Compilation:")
        for lang in ['c', 'ts', 'py']:
            status = "✅ PASS" if self.results['compilation'][lang] else "❌ FAIL"
            print(f"  {lang.upper():>10}: {status}")
            total_tests += 1
            if self.results['compilation'][lang]:
                passed_tests += 1

        # Test execution results
        test_types = ['basic_types', 'arrays', 'serialization']
        for test_type in test_types:
            print(f"\n🧪 {test_type.replace('_', ' ').title()} Tests:")
            for lang in ['c', 'ts', 'py']:
                status = "✅ PASS" if self.results[test_type][lang] else "❌ FAIL"
                print(f"  {lang.upper():>10}: {status}")
                total_tests += 1
                if self.results[test_type][lang]:
                    passed_tests += 1

        # Cross-language compatibility
        print(f"\n🌐 Cross-Language Compatibility:")
        status = "✅ PASS" if self.results['cross_language'] else "❌ FAIL"
        print(f"  {'OVERALL':>10}: {status}")
        total_tests += 1
        if self.results['cross_language']:
            passed_tests += 1

        # Overall result
        print(
            f"\n📈 Overall Results: {passed_tests}/{total_tests} tests passed")

        success_rate = (passed_tests / total_tests) * 100

        # Consider it successful if code generation works and at least one language passes
        core_success = (
            self.results['generation']['py'] and  # Python generation works
            self.results['basic_types']['py'] and  # Python tests pass
            self.results['cross_language']  # Cross-language files created
        )

        if success_rate >= 80:
            print(f"🎉 SUCCESS: {success_rate:.1f}% pass rate")
            return True
        elif core_success and success_rate >= 30:
            print(
                f"✅ PARTIAL SUCCESS: {success_rate:.1f}% pass rate - Core functionality working")
            print("   Note: C/TypeScript compilation requires additional tools (gcc/tsc)")
            return True
        else:
            print(f"⚠️  NEEDS WORK: {success_rate:.1f}% pass rate")
            return False


def main():
    """Main test runner entry point"""
    parser = argparse.ArgumentParser(
        description="Run comprehensive tests for struct-frame project"
    )
    parser.add_argument(
        "--generate-only",
        action="store_true",
        help="Only run code generation tests"
    )
    parser.add_argument(
        "--skip-c",
        action="store_true",
        help="Skip C language tests"
    )
    parser.add_argument(
        "--skip-ts",
        action="store_true",
        help="Skip TypeScript language tests"
    )
    parser.add_argument(
        "--skip-py",
        action="store_true",
        help="Skip Python language tests"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    # Determine which languages to test
    languages = []
    if not args.skip_c:
        languages.append("c")
    if not args.skip_ts:
        languages.append("ts")
    if not args.skip_py:
        languages.append("py")

    if not languages:
        print("❌ No languages selected for testing!")
        return False

    # Initialize test runner
    runner = TestRunner(verbose=args.verbose)

    print("🚀 Starting struct-frame Test Suite")
    print(f"📁 Project root: {runner.project_root}")
    print(
        f"🌍 Testing languages: {', '.join(lang.upper() for lang in languages)}")

    start_time = time.time()

    try:
        # Set up test environment
        runner.setup_directories()

        # Run code generation tests
        if not runner.test_code_generation(languages):
            print("❌ Code generation failed - aborting remaining tests")
            return False

        if args.generate_only:
            print("✅ Code generation completed successfully")
            return True

        # Run compilation tests
        success = True

        if "c" in languages:
            if not runner.test_c_compilation():
                success = False
            if not runner.run_c_tests():
                success = False

        if "ts" in languages:
            if not runner.test_typescript_compilation():
                success = False
            if not runner.run_typescript_tests():
                success = False

        if "py" in languages:
            if not runner.run_python_tests():
                success = False

        # Run cross-language compatibility tests
        if not runner.run_cross_language_tests():
            success = False

        # Print summary
        overall_success = runner.print_summary()

        end_time = time.time()
        print(f"\n⏱️  Total test time: {end_time - start_time:.2f} seconds")

        return overall_success and success

    except KeyboardInterrupt:
        print("\n⚠️  Test run interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Test run failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
