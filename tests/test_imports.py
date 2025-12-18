#!/usr/bin/env python3
"""
Test script for proto file import functionality.
Tests various import scenarios including same-package imports,
cross-package imports, and error conditions.
"""

import os
import sys
import subprocess
import tempfile
import shutil

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def run_struct_frame(proto_file, extra_args=None, expect_fail=False, debug=False):
    """Run struct_frame on a proto file and return success/output."""
    cmd = [
        sys.executable,
        os.path.join(os.path.dirname(__file__), '..', 'src', 'main.py'),
        proto_file,
        '--validate'
    ]
    if debug:
        cmd.append('--debug')
    if extra_args:
        cmd.extend(extra_args)
    
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.join(os.path.dirname(__file__), '..', 'src')
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env
    )
    
    if expect_fail:
        return result.returncode != 0, result.stdout + result.stderr
    else:
        return result.returncode == 0, result.stdout + result.stderr


def test_basic_import():
    """Test basic cross-package import with package IDs."""
    print("Testing basic cross-package import...")
    proto_file = os.path.join(os.path.dirname(__file__), 'proto', 'sensor_data.proto')
    success, output = run_struct_frame(proto_file, debug=True)
    
    if not success:
        print(f"  FAILED: {output}")
        return False
    
    # Check that both packages were processed
    if 'sensor_data' not in output or 'common_types' not in output:
        print(f"  FAILED: Expected both packages in output")
        return False
    
    print("  PASSED")
    return True


def test_same_package_import():
    """Test importing into the same package."""
    print("Testing same-package import...")
    proto_file = os.path.join(os.path.dirname(__file__), 'proto', 'same_package_import.proto')
    success, output = run_struct_frame(proto_file, debug=True)
    
    if not success:
        print(f"  FAILED: {output}")
        return False
    
    # Check that package contains types from both files
    if 'ExtendedStatus' not in output or 'Status' not in output:
        print(f"  FAILED: Expected types from both files in same package")
        return False
    
    print("  PASSED")
    return True


def test_missing_package_id():
    """Test error when package_id is missing in multi-package scenario."""
    print("Testing missing package_id error...")
    proto_file = os.path.join(os.path.dirname(__file__), 'proto', 'test_missing_id.proto')
    success, output = run_struct_frame(proto_file, expect_fail=True)
    
    if not success:
        print(f"  FAILED: Expected validation to fail")
        return False
    
    if 'does not have a package_id assigned' not in output:
        print(f"  FAILED: Expected error about missing package_id")
        return False
    
    print("  PASSED")
    return True


def test_duplicate_package_id():
    """Test error when package_id is duplicated."""
    print("Testing duplicate package_id error...")
    proto_file = os.path.join(os.path.dirname(__file__), 'proto', 'test_duplicate_id.proto')
    success, output = run_struct_frame(proto_file, expect_fail=True)
    
    if not success:
        print(f"  FAILED: Expected validation to fail")
        return False
    
    if 'Duplicate package_id' not in output:
        print(f"  FAILED: Expected error about duplicate package_id")
        return False
    
    print("  PASSED")
    return True


def test_circular_import():
    """Test circular import detection."""
    print("Testing circular import detection...")
    proto_file = os.path.join(os.path.dirname(__file__), 'proto', 'circular_a.proto')
    success, output = run_struct_frame(proto_file, expect_fail=True)
    
    if not success:
        print(f"  FAILED: Expected validation to fail")
        return False
    
    if 'Recursion Error' not in output or 'cyclical' not in output:
        print(f"  FAILED: Expected recursion error for circular dependency")
        return False
    
    print("  PASSED")
    return True


def test_code_generation_with_imports():
    """Test that code generation works with imports."""
    print("Testing code generation with imports...")
    proto_file = os.path.join(os.path.dirname(__file__), 'proto', 'sensor_data.proto')
    
    # Create temporary directory for generated code
    with tempfile.TemporaryDirectory() as tmpdir:
        py_path = os.path.join(tmpdir, 'py')
        c_path = os.path.join(tmpdir, 'c')
        
        cmd = [
            sys.executable,
            os.path.join(os.path.dirname(__file__), '..', 'src', 'main.py'),
            proto_file,
            '--build_py', '--py_path', py_path,
            '--build_c', '--c_path', c_path
        ]
        
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.join(os.path.dirname(__file__), '..', 'src')
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env
        )
        
        if result.returncode != 0:
            print(f"  FAILED: Code generation failed: {result.stdout + result.stderr}")
            return False
        
        # Check that files were generated for both packages
        py_sensor = os.path.join(py_path, 'sensor_data_sf.py')
        py_common = os.path.join(py_path, 'common_types_sf.py')
        c_sensor = os.path.join(c_path, 'sensor_data.sf.h')
        c_common = os.path.join(c_path, 'common_types.sf.h')
        
        if not all(os.path.exists(f) for f in [py_sensor, py_common, c_sensor, c_common]):
            print(f"  FAILED: Not all expected files were generated")
            print(f"    Python files exist: {os.path.exists(py_sensor)}, {os.path.exists(py_common)}")
            print(f"    C files exist: {os.path.exists(c_sensor)}, {os.path.exists(c_common)}")
            return False
        
        print("  PASSED")
        return True


def test_single_package_no_id_required():
    """Test that single package doesn't require package_id."""
    print("Testing single package without package_id...")
    proto_file = os.path.join(os.path.dirname(__file__), 'proto', 'no_package_id.proto')
    success, output = run_struct_frame(proto_file)
    
    if not success:
        print(f"  FAILED: Single package should not require package_id: {output}")
        return False
    
    print("  PASSED")
    return True


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Proto File Import Tests")
    print("="*60 + "\n")
    
    tests = [
        test_basic_import,
        test_same_package_import,
        test_missing_package_id,
        test_duplicate_package_id,
        test_circular_import,
        test_code_generation_with_imports,
        test_single_package_no_id_required,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60 + "\n")
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
