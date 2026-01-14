# Documentation Outline for Review

This outline represents the proposed new structure for the Struct Frame documentation.

**Principles:**
- Clear and concise writing
- No superlatives or overexaggerations
- Muted, professional tone
- Quick access to basic information
- Advanced topics separated from basics
- Code examples for all languages where applicable

---

## Home Page (index.md)

**Purpose:** Brief introduction, installation, and quick start
**Content:**
- What Struct Frame does (1-2 sentences)
- Installation instructions
- Minimal quick start example
- Language support table
- Links to next steps

---

## Basics Section
Essential information for common use cases. Users should find what they need here 90% of the time.

### basics/message-definitions.md
**Purpose:** How to write .proto files for Struct Frame
**Content:**
- Proto file syntax
- Message structure
- Field types (primitives, arrays, nested)
- Message IDs
- Package declarations
- Simple, practical examples in proto format

### basics/code-generation.md
**Purpose:** How to generate code
**Content:**
- Command line usage
- Language-specific flags
- Output paths
- Common patterns (single language, multiple languages)
- No build integration details (moved to reference)

### basics/language-examples.md
**Purpose:** Quick reference for using generated code in each language
**Content:**
- Tabbed sections for each language
- Basic serialization/deserialization examples
- Reading/writing message fields
- C example
- C++ example
- TypeScript example
- JavaScript example
- Python example
- C# example
- GraphQL example (if applicable)

### basics/framing.md
**Purpose:** Essential framing concepts for reliable communication
**Content:**
- What framing is and why it's needed (brief)
- Standard framing profiles (table)
- Quick decision guide (which profile to use)
- Example of encoding/decoding with standard profile
- Link to advanced framing for details

---

## Advanced Section
Detailed information for users with specific needs or complex use cases.

### advanced/framing-details.md
**Purpose:** In-depth framing system documentation
**Content:**
- Frame structure breakdown
- Header types (Basic, Tiny, None)
- Payload types (Minimal, Default, Extended, etc.)
- Custom frame configurations
- Byte-level frame diagrams
- Checksum details

### advanced/sdk-overview.md
**Purpose:** High-level SDK capabilities
**Content:**
- What the SDK provides
- When to use SDK vs. code generation only
- SDK availability by language
- Transport support overview
- Links to language-specific SDK docs

### advanced/cpp-sdk.md
**Purpose:** C++ SDK documentation
**Content:**
- Installation (--sdk vs --sdk_embedded)
- Observer/subscriber pattern
- Transport options
- Serial interface
- Network transports (UDP, TCP, WebSocket)
- Code examples

### advanced/typescript-sdk.md
**Purpose:** TypeScript/JavaScript SDK documentation
**Content:**
- Installation
- Transport options (UDP, TCP, WebSocket, Serial)
- Promise-based API
- Code examples
- Browser vs Node.js usage

### advanced/python-sdk.md
**Purpose:** Python SDK documentation
**Content:**
- Installation
- Parser usage
- Sync and async patterns
- Transport options
- Code examples

### advanced/csharp-sdk.md
**Purpose:** C# SDK documentation
**Content:**
- Installation
- Async/await patterns
- .NET integration
- Transport options
- Code examples

### advanced/custom-features.md
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

1. **Reorganized into 3 clear sections:**
   - Basics: Fast access to common tasks
   - Advanced: Detailed technical information
   - Reference: Developer/contributor info

2. **Consolidated similar content:**
   - Frame calculator merged into framing basics (decision guide)
   - Parser feature matrix integrated into SDK docs where relevant
   - Framing architecture details moved to advanced section

3. **Improved navigation:**
   - Home page provides clear next steps
   - Each section has a clear purpose
   - Progressive disclosure: basic → advanced → reference

4. **Language examples centralized:**
   - One page with tabs for all languages
   - Easier to compare across languages
   - Reduces duplication

5. **Tone improvements:**
   - Removed marketing language
   - Focused on facts and usage
   - Professional, technical writing style

---

## Files to Create

### Basics (5 files)
- [ ] basics/message-definitions.md
- [ ] basics/code-generation.md
- [ ] basics/language-examples.md
- [ ] basics/framing.md

### Advanced (6 files)
- [ ] advanced/framing-details.md
- [ ] advanced/sdk-overview.md
- [ ] advanced/cpp-sdk.md
- [ ] advanced/typescript-sdk.md
- [ ] advanced/python-sdk.md
- [ ] advanced/csharp-sdk.md
- [ ] advanced/custom-features.md

### Reference (4 files)
- [ ] reference/build-integration.md
- [ ] reference/cli-reference.md
- [ ] reference/testing.md
- [ ] reference/development.md

### Total: 15 new documentation files + updated index.md

---

## Review Questions for @rijesha

1. Does the 3-tier structure (Basics/Advanced/Reference) make sense for this project?
2. Should "Language Examples" be on the home page or a separate basics page?
3. Are there any critical topics missing from this outline?
4. Should GraphQL have its own usage section or is it sufficiently different that examples aren't needed?
5. Any concerns about the consolidated structure vs. the previous more granular approach?

---

**Status:** Ready for review by @rijesha
