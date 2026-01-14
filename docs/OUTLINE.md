# Documentation Outline for Review

This outline represents the proposed new structure for the Struct Frame documentation.

**Principles:**
- Clear and concise writing
- No superlatives or overexaggerations
- Muted, professional tone
- Quick access to basic information
- Extended features separated from basics
- Code examples for all languages where applicable

---

## Home Page (index.md)

**Purpose:** Brief introduction, installation, and quick start
**Content:**
- What Struct Frame does (1-2 sentences)
- Why Struct Frame - Benefits vs other coding schemes:
  - Zero-copy encoding/decoding in C/C++ (packed structs map directly to memory)
  - Flexible framing (multiple profiles for different scenarios)
  - Nested messages and variable-length arrays (unlike Mavlink)
  - Smaller and simpler than Protobuf/Cap'n Proto (lower encoding cost)
  - Cross-platform code generation
- Installation instructions
- Minimal quick start example
- Quick language reference (tabbed code snippets for C, C++, Python, TypeScript)
- Language support table
- Links to next steps

---

## Getting Started Section
Quick walkthrough to get users productive immediately.

### getting-started/installation.md
**Purpose:** How to install Struct Frame
**Content:**
- pip install command
- Language-specific requirements (compilers, runtimes)
- Verification steps

### getting-started/quick-start.md
**Purpose:** Complete walkthrough with working example
**Content:**
- Create a simple proto file
- Generate code (showing the command)
- Complete C++ example showing encoding and parsing
- Explanation of zero-copy design
- Links to next steps

---

## Basic Usage Section
Essential information for common use cases. Users should find what they need here 90% of the time.

### basic-usage/message-definitions.md
**Purpose:** How to write .proto files for Struct Frame
**Content:**
- Proto file syntax
- Message structure
- Field types (primitives, arrays, nested)
- **Arrays and variable-length messages**
- Message IDs
- Package declarations
- **All proto file options (msgid, package_id, etc.)**
- Simple, practical examples in proto format

### basic-usage/code-generation.md
**Purpose:** How to generate code
**Content:**
- Command line usage
- Language-specific flags
- Output paths
- Common patterns (single language, multiple languages)
- No build integration details (moved to reference)

### basic-usage/language-examples.md
**Purpose:** Detailed reference for using generated code in each language
**Content:**
- **Tabbed sections for each language (not separate pages)**
- Basic serialization/deserialization examples
- Reading/writing message fields
- Handling arrays and nested messages
- C example
- C++ example
- TypeScript example
- JavaScript example
- Python example
- C# example
- **No GraphQL examples** (schema generation only)

### basic-usage/framing.md
**Purpose:** Essential framing concepts for reliable communication
**Content:**
- What framing is and why it's needed (brief)
- Standard framing profiles (table)
- Quick decision guide (which profile to use)
- Example of encoding/decoding with standard profile
- Link to framing details for more info

### basic-usage/framing-details.md
**Purpose:** In-depth framing system documentation (moved from Extended Features)
**Content:**
- Frame structure breakdown
- Header types (Basic, Tiny, None)
- Payload types (Minimal, Default, Extended, etc.)
- Custom frame configurations
- Byte-level frame diagrams
- Checksum details

---

## Extended Features Section
Detailed information for users with specific needs or complex use cases.

### extended-features/sdk-overview.md
**Purpose:** High-level SDK capabilities
**Content:**
- What the SDK provides
- When to use SDK vs. code generation only
- SDK availability by language
- Transport support overview
- **Parser/Encoder Feature Matrix** (language-specific features)
- **SDK Feature Matrix** (which SDK features are available in which languages)
- Links to language-specific SDK docs

### extended-features/cpp-sdk.md
**Purpose:** C++ SDK documentation
**Content:**
- Installation (--sdk vs --sdk_embedded)
- Observer/subscriber pattern
- Transport options
- Serial interface
- Network transports (UDP, TCP, WebSocket)
- Code examples

### extended-features/typescript-sdk.md
**Purpose:** TypeScript/JavaScript SDK documentation
**Content:**
- Installation
- Transport options (UDP, TCP, WebSocket, Serial)
- Promise-based API
- Code examples
- Browser vs Node.js usage

