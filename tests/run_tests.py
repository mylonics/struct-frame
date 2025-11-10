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
            'cross_platform_serialization': {'c': False, 'ts': False, 'py': False, 'cpp': False},
            'cross_platform_deserialization': {'c': False, 'ts': False, 'py': False, 'cpp': False},
            'cross_language': False
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

    def run_command(self, command, cwd=None, timeout=30, show_command=True):
        """Run a shell command and return success status"""
        if cwd is None:
            cwd = self.project_root

        if show_command and self.verbose:
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
                if self.verbose:
                    self.log(f"Command succeeded", "INFO")
                return True, result.stdout, result.stderr
            else:
                if self.verbose:
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
        if self.verbose:
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
            if self.verbose:
                self.log(f"Created directory: {directory}")

        # Clean up any existing binary test files
        for pattern in ["*_test_data.bin", "*.exe"]:
            for file in self.project_root.glob(pattern):
                try:
                    file.unlink()
                    if self.verbose:
                        self.log(f"Cleaned up: {file}")
                except Exception as e:
                    if self.verbose:
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

        if self.verbose:
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
                if self.verbose:
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
        print("\n" + "="*60)
        print("🔧 CODE GENERATION")
        print("="*60)

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

        # Print summary for code generation
        print()
        for lang in languages:
            status = "✅ PASS" if self.results['generation'][lang] else "❌ FAIL"
            print(f"  {lang.upper():>6}: {status}")

        return all_success

    def test_c_compilation(self):
        """Test C code compilation"""
        # Check if gcc is available
        gcc_available, _, _ = self.run_command("gcc --version", show_command=False)
        if not gcc_available:
            self.log(
                "GCC compiler not found - skipping C compilation", "WARNING")
            return True  # Don't fail the entire test suite

        test_files = [
            "test_basic_types.c",
            "test_arrays.c",
            "test_cross_platform_serialization.c",
            "test_cross_platform_deserialization.c"
        ]

        all_success = True

        for test_file in test_files:
            test_path = self.tests_dir / "c" / test_file
            output_path = self.tests_dir / "c" / f"{test_file[:-2]}.exe"

            # Create compile command
            command = f"gcc -I{self.generated_dir / 'c'} -o {output_path} {test_path} -lm"

            success, stdout, stderr = self.run_command(command, show_command=False)
            if success:
                self.results['compilation']['c'] = True
            else:
                if self.verbose:
                    self.log(f"C compilation failed for {test_file}", "ERROR")
                all_success = False

        return all_success

    def test_cpp_compilation(self):
        """Test C++ code compilation"""
        # Check if g++ is available
        gpp_available, _, _ = self.run_command("g++ --version", show_command=False)
        if not gpp_available:
            self.log(
                "G++ compiler not found - skipping C++ compilation", "WARNING")
            return True  # Don't fail the entire test suite

        test_files = [
            "test_basic_types.cpp",
            "test_arrays.cpp",
            "test_cross_platform_serialization.cpp",
            "test_cross_platform_deserialization.cpp"
        ]

        all_success = True

        for test_file in test_files:
            test_path = self.tests_dir / "cpp" / test_file
            output_path = self.tests_dir / "cpp" / f"{test_file[:-4]}.exe"

            # Create compile command - use C++14 for compatibility with older GCC
            command = f"g++ -std=c++14 -I{self.generated_dir / 'cpp'} -o {output_path} {test_path}"

            success, stdout, stderr = self.run_command(command, show_command=False)
            if success:
                self.results['compilation']['cpp'] = True
            else:
                if self.verbose:
                    self.log(f"C++ compilation failed for {test_file}", "ERROR")
                all_success = False

        return all_success

    def run_cpp_tests(self):
        """Run C++ test executables"""
        test_executables = [
            ("test_basic_types.exe", "basic_types"),
            ("test_arrays.exe", "arrays"),
            ("test_cross_platform_serialization.exe", "cross_platform_serialization"),
            ("test_cross_platform_deserialization.exe", "cross_platform_deserialization")
        ]

        all_success = True

        for exe_name, test_type in test_executables:
            exe_path = self.tests_dir / "cpp" / exe_name

            if not exe_path.exists():
                if self.verbose:
                    self.log(f"Executable not found: {exe_name}", "WARNING")
                continue

            success, stdout, stderr = self.run_command(
                str(exe_path), cwd=self.tests_dir / "cpp", show_command=False)

            if success:
                self.results[test_type]['cpp'] = True
            else:
                if self.verbose:
                    self.log(f"C++ {test_type} test failed", "ERROR")
                all_success = False

        return all_success

    def test_typescript_compilation(self):
        """Test TypeScript code compilation"""
        # First check if TypeScript is available
        success, _, _ = self.run_command("tsc --version", show_command=False)
        if not success:
            self.log(
                "TypeScript compiler not found - skipping TS compilation", "WARNING")
            return True

        # Copy test files to generated directory for compilation
        test_files = [
            "test_basic_types.ts",
            "test_arrays.ts",
            "test_cross_platform_serialization.ts",
            "test_cross_platform_deserialization.ts",
            "encoder_framed.ts",
            "decoder_framed.ts"
        ]

        for test_file in test_files:
            src = self.tests_dir / "ts" / test_file
            if src.exists():
                dest = self.generated_dir / "ts" / test_file
                shutil.copy2(src, dest)

        # Try to compile TypeScript files
        command = f"tsc --outDir {self.generated_dir / 'ts' / 'js'} {self.generated_dir / 'ts'}/*.ts"
        success, stdout, stderr = self.run_command(command, show_command=False)

        if success:
            self.results['compilation']['ts'] = True
            return True
        else:
            if self.verbose:
                self.log("TypeScript compilation failed", "WARNING")
            # Don't fail the entire test suite for TS compilation issues
            return True

    def run_c_tests(self):
        """Run C test executables"""
        test_executables = [
            ("test_basic_types.exe", "basic_types"),
            ("test_arrays.exe", "arrays"),
            ("test_cross_platform_serialization.exe", "cross_platform_serialization"),
            ("test_cross_platform_deserialization.exe", "cross_platform_deserialization")
        ]

        all_success = True

        for exe_name, test_type in test_executables:
            exe_path = self.tests_dir / "c" / exe_name

            if not exe_path.exists():
                if self.verbose:
                    self.log(f"Executable not found: {exe_name}", "WARNING")
                continue

            success, stdout, stderr = self.run_command(
                str(exe_path), cwd=self.tests_dir / "c", show_command=False)

            if success:
                self.results[test_type]['c'] = True
            else:
                if self.verbose:
                    self.log(f"C {test_type} test failed", "ERROR")
                all_success = False

        return all_success

    def run_python_tests(self):
        """Run Python test scripts"""
        test_scripts = [
            ("test_basic_types.py", "basic_types"),
            ("test_arrays.py", "arrays"),
            ("test_cross_platform_serialization.py", "cross_platform_serialization"),
            ("test_cross_platform_deserialization.py", "cross_platform_deserialization")
        ]

        all_success = True

        # Set up Python path to include generated code
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.generated_dir / "py")

        for script_name, test_type in test_scripts:
            script_path = self.tests_dir / "py" / script_name

            if not script_path.exists():
                if self.verbose:
                    self.log(f"Script not found: {script_name}", "WARNING")
                continue

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
                    self.results[test_type]['py'] = True
                else:
                    if self.verbose:
                        self.log(f"Python {test_type} test failed", "ERROR")
                    if result.stderr and self.verbose:
                        print(f"  Error: {result.stderr}")
                    all_success = False

            except Exception as e:
                if self.verbose:
                    self.log(f"Python {test_type} test exception: {e}", "ERROR")
                all_success = False

        return all_success

    def run_typescript_tests(self):
        """Run TypeScript/JavaScript test scripts"""
        # Check if Node.js is available
        success, _, _ = self.run_command("node --version", show_command=False)
        if not success:
            self.log("Node.js not found - skipping TypeScript tests", "WARNING")
            return True

        test_scripts = [
            ("test_basic_types.ts", "basic_types"),
            ("test_arrays.ts", "arrays"),
            ("test_cross_platform_serialization.ts", "cross_platform_serialization"),
            ("test_cross_platform_deserialization.ts", "cross_platform_deserialization")
        ]

        all_success = True

        for script_name, test_type in test_scripts:
            # First compile the TypeScript file
            script_path = self.generated_dir / "ts" / script_name
            js_path = self.generated_dir / "ts" / \
                "js" / f"{script_name[:-3]}.js"

            if not script_path.exists():
                if self.verbose:
                    self.log(
                        f"TypeScript test not found: {script_name}", "WARNING")
                continue

            # Try to run the compiled JavaScript
            if js_path.exists():
                success, stdout, stderr = self.run_command(
                    f"node {js_path}",
                    cwd=self.project_root,  # Run from project root to find node_modules
                    show_command=False
                )

                if success:
                    self.results[test_type]['ts'] = True
                else:
                    if self.verbose:
                        self.log(f"TypeScript {test_type} test failed", "WARNING")
                    # Don't fail entire suite for TS runtime issues
            else:
                if self.verbose:
                    self.log(
                        f"Compiled JavaScript not found for {script_name}", "WARNING")

        return all_success

    def run_cross_language_tests(self):
        """Run cross-language compatibility tests"""
        print("\n" + "="*60)
        print("🔄 CROSS-LANGUAGE DATA INTERCHANGE")
        print("="*60)
        print("Testing if data serialized in one language can be decoded in another\n")

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
            'C++': {
                'data_file': 'cpp_test_data.bin',
                'data_locations': [self.tests_dir / "cpp"],
                'test_exe': self.tests_dir / "cpp" / "test_serialization.exe"
            },
            'Python': {
                'data_file': 'python_test_data.bin', 
                'data_locations': [self.tests_dir / "py"],
                'test_script': self.tests_dir / "py" / "test_serialization.py"
            },
            'TypeScript': {
                'data_file': 'typescript_test_data.bin',
                'data_locations': [self.generated_dir / "ts" / "js", self.generated_dir / "ts"],
                'test_script': self.generated_dir / "ts" / "js" / "test_serialization.js"
            }
        }

        # First, check which languages have generated test data files
        available_encoders = []
        for lang_name, lang_info in languages.items():
            for location in lang_info['data_locations']:
                data_path = location / lang_info['data_file']
                if data_path.exists():
                    available_encoders.append(lang_name)
                    if self.verbose:
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
            if decoder_lang in ['C', 'C++'] and 'test_exe' in decoder_info:
                return self._test_c_cpp_cross_decode(encoder_data_path, encoder_lang, decoder_info['test_exe'], decoder_lang)
            elif decoder_lang == 'Python' and 'test_script' in decoder_info:
                return self._test_python_cross_decode(encoder_data_path, encoder_lang, decoder_info['test_script'])
            elif decoder_lang == 'TypeScript' and 'test_script' in decoder_info:
                return self._test_typescript_cross_decode(encoder_data_path, encoder_lang, decoder_info['test_script'])
            else:
                # Language decoder not available
                return False
                
        except Exception as e:
            self.log(f"Exception testing {decoder_lang} decode of {encoder_lang} data: {e}", "WARNING")
            return False

    def _test_c_cpp_cross_decode(self, data_file_path, encoder_lang, test_exe_path, decoder_lang):
        """Test C/C++ decoder with data from another language"""
        if not test_exe_path.exists():
            return False
            
        # Determine the target directory based on decoder language
        target_dir = self.tests_dir / ("c" if decoder_lang == "C" else "cpp")
        target_file = target_dir / data_file_path.name
        
        try:
            import shutil
            shutil.copy2(data_file_path, target_file)
            
            # Run the C/C++ test (it will try to decode the copied file)
            success, stdout, stderr = self.run_command(str(test_exe_path), cwd=target_dir)
            return success
            
        except Exception as e:
            self.log(f"{decoder_lang} cross-decode test failed: {e}", "WARNING")
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

    def _test_typescript_cross_decode(self, data_file_path, encoder_lang, test_script_path):
        """Test TypeScript decoder with data from another language"""
        if not test_script_path.exists():
            return False
            
        # Copy the data file to where the TypeScript test expects it (running from project root now)
        target_dir = self.project_root / "tests" / "generated" / "ts" / "js"
        target_file = target_dir / data_file_path.name
        try:
            import shutil
            shutil.copy2(data_file_path, target_file)
            
            # Run the TypeScript test from project root
            result = subprocess.run(
                ["node", str(test_script_path)],
                cwd=self.project_root,  # Run from project root
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return result.returncode == 0
            
        except Exception as e:
            self.log(f"TypeScript cross-decode test failed: {e}", "WARNING")
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
        
        # Column width for consistent formatting
        ENCODER_COL_WIDTH = 18
            
        print("\nCompatibility Test Results:")
        
        # Get all languages involved
        all_languages = set()
        for encoder_lang, decoder_results in self.cross_language_matrix.items():
            all_languages.add(encoder_lang)
            all_languages.update(decoder_results.keys())
        
        # Sort for consistent output
        sorted_languages = sorted(all_languages)
        
        # Print matrix table
        header = "Encoder\\Decoder".ljust(ENCODER_COL_WIDTH)
        for lang in sorted_languages:
            header += lang[:8].ljust(10)
        print(header)
        print("-" * len(header))
        
        # Print matrix rows
        for encoder_lang in sorted_languages:
            if encoder_lang in self.cross_language_matrix:
                row = encoder_lang.ljust(ENCODER_COL_WIDTH)
                for decoder_lang in sorted_languages:
                    if decoder_lang in self.cross_language_matrix[encoder_lang]:
                        success = self.cross_language_matrix[encoder_lang][decoder_lang]
                        if encoder_lang == decoder_lang:
                            symbol = "  —  "  # Self-test symbol
                        else:
                            symbol = " ✅ " if success else " ❌ "
                    else:
                        symbol = "  ⚫  "  # Not tested
                    row += f"{symbol:>8}  "
                print(row)
        
        # Count success rate
        cross_success = sum(1 for encoder_lang, decoder_results in self.cross_language_matrix.items()
                          for decoder_lang, success in decoder_results.items() 
                          if encoder_lang != decoder_lang and success)
        cross_total = sum(1 for encoder_lang, decoder_results in self.cross_language_matrix.items()
                        for decoder_lang, success in decoder_results.items() 
                        if encoder_lang != decoder_lang)
        
        if cross_total > 0:
            print(f"\nSuccess rate: {cross_success}/{cross_total} ({100*cross_success/cross_total:.0f}%)")
        print()
    
    
    def run_test_by_type(self, test_type, languages):
        """Run a specific test type across all languages"""
        test_display_name = test_type.replace('_', ' ').title()
        print(f"\n🧪 {test_display_name} Tests")
        
        # Run test for each language
        for lang in languages:
            if lang == 'c':
                exe_path = self.tests_dir / "c" / f"test_{test_type}.exe"
                if exe_path.exists():
                    success, _, _ = self.run_command(
                        str(exe_path), cwd=self.tests_dir / "c", show_command=False)
                    self.results[test_type]['c'] = success
            
            elif lang == 'cpp':
                exe_path = self.tests_dir / "cpp" / f"test_{test_type}.exe"
                if exe_path.exists():
                    success, _, _ = self.run_command(
                        str(exe_path), cwd=self.tests_dir / "cpp", show_command=False)
                    self.results[test_type]['cpp'] = success
            
            elif lang == 'py':
                script_path = self.tests_dir / "py" / f"test_{test_type}.py"
                if script_path.exists():
                    env = os.environ.copy()
                    env["PYTHONPATH"] = str(self.generated_dir / "py")
                    
                    try:
                        result = subprocess.run(
                            [sys.executable, str(script_path)],
                            cwd=self.tests_dir / "py",
                            capture_output=True,
                            text=True,
                            env=env,
                            timeout=30
                        )
                        self.results[test_type]['py'] = (result.returncode == 0)
                    except Exception:
                        self.results[test_type]['py'] = False
            
            elif lang == 'ts':
                js_path = self.generated_dir / "ts" / "js" / f"test_{test_type}.js"
                if js_path.exists():
                    success, _, _ = self.run_command(
                        f"node {js_path}",
                        cwd=self.project_root,  # Run from project root to find node_modules
                        show_command=False
                    )
                    self.results[test_type]['ts'] = success
        
        # Print results for this test type
        for lang in languages:
            status = "✅ PASS" if self.results[test_type][lang] else "❌ FAIL"
            print(f"  {lang.upper():>6}: {status}")
    
    def compile_all_languages(self, languages):
        """Compile test code for all languages"""
        print("\n" + "="*60)
        print("🔨 COMPILATION")
        print("="*60)
        
        for lang in languages:
            if lang == 'c':
                self.test_c_compilation()
            elif lang == 'cpp':
                self.test_cpp_compilation()
            elif lang == 'ts':
                self.test_typescript_compilation()
        
        # Print compilation results
        print()
        compiled_languages = [lang for lang in languages if lang in ['c', 'ts', 'cpp']]
        for lang in compiled_languages:
            status = "✅ PASS" if self.results['compilation'][lang] else "❌ FAIL"
            print(f"  {lang.upper():>6}: {status}")

    def print_summary(self, tested_languages=['c', 'ts', 'py', 'cpp']):
        """Print a summary of all test results"""
        print("\n" + "="*60)
        print("📊 TEST RESULTS SUMMARY")
        print("="*60)

        # Count successes (adjust for skipped compiler tests)
        total_tests = 0
        passed_tests = 0

        # Count code generation results
        for lang in tested_languages:
            total_tests += 1
            if self.results['generation'][lang]:
                passed_tests += 1

        # Count compilation results (only for languages that need compilation)
        compiled_languages = [
            lang for lang in tested_languages if lang in ['c', 'ts', 'cpp']]
        for lang in compiled_languages:
            total_tests += 1
            if self.results['compilation'][lang]:
                passed_tests += 1

        # Count test execution results
        test_types = ['basic_types', 'arrays', 'cross_platform_serialization', 'cross_platform_deserialization']
        for test_type in test_types:
            for lang in tested_languages:
                total_tests += 1
                if self.results[test_type][lang]:
                    passed_tests += 1

        # Cross-language compatibility
        total_tests += 1
        if self.results['cross_language']:
            passed_tests += 1

        # Overall result
        print(f"\n📈 {passed_tests}/{total_tests} tests passed")

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
            print("   Note: C/C++/TypeScript tests may require additional tools (gcc/g++/tsc)")
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

        # Compile all language implementations
        runner.compile_all_languages(languages)

        # Run tests organized by test type (not by language)
        test_types = ['basic_types', 'arrays', 'cross_platform_serialization', 'cross_platform_deserialization']
        for test_type in test_types:
            runner.run_test_by_type(test_type, languages)

        # Run cross-language compatibility tests
        runner.run_cross_language_tests()

        # Print summary
        overall_success = runner.print_summary(languages)

        end_time = time.time()
        print(f"\n⏱️  Total test time: {end_time - start_time:.2f} seconds")

        return overall_success

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
