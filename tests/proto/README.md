# Test Proto Files Organization

This directory contains Protocol Buffer definitions used for testing the struct-frame code generation framework across all supported languages.

## File Categories

### Core Test Messages
- **test_messages.proto** - Main test suite for all language backends
  - Message IDs: 201-211
  - Tests: Basic types, arrays, unions, variable-length encoding
  - Used by: Standard test suite across all languages

### Extended Feature Tests
- **extended_messages.proto** - Tests for extended features
  - Message IDs: 256-2048, 800-807
  - Tests: Extended message IDs (>255), large payloads (>255 bytes), large arrays (>256 elements)
  - Requires: ProfileBulk or ProfileNetwork profiles
  - Used by: Extended test suite

- **envelope_messages.proto** - Envelope/container message tests
  - Message IDs: 112-115 (commands), 200 (CommandEnvelope), 212-215 (responses), 250 (ResponseEnvelope)
  - Tests: Message wrapping with oneof and is_envelope option
  - Used by: Envelope feature tests

### Package ID Tests
- **package_test.proto** - Basic package ID functionality (pkgid=10)
- **pkg_test_messages.proto** - Package inheritance testing (pkgid=1)
- **pkg_test_a.proto** - Cross-package imports (pkgid=2)
- **package_a.proto** - Package A for imports (pkgid=12)
- **package_b.proto** - Package B importing A (pkgid=13)

### Multi-File Package Tests
- **sensor_types.proto** - Sensor enums (pkgid=2)
- **sensor_messages.proto** - Sensor messages using types (pkgid=2)
- **sensor_with_import.proto** - Sensor data with common types import (pkgid=2)

### Shared Types
- **common_types.proto** - Reusable types for import testing (no pkgid - inherits from importer)

### Edge Cases
- **multi_pkg_no_ids.proto** - Main package without pkgid
- **no_id_pkg.proto** - Imported package without pkgid

## Message ID Allocation Strategy

Message IDs are organized by feature area to avoid conflicts:

| Range      | Purpose                          | File                    |
|------------|----------------------------------|-------------------------|
| 1-3        | Package ID tests                 | package_test.proto, pkg_test_*.proto |
| 112-115    | Envelope commands                | envelope_messages.proto |
| 200        | Command envelope                 | envelope_messages.proto |
| 201-211    | Core test messages               | test_messages.proto     |
| 212-215    | Envelope responses               | envelope_messages.proto |
| 250        | Response envelope                | envelope_messages.proto |
| 256-2048   | Extended message ID tests        | extended_messages.proto |
| 800-807    | Large payload/array tests        | extended_messages.proto |

## Naming Conventions

### Message Names
- Descriptive names indicating purpose (e.g., `BasicTypesMessage`, `LogMessage`)
- Extended test messages numbered sequentially (e.g., `ExtendedIdMessage1-10`)
- Helper messages use domain names (e.g., `Sensor`, `ADCCommand`)

### Package IDs
- Unique across all test files
- Package A family: pkgid=12-13
- Sensor family: pkgid=2
- Main test packages: pkgid=1, 10

## Recent Improvements

The test messages were reorganized for better coverage and clarity:

1. **Fixed Duplicate Package IDs**
   - package_a: Changed from pkgid=10 to pkgid=12
   - package_b: Changed from pkgid=11 to pkgid=13

2. **Improved Message Naming**
   - Renamed generic "Message" to "LogMessage" (msgid=211) for clarity

3. **Enhanced Documentation**
   - Added file headers explaining purpose and message ID allocation
   - Documented compatible profiles for extended tests
   - Clear comments on message ID ranges and test coverage

4. **Better Organization**
   - Message IDs allocated by feature area
   - Consistent file-level documentation
   - Clear purpose statements for each proto file
