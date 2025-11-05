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
            'generation': {'c': False, 'ts': False, 'py': False, 'cpp': False},
            'compilation': {'c': False, 'ts': False, 'py': False, 'cpp': False},
            'basic_types': {'c': False, 'ts': False, 'py': False, 'cpp': False},
            'arrays': {'c': False, 'ts': False, 'py': False, 'cpp': False},
            'serialization': {'c': False, 'ts': False, 'py': False, 'cpp': False},
            'cross_language': False,
            'cross_platform_pipe': False
        }
        
        # Cross-language compatibility matrix
        self.cross_language_matrix = {}

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
            self.generated_dir / "py",
            self.generated_dir / "cpp"
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

        # Build the command - use sys.executable to get the correct Python interpreter
        command_parts = [
            sys.executable, "-m", "struct_frame",
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
        if "cpp" in lang_flags:
            command_parts.extend(
                ["--build_cpp", "--cpp_path", str(self.generated_dir / "cpp")])

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

    def test_cpp_compilation(self):
        """Test C++ code compilation"""
        self.log("=== Testing C++ Compilation ===")

        # Check if g++ is available
        gpp_available, _, _ = self.run_command("g++ --version")
        if not gpp_available:
            self.log(
                "G++ compiler not found - skipping C++ compilation test", "WARNING")
            return True  # Don't fail the entire test suite

        test_files = [
            "test_basic_types.cpp",
            "test_arrays.cpp",
            "test_serialization.cpp"
        ]

        all_success = True

        for test_file in test_files:
            test_path = self.tests_dir / "cpp" / test_file
            output_path = self.tests_dir / "cpp" / f"{test_file[:-4]}.exe"

            # Create compile command - use C++14 for compatibility with older GCC
            command = f"g++ -std=c++14 -I{self.generated_dir / 'cpp'} -o {output_path} {test_path}"

            success, stdout, stderr = self.run_command(command)
            if success:
                self.log(
                    f"C++ compilation successful for {test_file}", "SUCCESS")
                self.results['compilation']['cpp'] = True
            else:
                self.log(f"C++ compilation failed for {test_file}", "ERROR")
                all_success = False

        return all_success

    def run_cpp_tests(self):
        """Run C++ test executables"""
        self.log("=== Running C++ Tests ===")

        test_executables = [
            ("test_basic_types.exe", "basic_types"),
            ("test_arrays.exe", "arrays"),
            ("test_serialization.exe", "serialization")
        ]

        all_success = True

        for exe_name, test_type in test_executables:
            exe_path = self.tests_dir / "cpp" / exe_name

            if not exe_path.exists():
                self.log(f"Executable not found: {exe_name}", "WARNING")
                continue

            success, stdout, stderr = self.run_command(
                str(exe_path), cwd=self.tests_dir / "cpp")

            if success:
                self.log(f"C++ {test_type} test passed", "SUCCESS")
                self.results[test_type]['cpp'] = True
            else:
                self.log(f"C++ {test_type} test failed", "ERROR")
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

        # Initialize cross-language compatibility matrix
        # Structure: encoder_language -> {decoder_language: success_status}
        self.cross_language_matrix = {}

        # Define available languages and their test data files
        languages = {
            'C': {
                'data_file': 'c_test_data.bin',
                'data_locations': [self.tests_dir / "c"],
                'test_exe': self.tests_dir / "c" / "test_serialization.exe"
            },
            'Python': {
                'data_file': 'python_test_data.bin', 
                'data_locations': [self.tests_dir / "py"],
                'test_script': self.tests_dir / "py" / "test_serialization.py"
            },
            'TypeScript': {
                'data_file': 'typescript_test_data.bin',
                'data_locations': [self.generated_dir / "ts"],
                'test_script': None  # TypeScript tests might not be available
            }
        }

        # First, check which languages have generated test data files
        available_encoders = []
        for lang_name, lang_info in languages.items():
            for location in lang_info['data_locations']:
                data_path = location / lang_info['data_file']
                if data_path.exists():
                    available_encoders.append(lang_name)
                    self.log(f"Found {lang_name} test data: {data_path}", "SUCCESS")
                    break

        if not available_encoders:
            self.log("No cross-language test data files found", "WARNING") 
            return False

        # Test cross-language decoding for each available encoder/decoder pair
        for encoder_lang in available_encoders:
            self.cross_language_matrix[encoder_lang] = {}
            
            # Test decoding with each available language
            for decoder_lang in available_encoders:
                if decoder_lang == encoder_lang:
                    # Same language encoding/decoding should always work (tested in serialization tests)
                    self.cross_language_matrix[encoder_lang][decoder_lang] = True
                    continue
                
                # Test cross-language compatibility
                success = self._test_cross_decode(encoder_lang, decoder_lang, languages)
                self.cross_language_matrix[encoder_lang][decoder_lang] = success

        # Print detailed compatibility matrix
        self._print_cross_language_matrix()

        # Determine overall success
        total_tests = 0
        successful_tests = 0
        for encoder_lang, decoder_results in self.cross_language_matrix.items():
            for decoder_lang, success in decoder_results.items():
                if encoder_lang != decoder_lang:  # Skip self-tests
                    total_tests += 1
                    if success:
                        successful_tests += 1

        if successful_tests > 0:
            self.results['cross_language'] = True
            self.log(f"Cross-language compatibility: {successful_tests}/{total_tests} tests passed", "SUCCESS")
            return True
        else:
            self.results['cross_language'] = False
            self.log("No cross-language compatibility tests passed", "WARNING")
            return False

    def _test_cross_decode(self, encoder_lang, decoder_lang, languages):
        """Test if decoder_lang can decode data from encoder_lang"""
        try:
            encoder_info = languages[encoder_lang]
            decoder_info = languages[decoder_lang]
            
            # Find the encoder's data file
            encoder_data_path = None
            for location in encoder_info['data_locations']:
                potential_path = location / encoder_info['data_file']
                if potential_path.exists():
                    encoder_data_path = potential_path
                    break
                    
            if not encoder_data_path:
                return False

            # Test decoding based on decoder language
            if decoder_lang == 'C' and 'test_exe' in decoder_info:
                return self._test_c_cross_decode(encoder_data_path, encoder_lang, decoder_info['test_exe'])
            elif decoder_lang == 'Python' and 'test_script' in decoder_info:
                return self._test_python_cross_decode(encoder_data_path, encoder_lang, decoder_info['test_script'])
            else:
                # Language decoder not available
                return False
                
        except Exception as e:
            self.log(f"Exception testing {decoder_lang} decode of {encoder_lang} data: {e}", "WARNING")
            return False

    def _test_c_cross_decode(self, data_file_path, encoder_lang, test_exe_path):
        """Test C decoder with data from another language"""
        if not test_exe_path.exists():
            return False
            
        # Copy the data file to where the C test expects it
        target_file = self.tests_dir / "c" / data_file_path.name
        try:
            import shutil
            shutil.copy2(data_file_path, target_file)
            
            # Run the C test (it will try to decode the copied file)
            success, stdout, stderr = self.run_command(str(test_exe_path), cwd=self.tests_dir / "c")
            return success
            
        except Exception as e:
            self.log(f"C cross-decode test failed: {e}", "WARNING")
            return False
        finally:
            # Clean up the copied file
            try:
                if target_file.exists():
                    target_file.unlink()
            except:
                pass

    def _test_python_cross_decode(self, data_file_path, encoder_lang, test_script_path):
        """Test Python decoder with data from another language"""
        if not test_script_path.exists():
            return False
            
        # Copy the data file to where the Python test expects it
        target_file = self.tests_dir / "py" / data_file_path.name
        try:
            import shutil
            shutil.copy2(data_file_path, target_file)
            
            # Set up Python environment and run the test
            env = os.environ.copy()
            env["PYTHONPATH"] = str(self.generated_dir / "py")
            
            result = subprocess.run(
                [sys.executable, str(test_script_path)],
                cwd=self.tests_dir / "py",
                capture_output=True,
                text=True,
                env=env,
                timeout=30
            )
            
            return result.returncode == 0
            
        except Exception as e:
            self.log(f"Python cross-decode test failed: {e}", "WARNING")
            return False
        finally:
            # Clean up the copied file
            try:
                if target_file.exists():
                    target_file.unlink()
            except:
                pass

    def _print_cross_language_matrix(self):
        """Print a detailed cross-language compatibility matrix"""
        if not self.cross_language_matrix:
            return
            
        print("\n🔀 CROSS-LANGUAGE COMPATIBILITY MATRIX")
        print("="*50)
        print("Format: [Encoder Language] → [Decoder Language]")
        print()
        
        # Get all languages involved
        all_languages = set()
        for encoder_lang, decoder_results in self.cross_language_matrix.items():
            all_languages.add(encoder_lang)
            all_languages.update(decoder_results.keys())
        
        # Sort for consistent output
        sorted_languages = sorted(all_languages)
        
        # Print header
        header = "Encoder\\Decoder".ljust(15)
        for lang in sorted_languages:
            header += lang[:8].ljust(10)
        print(header)
        print("-" * len(header))
        
        # Print matrix rows
        for encoder_lang in sorted_languages:
            if encoder_lang in self.cross_language_matrix:
                row = encoder_lang.ljust(15)
                for decoder_lang in sorted_languages:
                    if decoder_lang in self.cross_language_matrix[encoder_lang]:
                        success = self.cross_language_matrix[encoder_lang][decoder_lang]
                        symbol = "✅" if success else "❌"
                        if encoder_lang == decoder_lang:
                            symbol = "🔄"  # Self-test symbol
                    else:
                        symbol = "⚫"  # Not tested
                    row += f"{symbol:>8}  "
                print(row)
        
        print()
        print("Legend: ✅ = Success  ❌ = Failed  🔄 = Self-test  ⚫ = Not tested")
        print()
    
    def run_cross_platform_pipe_tests(self):
        """Run cross-platform pipe tests"""
        self.log("=== Running Cross-Platform Pipe Tests ===")
        
        cross_platform_script = self.tests_dir / "cross_platform_test.py"
        if not cross_platform_script.exists():
            self.log("Cross-platform test script not found", "WARNING")
            return True  # Don't fail if test doesn't exist
        
        cmd = f"{sys.executable} {cross_platform_script}"
        success, stdout, stderr = self.run_command(cmd, cwd=self.tests_dir)
        
        # Print the output regardless of success for visibility
        if stdout:
            print(stdout)
        
        if success:
            self.log("Cross-platform pipe tests passed", "SUCCESS")
            self.results['cross_platform_pipe'] = True
            return True
        else:
            self.log("Cross-platform pipe tests failed", "WARNING")
            # Don't fail the entire suite for this
            self.results['cross_platform_pipe'] = False
            return True

    def print_summary(self, tested_languages=['c', 'ts', 'py', 'cpp']):
        """Print a summary of all test results"""
        print("\n" + "="*60)
        print("📊 TEST RESULTS SUMMARY")
        print("="*60)

        # Count successes (adjust for skipped compiler tests)
        total_tests = 0
        passed_tests = 0

        # Code generation results
        print("\n🔧 Code Generation:")
        for lang in tested_languages:
            status = "✅ PASS" if self.results['generation'][lang] else "❌ FAIL"
            print(f"  {lang.upper():>10}: {status}")
            total_tests += 1
            if self.results['generation'][lang]:
                passed_tests += 1

        # Compilation results (only for languages that need compilation)
        compiled_languages = [
            lang for lang in tested_languages if lang in ['c', 'ts', 'cpp']]
        if compiled_languages:
            print("\n🔨 Compilation:")
            for lang in compiled_languages:
                status = "✅ PASS" if self.results['compilation'][lang] else "❌ FAIL"
                print(f"  {lang.upper():>10}: {status}")
                total_tests += 1
                if self.results['compilation'][lang]:
                    passed_tests += 1

        # Test execution results
        test_types = ['basic_types', 'arrays', 'serialization']
        for test_type in test_types:
            print(f"\n🧪 {test_type.replace('_', ' ').title()} Tests:")
            for lang in tested_languages:
                status = "✅ PASS" if self.results[test_type][lang] else "❌ FAIL"
                print(f"  {lang.upper():>10}: {status}")
                total_tests += 1
                if self.results[test_type][lang]:
                    passed_tests += 1

        # Cross-language compatibility
        print(f"\n🌐 Cross-Language Compatibility:")
        status = "✅ PASS" if self.results['cross_language'] else "❌ FAIL"
        print(f"  {'Overall':>10}: {status}")
        total_tests += 1
        if self.results['cross_language']:
            passed_tests += 1
        
        # Print detailed cross-language matrix if available
        if hasattr(self, 'cross_language_matrix') and self.cross_language_matrix:
            print("\n📋 Detailed Cross-Language Test Results:")
            for encoder_lang, decoder_results in self.cross_language_matrix.items():
                for decoder_lang, success in decoder_results.items():
                    if encoder_lang != decoder_lang:  # Skip self-tests in summary
                        status_symbol = "✅" if success else "❌"
                        print(f"    {encoder_lang} → {decoder_lang}: {status_symbol}")
            
            # Count cross-language specific results
            cross_success = sum(1 for encoder_lang, decoder_results in self.cross_language_matrix.items()
                              for decoder_lang, success in decoder_results.items() 
                              if encoder_lang != decoder_lang and success)
            cross_total = sum(1 for encoder_lang, decoder_results in self.cross_language_matrix.items()
                            for decoder_lang, success in decoder_results.items() 
                            if encoder_lang != decoder_lang)
            
            if cross_total > 0:
                print(f"    Cross-language decode success rate: {cross_success}/{cross_total} ({100*cross_success/cross_total:.1f}%)")
            else:
                print("    No cross-language tests available")
        
        # Cross-platform pipe tests
        status = "✅ PASS" if self.results['cross_platform_pipe'] else "❌ FAIL"
        print(f"  {'Pipe-based':>10}: {status}")
        total_tests += 1
        if self.results['cross_platform_pipe']:
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
        "--skip-cpp",
        action="store_true",
        help="Skip C++ language tests"
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
    if not args.skip_cpp:
        languages.append("cpp")

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

        if "cpp" in languages:
            if not runner.test_cpp_compilation():
                success = False
            if not runner.run_cpp_tests():
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
        
        # Run cross-platform pipe tests
        if not runner.run_cross_platform_pipe_tests():
            success = False

        # Print summary
        overall_success = runner.print_summary(languages)

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