### extended-features/python-sdk.md
**Purpose:** Python SDK documentation
**Content:**
- Installation
- Parser usage
- Sync and async patterns
- Transport options
- Code examples

### extended-features/csharp-sdk.md
**Purpose:** C# SDK documentation
**Content:**
- Installation
- Async/await patterns
- .NET integration
- Transport options
- Code examples

### extended-features/custom-features.md
**Purpose:** Advanced proto features
**Content:**
- Package IDs
- Variable-length messages
- Minimal frames
- Import statements
- Edge cases and limitations

---

## Reference Section
Developer-focused documentation for integration and contribution.

### reference/build-integration.md
**Purpose:** Integrating code generation into build systems
**Content:**
- Makefile integration
- CMake integration
- npm scripts
- Python setuptools
- Examples for each build system

### reference/cli-reference.md
**Purpose:** Complete command-line interface documentation
**Content:**
- All flags and options
- Default values
- Output file naming
- Generated file structure by language

### reference/testing.md
**Purpose:** How to run the test suite
**Content:**
- Running tests
- Test configuration
- Adding new tests
- CI/CD integration

### reference/development.md
**Purpose:** Contributing to Struct Frame
**Content:**
- Development setup
- Repository structure
- Code generation architecture
- Pull request process
- Style guidelines

---

## Migration Notes

### Changes from Previous Documentation:

1. **Reorganized into 4 clear sections:**
   - Getting Started: Fast onboarding
   - Basic Usage: Common tasks
   - Extended Features: Detailed technical information
   - Reference: Developer/contributor info

2. **Key structural changes based on review:**
   - Added Getting Started section with installation and quick start
   - Renamed "Basics" → "Basic Usage"
   - Renamed "Advanced" → "Extended Features"
   - Moved Framing Details to Basic Usage (from Extended Features)
   - Added quick language reference on home page
   - Added benefits summary on home page

3. **Consolidated similar content:**
   - Frame calculator merged into framing basics (decision guide)
   - Parser/Encoder feature matrix added to SDK Overview
   - Language examples in tabbed format (not separate files)

4. **Improved navigation:**
   - Home page provides clear next steps
   - Each section has a clear purpose
   - Progressive disclosure: getting started → basic → extended → reference

5. **Content enhancements:**
   - Arrays and variable messages in message definitions
   - All proto file options documented
   - Feature matrices for language and SDK capabilities
   - No GraphQL examples (schema generation only)

---

## Files to Create/Update

### Getting Started (2 files)
- [x] getting-started/installation.md
- [x] getting-started/quick-start.md

### Basic Usage (5 files)
- [ ] basic-usage/message-definitions.md (update to include arrays, variable messages, all options)
- [ ] basic-usage/code-generation.md
- [ ] basic-usage/language-examples.md (tabbed format, no GraphQL examples)
- [ ] basic-usage/framing.md
- [ ] basic-usage/framing-details.md (moved from extended features)

### Extended Features (6 files)
- [ ] extended-features/sdk-overview.md (add feature matrices)
- [ ] extended-features/cpp-sdk.md
- [ ] extended-features/typescript-sdk.md
- [ ] extended-features/python-sdk.md
- [ ] extended-features/csharp-sdk.md
- [ ] extended-features/custom-features.md

### Reference (4 files)
- [ ] reference/build-integration.md
- [ ] reference/cli-reference.md
- [ ] reference/testing.md
- [ ] reference/development.md

### Total: 17 documentation files + updated index.md

---

## Review Responses

### Structure
✓ Changed to 4-tier structure: Getting Started / Basic Usage / Extended Features / Reference

### Language Examples
✓ Quick reference on home page (tabbed snippets)
✓ Detailed examples in tabbed page (not separate files)
✓ No GraphQL examples

### Framing Details
✓ Moved to Basic Usage section

### Benefits
✓ Added benefits summary to home page comparing to Mavlink, Protobuf, Cap'n Proto

### Message Definitions
✓ Will ensure arrays and variable messages are described
✓ Will document all proto file options

### Feature Matrix
✓ Will add Parser/Encoder Feature Matrix to SDK Overview
✓ Will include SDK features matrix

---

**Status:** Structure updated based on @rijesha review. Ready for content development in Step 3.
