#!/usr/bin/env python3
"""
Test package import and inheritance functionality.
This script validates:
1. Package ID inheritance from importing package to imported package
2. Cross-package type references work correctly
3. Each proto file generates its own output files
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from struct_frame.generate import parseFile, packages, package_imports, validatePackages

def test_pkg_test_messages_import():
    """Test that pkg_test_messages.proto correctly imports and inherits package IDs."""
    print("Testing pkg_test_messages.proto import and inheritance...")
    
    # Change to tests/proto directory
    test_proto_dir = os.path.join(os.path.dirname(__file__), 'proto')
    os.chdir(test_proto_dir)
    
    # Parse the proto file
    success = parseFile('pkg_test_messages.proto')
    if not success:
        print("  FAIL: Failed to parse pkg_test_messages.proto")
        return False
    
    # Check packages were created
    expected_packages = ['pkg_test_messages', 'common_types', 'pkg_test_a']
    for pkg_name in expected_packages:
        if pkg_name not in packages:
            print(f"  FAIL: Package '{pkg_name}' not found")
            return False
    
    # Check package imports were tracked
    if 'pkg_test_messages' not in package_imports:
        print("  FAIL: package_imports not tracking pkg_test_messages")
        return False
    
    imported_pkgs = package_imports['pkg_test_messages']
    if 'common_types' not in imported_pkgs:
        print("  FAIL: common_types not in imports")
        return False
    if 'pkg_test_a' not in imported_pkgs:
        print("  FAIL: pkg_test_a not in imports")
        return False
    
    # Validate packages (this applies inheritance)
    if not validatePackages():
        print("  FAIL: Package validation failed")
        return False
    
    # Check package IDs after inheritance
    expected_ids = {
        'pkg_test_messages': 1,  # Explicit
        'common_types': 1,       # Inherited from pkg_test_messages
        'pkg_test_a': 2          # Explicit, different ID
    }
    
    for pkg_name, expected_id in expected_ids.items():
        actual_id = packages[pkg_name].package_id
        if actual_id != expected_id:
            print(f"  FAIL: Package '{pkg_name}' has ID {actual_id}, expected {expected_id}")
            return False
    
    # Check cross-package type references
    pkg_test_msg = packages['pkg_test_messages']
    if 'PackageTestMessage' not in pkg_test_msg.messages:
        print("  FAIL: PackageTestMessage not found")
        return False
    
    msg = pkg_test_msg.messages['PackageTestMessage']
    
    # Check field types and their packages
    expected_fields = {
        'created_at': ('Timestamp', 'common_types'),
        'current_status': ('Status', 'common_types'),
        'name': ('string', None)
    }
    
    for field_name, (field_type, expected_type_pkg) in expected_fields.items():
        if field_name not in msg.fields:
            print(f"  FAIL: Field '{field_name}' not found in PackageTestMessage")
            return False
        
        field = msg.fields[field_name]
        if field.fieldType != field_type:
            print(f"  FAIL: Field '{field_name}' has type {field.fieldType}, expected {field_type}")
            return False
        
        if expected_type_pkg and field.type_package != expected_type_pkg:
            print(f"  FAIL: Field '{field_name}' type_package is {field.type_package}, expected {expected_type_pkg}")
            return False
    
    print("  PASS: All package import and inheritance tests passed")
    return True

def main():
    """Run all package tests."""
    print("=" * 60)
    print("PACKAGE IMPORT TESTS")
    print("=" * 60)
    
    all_passed = True
    
    # Test 1: Package import and inheritance
    if not test_pkg_test_messages_import():
        all_passed = False
    
    print()
    print("=" * 60)
    if all_passed:
        print("ALL PACKAGE TESTS PASSED")
        print("=" * 60)
        return 0
    else:
        print("SOME PACKAGE TESTS FAILED")
        print("=" * 60)
        return 1

if __name__ == '__main__':
    sys.exit(main())
