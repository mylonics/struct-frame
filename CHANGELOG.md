# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!-- insertion marker -->
## [0.0.55](https://github.com/mylonics/struct-frame/releases/tag/0.0.55) - 2026-01-07

<small>[Compare with v0.0.52](https://github.com/mylonics/struct-frame/compare/v0.0.52...0.0.55)</small>

### Added

- Added msg id and msg size directly into cpp code ([00299b6](https://github.com/mylonics/struct-frame/commit/00299b6de59e6b5c95485173dd4758f62887cc43) by Rijesh Augustine).
- Add payload type filtering based on package configuration ([a24d62a](https://github.com/mylonics/struct-frame/commit/a24d62ac3e3802ecec70b82ca53b63a2633646b7) by copilot-swe-agent[bot]).
- Add message ID validation and update generators to use combined 16-bit message IDs ([f7bbcee](https://github.com/mylonics/struct-frame/commit/f7bbceecd36de8463e5d9a20dc3bdc59c1109239) by copilot-swe-agent[bot]).
- Add generated profile-specific framers and parsers for all profiles (#136) ([064daa7](https://github.com/mylonics/struct-frame/commit/064daa7f95cd677c673e514736af762e439fe2d5) by Copilot).

### Fixed

- Fix C# switch statement to use local message ID values instead of combined constants ([26283f2](https://github.com/mylonics/struct-frame/commit/26283f2fb3e3009ab5728812088f0e417f6c8a80) by copilot-swe-agent[bot]).
- Fix type consistency issues identified in code review ([c45326c](https://github.com/mylonics/struct-frame/commit/c45326cdb7ffe7a4eb3e19985a00279578c1c460) by copilot-swe-agent[bot]).
- fixed max_observers ([46ccadd](https://github.com/mylonics/struct-frame/commit/46ccadd3e4930f1fcb2ccf7bfdab1f275d7fc567) by Rijesh Augustine).

### Removed

- Remove pkg_id parameter from encode functions and add ExtendedMinimal payload type ([d1e2ac7](https://github.com/mylonics/struct-frame/commit/d1e2ac71dce11462c9517c2f6b609444594dd341) by copilot-swe-agent[bot]).

## [v0.0.52](https://github.com/mylonics/struct-frame/releases/tag/v0.0.52) - 2026-01-06

<small>[Compare with v0.0.51](https://github.com/mylonics/struct-frame/compare/v0.0.51...v0.0.52)</small>

## [v0.0.51](https://github.com/mylonics/struct-frame/releases/tag/v0.0.51) - 2026-01-06

<small>[Compare with first commit](https://github.com/mylonics/struct-frame/compare/9b9977bd29b2acb1bb1681df472b7400349172d2...v0.0.51)</small>

### Added

- Add automated release pipeline with version bumping and PyPI publishing (#130) ([f289a0c](https://github.com/mylonics/struct-frame/commit/f289a0c10519907a6cb82262d8e01d24f11af4bf) by Copilot).
- Add minimal frame parsing documentation, examples, and auto-generated helper functions (#123) ([a441990](https://github.com/mylonics/struct-frame/commit/a441990f914e9efc04a1d0ac9306e35c083b09dd) by Copilot).
- Add C++ buffer parsing API and comprehensive parser feature matrix (#118) ([3da509b](https://github.com/mylonics/struct-frame/commit/3da509baaa63afdd85736c289599ed3238bd3a48) by Copilot).
- Add Wireshark dissector for struct-frame protocols (#119) ([b9479ae](https://github.com/mylonics/struct-frame/commit/b9479ae12e9befc6813ef8217f9de30650db2868) by Copilot).
- Add inline frame format helpers to C# tests (#114) ([681cd81](https://github.com/mylonics/struct-frame/commit/681cd8159c365a73d5ec490547f867809b8a6e5f) by Copilot).
- Add polyglot parser for multi-frame-type streams (#103) ([6420666](https://github.com/mylonics/struct-frame/commit/6420666082a58259b04f209534f850735edcc669) by Copilot).
- Add intent-based framing profiles and interactive calculator to simplify frame format selection (#99) ([eab5b66](https://github.com/mylonics/struct-frame/commit/eab5b66bee186e404c45c7baf68740c039d2e81f) by Copilot).
- Add high-level SDK with transport abstraction for TypeScript, Python, C++, and C# (opt-in via flags) (#95) ([ddf3b74](https://github.com/mylonics/struct-frame/commit/ddf3b7490e4c92027e09f79ee1563880ceeefb1b) by Copilot).
- Added logo ([b301a31](https://github.com/mylonics/struct-frame/commit/b301a317376d47a70f0cf3251721e1fcff6d9a42) by Rijesh Augustine).
- Added C# tests ([65c7330](https://github.com/mylonics/struct-frame/commit/65c7330fb37a0341adb9200e86c3aefffe534f19) by Rijesh Augustine).
- Add C# language with tests (#73) ([cb5292a](https://github.com/mylonics/struct-frame/commit/cb5292a28442c0d856c8b21be93e27a9c21266b9) by Copilot).
- Add boilerplate code generator script and move frame_formats.proto to src (#61) ([c269bf2](https://github.com/mylonics/struct-frame/commit/c269bf29a699d3d88e55f5406aae96149c9ff633) by Copilot).
- Add separate BasicFrame and BasicFrameWithLen implementations for C and C++ (#52) ([2b4938c](https://github.com/mylonics/struct-frame/commit/2b4938cb6301eea8a4b4745a0603ac7348024d9a) by Copilot).
- Add frame format definitions proto file (#48) ([021f7fc](https://github.com/mylonics/struct-frame/commit/021f7fc6efd594edbd179ce8f270957c6f41cbe2) by Copilot).
- Add GitHub Actions workflow to automatically publish wiki on pushes to main (#44) ([9d08404](https://github.com/mylonics/struct-frame/commit/9d084048972736cb76a5dd619cf6a086eca8c70d) by Copilot).
- Add documentation wiki pages (#42) ([cc97976](https://github.com/mylonics/struct-frame/commit/cc979765589690408e52156a6100e1877dfe8b5f) by Copilot).
- Add JavaScript as a language target (#38) ([0340272](https://github.com/mylonics/struct-frame/commit/0340272719483556cbdcb7702384996566994d59) by Copilot).
- Add guard check for module availability in TS array test ([cb405cc](https://github.com/mylonics/struct-frame/commit/cb405cc5e8e449f92d97c92f61bbfebba84445fc) by copilot-swe-agent[bot]).
- Add encoder/decoder compilation for TypeScript pipe tests ([649aea5](https://github.com/mylonics/struct-frame/commit/649aea5c5ac16e4409e639903a3a8bfd9599ff1f) by copilot-swe-agent[bot]).
- Address code review comments: use constants and improve formatting ([cc9475c](https://github.com/mylonics/struct-frame/commit/cc9475c590621dd63e80b0305cd14d7ef019deb7) by copilot-swe-agent[bot]).
- Address code review feedback - improve comments and remove duplicate checks ([a80c781](https://github.com/mylonics/struct-frame/commit/a80c781de265bac718ce262eae7017f3bedeec03) by copilot-swe-agent[bot]).
- Add explicit permissions to GitHub Actions workflow for security ([f8ccc27](https://github.com/mylonics/struct-frame/commit/f8ccc27e7c856726f60828c913a96560cc2b3c13) by copilot-swe-agent[bot]).
- Add CI pipeline documentation to README ([8f7edbd](https://github.com/mylonics/struct-frame/commit/8f7edbd24e61196f9c04524deae5961dda310781) by copilot-swe-agent[bot]).
- Add GitHub Actions workflow for testing pipeline ([381c1af](https://github.com/mylonics/struct-frame/commit/381c1afbf049606785065fea9a02ce8c9372d96a) by copilot-swe-agent[bot]).
- Address code review feedback ([281551e](https://github.com/mylonics/struct-frame/commit/281551eedb515f2c56c1a535b3e1dc8d10639d60) by copilot-swe-agent[bot]).
- Add proper C++ test files following same pattern as C/TS/Python tests ([352b9bf](https://github.com/mylonics/struct-frame/commit/352b9bfbbaca441de0c63923b4e098394957d4d6) by copilot-swe-agent[bot]).
- Add implementation summary and finalize cross-platform tests ([35c06c4](https://github.com/mylonics/struct-frame/commit/35c06c4964106bdad92d815e34fe1be3366b57cb) by copilot-swe-agent[bot]).
- Address code review feedback and improve cross-platform test ([3f5be2c](https://github.com/mylonics/struct-frame/commit/3f5be2c7d930cb4f4968a7fdab41ad66dc011ebe) by copilot-swe-agent[bot]).
- Add cross-platform pipe test with C encoder/decoder ([4c0f86c](https://github.com/mylonics/struct-frame/commit/4c0f86c0f2736676b24936a1d6525735a7822831) by copilot-swe-agent[bot]).
- Add C++ code generation with enum classes and modern C++ style ([fe671ee](https://github.com/mylonics/struct-frame/commit/fe671eecb2899a871b94595d05b66ee706bdb999) by copilot-swe-agent[bot]).
- Add comprehensive C++ documentation to README ([b847f18](https://github.com/mylonics/struct-frame/commit/b847f182dbdefe7d231d598735bd7c17611aeaef) by copilot-swe-agent[bot]).
- Add C++ code generator with enum classes and boilerplate files ([04dd66b](https://github.com/mylonics/struct-frame/commit/04dd66bc3960c32542069d93dd55aaadd695a821) by copilot-swe-agent[bot]).
- Added details on message framinig ([3637b8c](https://github.com/mylonics/struct-frame/commit/3637b8c29abb3795e370ec8287be9ef485d805ca) by Rijesh Augustine).
- Added flatten keyword ([9a8ea2c](https://github.com/mylonics/struct-frame/commit/9a8ea2c5102b253cf4896059d042189791f48058) by Rijesh Augustine).
- Added graphql schema generator ([2076d92](https://github.com/mylonics/struct-frame/commit/2076d928b3b4aa778dfe5fd1446d330876b8111e) by Rijesh Augustine).
- Added python to dict methods ([bae7220](https://github.com/mylonics/struct-frame/commit/bae7220972efb96318f67352624e26ffc97281dd) by Rijesh Augustine).
- Add comprehensive GitHub Copilot instructions ([d89e963](https://github.com/mylonics/struct-frame/commit/d89e9636892d4c438107af63955c9239731cc4d7) by copilot-swe-agent[bot]).
- Added custom printing of python messages ([5bcf582](https://github.com/mylonics/struct-frame/commit/5bcf58252dfe04f8ed6ba7ae5d89dd2a26feeb80) by Rijesh Augustine).
- Added prototype python parser ([db0a265](https://github.com/mylonics/struct-frame/commit/db0a26585f019314adfffab1e0d0d4db5c1311d8) by Rijesh Augustine).
- Added clang-format file ([4917cf1](https://github.com/mylonics/struct-frame/commit/4917cf18167ad0799d2794c12b2e7a32d8bae641) by Rijesh Augustine).
- Added start of new generator ([b3cdf77](https://github.com/mylonics/struct-frame/commit/b3cdf77df52a1243fe3a27aac3acec419eb56dfc) by Rijesh Augustine).

### Fixed

- Fix multi-message serialization/deserialization across C, C++, Python, JavaScript, TypeScript, and C# (#125) ([62e330c](https://github.com/mylonics/struct-frame/commit/62e330c676fb06f62e4add73f984d978eaba7f4e) by Copilot).
- Fix documentation to use correct module name and prioritize pip installation (#91) ([1c400ca](https://github.com/mylonics/struct-frame/commit/1c400ca7e9e65971605a3b82efe820a2f1e82da0) by Copilot).
- fixed docs deploy (#86) ([b49eb9a](https://github.com/mylonics/struct-frame/commit/b49eb9a4a0521f79dfd7c8297bed3211a8266fa1) by Rijesh Augustine).
- Fix docs build by quoting pip install version constraints (#83) ([427acd9](https://github.com/mylonics/struct-frame/commit/427acd952c5712c141cd01eb42170eeec9286bad) by Copilot).
- Fix documentation deployment workflow error (#79) ([70ec0f8](https://github.com/mylonics/struct-frame/commit/70ec0f872c54e9ec3f24829bbdfcc1bed3e40ab1) by Copilot).
- Fixed test reporting issues ([09b177f](https://github.com/mylonics/struct-frame/commit/09b177fe905f3e3dcfb068458e86219cbaafc0ab) by Rijesh Augustine).
- Fixed c# tests ([ce7fe42](https://github.com/mylonics/struct-frame/commit/ce7fe42b07f2c056e552546d83bb55bad88abe10) by Rijesh Augustine).
- Fix Publish Wiki workflow by using clone strategy with preprocess (#49) ([99bd87f](https://github.com/mylonics/struct-frame/commit/99bd87f6152df2cea0b657f265615f28728da117) by Copilot).
- Fix Publish Wiki workflow configuration (#46) ([9a85797](https://github.com/mylonics/struct-frame/commit/9a857979567e22d867e5759114da75658611a9f0) by Copilot).
- Fix TypeScript cross-platform deserialization test path (#35) ([85c79e9](https://github.com/mylonics/struct-frame/commit/85c79e97d7786a7381485773093a6c8d357ea9fd) by Copilot).
- fixed tests ([f89a0ad](https://github.com/mylonics/struct-frame/commit/f89a0ad43fc4b732ea4ce905bf31007d1b50ea3c) by Rijesh Augustine).
- Fix TypeScript test working directory inconsistency (#28) ([a49985d](https://github.com/mylonics/struct-frame/commit/a49985d4743c6a1a830a180094a71c7f60077056) by Copilot).
- Fixed upload issue ([f9dd3be](https://github.com/mylonics/struct-frame/commit/f9dd3be07dcdbbff831775dd096fec49aedf87fd) by Rijesh Augustine).
- Fix TypeScript test execution path in run_test_by_type ([5c5ff46](https://github.com/mylonics/struct-frame/commit/5c5ff464886c4ac629bef8a0af71f25f8cb69fc5) by copilot-swe-agent[bot]).
- Fix TypeScript enum handling and struct array naming ([3619892](https://github.com/mylonics/struct-frame/commit/3619892fc42c36490701840662195779d7a41794) by copilot-swe-agent[bot]).
- Fix TypeScript array generation and skip basic_types test due to typed-struct library bug ([b4ab68f](https://github.com/mylonics/struct-frame/commit/b4ab68f8fc898f2f8917cda3c4b373de07dbe9b1) by copilot-swe-agent[bot]).
- Fix TypeScript compilation errors - Buffer.from API and int64/uint64 type swap ([f9e126d](https://github.com/mylonics/struct-frame/commit/f9e126d1597a558d8e474ff2393fcb0d286f71d5) by copilot-swe-agent[bot]).
- Fix Python cross-language compatibility tests ([751f6af](https://github.com/mylonics/struct-frame/commit/751f6afb82501c40e45eede0a21a8dede74abcde) by copilot-swe-agent[bot]).
- Fix code review issues and re-enable Python cross-platform tests ([941a56b](https://github.com/mylonics/struct-frame/commit/941a56b272e9cad86ae847642dfb0f07666de740) by copilot-swe-agent[bot]).
- Fix handling of fixed arrays of nested messages ([e2c9719](https://github.com/mylonics/struct-frame/commit/e2c971944031328ed92bb207978650f5232a7e31) by copilot-swe-agent[bot]).
- fixing some test issues ([5f5e53b](https://github.com/mylonics/struct-frame/commit/5f5e53b3d11d4233d7dcae28a98f152b69312a0a) by Rijesh Augustine).
- Fix variable-size strings and add C++ to cross-platform tests ([dabcee3](https://github.com/mylonics/struct-frame/commit/dabcee306039b162798a745fb305825f56b9a90a) by copilot-swe-agent[bot]).
- Fix Python array generation with proper structured library syntax ([195f914](https://github.com/mylonics/struct-frame/commit/195f9145a0d37e8cf197bcf783518d6e82dafdcb) by copilot-swe-agent[bot]).
- fixing some cpp issues ([35623bd](https://github.com/mylonics/struct-frame/commit/35623bdd63db6d5ad9972812ad58ff7f449c1641) by Rijesh Augustine).
- Fix comment about empty structs in C++ generator ([2e62fbf](https://github.com/mylonics/struct-frame/commit/2e62fbf40504744b02c03e1964944114231bed52) by copilot-swe-agent[bot]).
- Fixed cpp array test ([b45e352](https://github.com/mylonics/struct-frame/commit/b45e352557862490ca86269e239119d0df230bdb) by Rijesh Augustine).
- fixed debug validate ([f10c2a4](https://github.com/mylonics/struct-frame/commit/f10c2a4c6122552ab2036a73ddf3969f533e57cf) by Rijesh Augustine).

### Changed

- Changes before error encountered ([8b7cf2c](https://github.com/mylonics/struct-frame/commit/8b7cf2c00cbe845a8558d35a185d9d790ae0a320) by copilot-swe-agent[bot]).
- Changes ready for testing ([7e90204](https://github.com/mylonics/struct-frame/commit/7e902043f8e70300bea4513134eb5294584ac84f) by Rijesh Augustine).

### Removed

- Remove legacy code and deprecated features (#131) ([894f1f5](https://github.com/mylonics/struct-frame/commit/894f1f58ddd19a96e1b00317a418c715286586f3) by Copilot).
- Remove hardcoded test values and implement mixed message type testing (all 6 languages complete) (#128) ([1d5ea0c](https://github.com/mylonics/struct-frame/commit/1d5ea0cf386519661f284806f2f5a2c09b523001) by Copilot).
- Remove legacy compatibility layers and deprecated code (#112) ([31145bc](https://github.com/mylonics/struct-frame/commit/31145bce1ccb580300dcfccce9f279b6997ed440) by Copilot).
- removed theme overrides ([1e66c26](https://github.com/mylonics/struct-frame/commit/1e66c2677c7edb17b696db78ff234050de26b34e) by Rijesh Augustine).
- Remove unused boilerplate code, consolidate to frame_parsers_gen files (#63) ([bbbe504](https://github.com/mylonics/struct-frame/commit/bbbe504ec38ce1c7a9c554f1d4a6c0a411c27a3c) by Copilot).
- Remove typed-struct dependency (#33) ([fc75162](https://github.com/mylonics/struct-frame/commit/fc75162ae47379fcf9b3b23f7bbedad949ac439e) by Copilot).
- Remove structured-classes from CI dependencies ([ec83663](https://github.com/mylonics/struct-frame/commit/ec83663a01f4186a052b9f944999985ea25bb12f) by copilot-swe-agent[bot]).
- Remove backup file and add .bak to gitignore ([041b7a4](https://github.com/mylonics/struct-frame/commit/041b7a4d29e4168e9c6ebfba57aaf73567ef7581) by copilot-swe-agent[bot]).

## [0.0.54](https://github.com/mylonics/struct-frame/releases/tag/0.0.54) - 2026-01-07

<small>[Compare with v0.0.52](https://github.com/mylonics/struct-frame/compare/v0.0.52...0.0.54)</small>

### Added

- Add payload type filtering based on package configuration ([a24d62a](https://github.com/mylonics/struct-frame/commit/a24d62ac3e3802ecec70b82ca53b63a2633646b7) by copilot-swe-agent[bot]).
- Add message ID validation and update generators to use combined 16-bit message IDs ([f7bbcee](https://github.com/mylonics/struct-frame/commit/f7bbceecd36de8463e5d9a20dc3bdc59c1109239) by copilot-swe-agent[bot]).
- Add generated profile-specific framers and parsers for all profiles (#136) ([064daa7](https://github.com/mylonics/struct-frame/commit/064daa7f95cd677c673e514736af762e439fe2d5) by Copilot).

### Fixed

- Fix C# switch statement to use local message ID values instead of combined constants ([26283f2](https://github.com/mylonics/struct-frame/commit/26283f2fb3e3009ab5728812088f0e417f6c8a80) by copilot-swe-agent[bot]).
- Fix type consistency issues identified in code review ([c45326c](https://github.com/mylonics/struct-frame/commit/c45326cdb7ffe7a4eb3e19985a00279578c1c460) by copilot-swe-agent[bot]).
- fixed max_observers ([46ccadd](https://github.com/mylonics/struct-frame/commit/46ccadd3e4930f1fcb2ccf7bfdab1f275d7fc567) by Rijesh Augustine).

### Removed

- Remove pkg_id parameter from encode functions and add ExtendedMinimal payload type ([d1e2ac7](https://github.com/mylonics/struct-frame/commit/d1e2ac71dce11462c9517c2f6b609444594dd341) by copilot-swe-agent[bot]).

## [v0.0.52](https://github.com/mylonics/struct-frame/releases/tag/v0.0.52) - 2026-01-06

<small>[Compare with v0.0.51](https://github.com/mylonics/struct-frame/compare/v0.0.51...v0.0.52)</small>

## [v0.0.51](https://github.com/mylonics/struct-frame/releases/tag/v0.0.51) - 2026-01-06

<small>[Compare with first commit](https://github.com/mylonics/struct-frame/compare/9b9977bd29b2acb1bb1681df472b7400349172d2...v0.0.51)</small>

### Added

- Add automated release pipeline with version bumping and PyPI publishing (#130) ([f289a0c](https://github.com/mylonics/struct-frame/commit/f289a0c10519907a6cb82262d8e01d24f11af4bf) by Copilot).
- Add minimal frame parsing documentation, examples, and auto-generated helper functions (#123) ([a441990](https://github.com/mylonics/struct-frame/commit/a441990f914e9efc04a1d0ac9306e35c083b09dd) by Copilot).
- Add C++ buffer parsing API and comprehensive parser feature matrix (#118) ([3da509b](https://github.com/mylonics/struct-frame/commit/3da509baaa63afdd85736c289599ed3238bd3a48) by Copilot).
- Add Wireshark dissector for struct-frame protocols (#119) ([b9479ae](https://github.com/mylonics/struct-frame/commit/b9479ae12e9befc6813ef8217f9de30650db2868) by Copilot).
- Add inline frame format helpers to C# tests (#114) ([681cd81](https://github.com/mylonics/struct-frame/commit/681cd8159c365a73d5ec490547f867809b8a6e5f) by Copilot).
- Add polyglot parser for multi-frame-type streams (#103) ([6420666](https://github.com/mylonics/struct-frame/commit/6420666082a58259b04f209534f850735edcc669) by Copilot).
- Add intent-based framing profiles and interactive calculator to simplify frame format selection (#99) ([eab5b66](https://github.com/mylonics/struct-frame/commit/eab5b66bee186e404c45c7baf68740c039d2e81f) by Copilot).
- Add high-level SDK with transport abstraction for TypeScript, Python, C++, and C# (opt-in via flags) (#95) ([ddf3b74](https://github.com/mylonics/struct-frame/commit/ddf3b7490e4c92027e09f79ee1563880ceeefb1b) by Copilot).
- Added logo ([b301a31](https://github.com/mylonics/struct-frame/commit/b301a317376d47a70f0cf3251721e1fcff6d9a42) by Rijesh Augustine).
- Added C# tests ([65c7330](https://github.com/mylonics/struct-frame/commit/65c7330fb37a0341adb9200e86c3aefffe534f19) by Rijesh Augustine).
- Add C# language with tests (#73) ([cb5292a](https://github.com/mylonics/struct-frame/commit/cb5292a28442c0d856c8b21be93e27a9c21266b9) by Copilot).
- Add boilerplate code generator script and move frame_formats.proto to src (#61) ([c269bf2](https://github.com/mylonics/struct-frame/commit/c269bf29a699d3d88e55f5406aae96149c9ff633) by Copilot).
- Add separate BasicFrame and BasicFrameWithLen implementations for C and C++ (#52) ([2b4938c](https://github.com/mylonics/struct-frame/commit/2b4938cb6301eea8a4b4745a0603ac7348024d9a) by Copilot).
- Add frame format definitions proto file (#48) ([021f7fc](https://github.com/mylonics/struct-frame/commit/021f7fc6efd594edbd179ce8f270957c6f41cbe2) by Copilot).
- Add GitHub Actions workflow to automatically publish wiki on pushes to main (#44) ([9d08404](https://github.com/mylonics/struct-frame/commit/9d084048972736cb76a5dd619cf6a086eca8c70d) by Copilot).
- Add documentation wiki pages (#42) ([cc97976](https://github.com/mylonics/struct-frame/commit/cc979765589690408e52156a6100e1877dfe8b5f) by Copilot).
- Add JavaScript as a language target (#38) ([0340272](https://github.com/mylonics/struct-frame/commit/0340272719483556cbdcb7702384996566994d59) by Copilot).
- Add guard check for module availability in TS array test ([cb405cc](https://github.com/mylonics/struct-frame/commit/cb405cc5e8e449f92d97c92f61bbfebba84445fc) by copilot-swe-agent[bot]).
- Add encoder/decoder compilation for TypeScript pipe tests ([649aea5](https://github.com/mylonics/struct-frame/commit/649aea5c5ac16e4409e639903a3a8bfd9599ff1f) by copilot-swe-agent[bot]).
- Address code review comments: use constants and improve formatting ([cc9475c](https://github.com/mylonics/struct-frame/commit/cc9475c590621dd63e80b0305cd14d7ef019deb7) by copilot-swe-agent[bot]).
- Address code review feedback - improve comments and remove duplicate checks ([a80c781](https://github.com/mylonics/struct-frame/commit/a80c781de265bac718ce262eae7017f3bedeec03) by copilot-swe-agent[bot]).
- Add explicit permissions to GitHub Actions workflow for security ([f8ccc27](https://github.com/mylonics/struct-frame/commit/f8ccc27e7c856726f60828c913a96560cc2b3c13) by copilot-swe-agent[bot]).
- Add CI pipeline documentation to README ([8f7edbd](https://github.com/mylonics/struct-frame/commit/8f7edbd24e61196f9c04524deae5961dda310781) by copilot-swe-agent[bot]).
- Add GitHub Actions workflow for testing pipeline ([381c1af](https://github.com/mylonics/struct-frame/commit/381c1afbf049606785065fea9a02ce8c9372d96a) by copilot-swe-agent[bot]).
- Address code review feedback ([281551e](https://github.com/mylonics/struct-frame/commit/281551eedb515f2c56c1a535b3e1dc8d10639d60) by copilot-swe-agent[bot]).
- Add proper C++ test files following same pattern as C/TS/Python tests ([352b9bf](https://github.com/mylonics/struct-frame/commit/352b9bfbbaca441de0c63923b4e098394957d4d6) by copilot-swe-agent[bot]).
- Add implementation summary and finalize cross-platform tests ([35c06c4](https://github.com/mylonics/struct-frame/commit/35c06c4964106bdad92d815e34fe1be3366b57cb) by copilot-swe-agent[bot]).
- Address code review feedback and improve cross-platform test ([3f5be2c](https://github.com/mylonics/struct-frame/commit/3f5be2c7d930cb4f4968a7fdab41ad66dc011ebe) by copilot-swe-agent[bot]).
- Add cross-platform pipe test with C encoder/decoder ([4c0f86c](https://github.com/mylonics/struct-frame/commit/4c0f86c0f2736676b24936a1d6525735a7822831) by copilot-swe-agent[bot]).
- Add C++ code generation with enum classes and modern C++ style ([fe671ee](https://github.com/mylonics/struct-frame/commit/fe671eecb2899a871b94595d05b66ee706bdb999) by copilot-swe-agent[bot]).
- Add comprehensive C++ documentation to README ([b847f18](https://github.com/mylonics/struct-frame/commit/b847f182dbdefe7d231d598735bd7c17611aeaef) by copilot-swe-agent[bot]).
- Add C++ code generator with enum classes and boilerplate files ([04dd66b](https://github.com/mylonics/struct-frame/commit/04dd66bc3960c32542069d93dd55aaadd695a821) by copilot-swe-agent[bot]).
- Added details on message framinig ([3637b8c](https://github.com/mylonics/struct-frame/commit/3637b8c29abb3795e370ec8287be9ef485d805ca) by Rijesh Augustine).
- Added flatten keyword ([9a8ea2c](https://github.com/mylonics/struct-frame/commit/9a8ea2c5102b253cf4896059d042189791f48058) by Rijesh Augustine).
- Added graphql schema generator ([2076d92](https://github.com/mylonics/struct-frame/commit/2076d928b3b4aa778dfe5fd1446d330876b8111e) by Rijesh Augustine).
- Added python to dict methods ([bae7220](https://github.com/mylonics/struct-frame/commit/bae7220972efb96318f67352624e26ffc97281dd) by Rijesh Augustine).
- Add comprehensive GitHub Copilot instructions ([d89e963](https://github.com/mylonics/struct-frame/commit/d89e9636892d4c438107af63955c9239731cc4d7) by copilot-swe-agent[bot]).
- Added custom printing of python messages ([5bcf582](https://github.com/mylonics/struct-frame/commit/5bcf58252dfe04f8ed6ba7ae5d89dd2a26feeb80) by Rijesh Augustine).
- Added prototype python parser ([db0a265](https://github.com/mylonics/struct-frame/commit/db0a26585f019314adfffab1e0d0d4db5c1311d8) by Rijesh Augustine).
- Added clang-format file ([4917cf1](https://github.com/mylonics/struct-frame/commit/4917cf18167ad0799d2794c12b2e7a32d8bae641) by Rijesh Augustine).
- Added start of new generator ([b3cdf77](https://github.com/mylonics/struct-frame/commit/b3cdf77df52a1243fe3a27aac3acec419eb56dfc) by Rijesh Augustine).

### Fixed

- Fix multi-message serialization/deserialization across C, C++, Python, JavaScript, TypeScript, and C# (#125) ([62e330c](https://github.com/mylonics/struct-frame/commit/62e330c676fb06f62e4add73f984d978eaba7f4e) by Copilot).
- Fix documentation to use correct module name and prioritize pip installation (#91) ([1c400ca](https://github.com/mylonics/struct-frame/commit/1c400ca7e9e65971605a3b82efe820a2f1e82da0) by Copilot).
- fixed docs deploy (#86) ([b49eb9a](https://github.com/mylonics/struct-frame/commit/b49eb9a4a0521f79dfd7c8297bed3211a8266fa1) by Rijesh Augustine).
- Fix docs build by quoting pip install version constraints (#83) ([427acd9](https://github.com/mylonics/struct-frame/commit/427acd952c5712c141cd01eb42170eeec9286bad) by Copilot).
- Fix documentation deployment workflow error (#79) ([70ec0f8](https://github.com/mylonics/struct-frame/commit/70ec0f872c54e9ec3f24829bbdfcc1bed3e40ab1) by Copilot).
- Fixed test reporting issues ([09b177f](https://github.com/mylonics/struct-frame/commit/09b177fe905f3e3dcfb068458e86219cbaafc0ab) by Rijesh Augustine).
- Fixed c# tests ([ce7fe42](https://github.com/mylonics/struct-frame/commit/ce7fe42b07f2c056e552546d83bb55bad88abe10) by Rijesh Augustine).
- Fix Publish Wiki workflow by using clone strategy with preprocess (#49) ([99bd87f](https://github.com/mylonics/struct-frame/commit/99bd87f6152df2cea0b657f265615f28728da117) by Copilot).
- Fix Publish Wiki workflow configuration (#46) ([9a85797](https://github.com/mylonics/struct-frame/commit/9a857979567e22d867e5759114da75658611a9f0) by Copilot).
- Fix TypeScript cross-platform deserialization test path (#35) ([85c79e9](https://github.com/mylonics/struct-frame/commit/85c79e97d7786a7381485773093a6c8d357ea9fd) by Copilot).
- fixed tests ([f89a0ad](https://github.com/mylonics/struct-frame/commit/f89a0ad43fc4b732ea4ce905bf31007d1b50ea3c) by Rijesh Augustine).
- Fix TypeScript test working directory inconsistency (#28) ([a49985d](https://github.com/mylonics/struct-frame/commit/a49985d4743c6a1a830a180094a71c7f60077056) by Copilot).
- Fixed upload issue ([f9dd3be](https://github.com/mylonics/struct-frame/commit/f9dd3be07dcdbbff831775dd096fec49aedf87fd) by Rijesh Augustine).
- Fix TypeScript test execution path in run_test_by_type ([5c5ff46](https://github.com/mylonics/struct-frame/commit/5c5ff464886c4ac629bef8a0af71f25f8cb69fc5) by copilot-swe-agent[bot]).
- Fix TypeScript enum handling and struct array naming ([3619892](https://github.com/mylonics/struct-frame/commit/3619892fc42c36490701840662195779d7a41794) by copilot-swe-agent[bot]).
- Fix TypeScript array generation and skip basic_types test due to typed-struct library bug ([b4ab68f](https://github.com/mylonics/struct-frame/commit/b4ab68f8fc898f2f8917cda3c4b373de07dbe9b1) by copilot-swe-agent[bot]).
- Fix TypeScript compilation errors - Buffer.from API and int64/uint64 type swap ([f9e126d](https://github.com/mylonics/struct-frame/commit/f9e126d1597a558d8e474ff2393fcb0d286f71d5) by copilot-swe-agent[bot]).
- Fix Python cross-language compatibility tests ([751f6af](https://github.com/mylonics/struct-frame/commit/751f6afb82501c40e45eede0a21a8dede74abcde) by copilot-swe-agent[bot]).
- Fix code review issues and re-enable Python cross-platform tests ([941a56b](https://github.com/mylonics/struct-frame/commit/941a56b272e9cad86ae847642dfb0f07666de740) by copilot-swe-agent[bot]).
- Fix handling of fixed arrays of nested messages ([e2c9719](https://github.com/mylonics/struct-frame/commit/e2c971944031328ed92bb207978650f5232a7e31) by copilot-swe-agent[bot]).
- fixing some test issues ([5f5e53b](https://github.com/mylonics/struct-frame/commit/5f5e53b3d11d4233d7dcae28a98f152b69312a0a) by Rijesh Augustine).
- Fix variable-size strings and add C++ to cross-platform tests ([dabcee3](https://github.com/mylonics/struct-frame/commit/dabcee306039b162798a745fb305825f56b9a90a) by copilot-swe-agent[bot]).
- Fix Python array generation with proper structured library syntax ([195f914](https://github.com/mylonics/struct-frame/commit/195f9145a0d37e8cf197bcf783518d6e82dafdcb) by copilot-swe-agent[bot]).
- fixing some cpp issues ([35623bd](https://github.com/mylonics/struct-frame/commit/35623bdd63db6d5ad9972812ad58ff7f449c1641) by Rijesh Augustine).
- Fix comment about empty structs in C++ generator ([2e62fbf](https://github.com/mylonics/struct-frame/commit/2e62fbf40504744b02c03e1964944114231bed52) by copilot-swe-agent[bot]).
- Fixed cpp array test ([b45e352](https://github.com/mylonics/struct-frame/commit/b45e352557862490ca86269e239119d0df230bdb) by Rijesh Augustine).
- fixed debug validate ([f10c2a4](https://github.com/mylonics/struct-frame/commit/f10c2a4c6122552ab2036a73ddf3969f533e57cf) by Rijesh Augustine).

### Changed

- Changes before error encountered ([8b7cf2c](https://github.com/mylonics/struct-frame/commit/8b7cf2c00cbe845a8558d35a185d9d790ae0a320) by copilot-swe-agent[bot]).
- Changes ready for testing ([7e90204](https://github.com/mylonics/struct-frame/commit/7e902043f8e70300bea4513134eb5294584ac84f) by Rijesh Augustine).

### Removed

- Remove legacy code and deprecated features (#131) ([894f1f5](https://github.com/mylonics/struct-frame/commit/894f1f58ddd19a96e1b00317a418c715286586f3) by Copilot).
- Remove hardcoded test values and implement mixed message type testing (all 6 languages complete) (#128) ([1d5ea0c](https://github.com/mylonics/struct-frame/commit/1d5ea0cf386519661f284806f2f5a2c09b523001) by Copilot).
- Remove legacy compatibility layers and deprecated code (#112) ([31145bc](https://github.com/mylonics/struct-frame/commit/31145bce1ccb580300dcfccce9f279b6997ed440) by Copilot).
- removed theme overrides ([1e66c26](https://github.com/mylonics/struct-frame/commit/1e66c2677c7edb17b696db78ff234050de26b34e) by Rijesh Augustine).
- Remove unused boilerplate code, consolidate to frame_parsers_gen files (#63) ([bbbe504](https://github.com/mylonics/struct-frame/commit/bbbe504ec38ce1c7a9c554f1d4a6c0a411c27a3c) by Copilot).
- Remove typed-struct dependency (#33) ([fc75162](https://github.com/mylonics/struct-frame/commit/fc75162ae47379fcf9b3b23f7bbedad949ac439e) by Copilot).
- Remove structured-classes from CI dependencies ([ec83663](https://github.com/mylonics/struct-frame/commit/ec83663a01f4186a052b9f944999985ea25bb12f) by copilot-swe-agent[bot]).
- Remove backup file and add .bak to gitignore ([041b7a4](https://github.com/mylonics/struct-frame/commit/041b7a4d29e4168e9c6ebfba57aaf73567ef7581) by copilot-swe-agent[bot]).

## [0.0.53](https://github.com/mylonics/struct-frame/releases/tag/0.0.53) - 2026-01-06

<small>[Compare with v0.0.51](https://github.com/mylonics/struct-frame/compare/v0.0.51...0.0.53)</small>

### Added

- Add generated profile-specific framers and parsers for all profiles (#136) ([064daa7](https://github.com/mylonics/struct-frame/commit/064daa7f95cd677c673e514736af762e439fe2d5) by Copilot).

## [v0.0.51](https://github.com/mylonics/struct-frame/releases/tag/v0.0.51) - 2026-01-06

<small>[Compare with first commit](https://github.com/mylonics/struct-frame/compare/9b9977bd29b2acb1bb1681df472b7400349172d2...v0.0.51)</small>

### Added

- Add automated release pipeline with version bumping and PyPI publishing (#130) ([f289a0c](https://github.com/mylonics/struct-frame/commit/f289a0c10519907a6cb82262d8e01d24f11af4bf) by Copilot).
- Add minimal frame parsing documentation, examples, and auto-generated helper functions (#123) ([a441990](https://github.com/mylonics/struct-frame/commit/a441990f914e9efc04a1d0ac9306e35c083b09dd) by Copilot).
- Add C++ buffer parsing API and comprehensive parser feature matrix (#118) ([3da509b](https://github.com/mylonics/struct-frame/commit/3da509baaa63afdd85736c289599ed3238bd3a48) by Copilot).
- Add Wireshark dissector for struct-frame protocols (#119) ([b9479ae](https://github.com/mylonics/struct-frame/commit/b9479ae12e9befc6813ef8217f9de30650db2868) by Copilot).
- Add inline frame format helpers to C# tests (#114) ([681cd81](https://github.com/mylonics/struct-frame/commit/681cd8159c365a73d5ec490547f867809b8a6e5f) by Copilot).
- Add polyglot parser for multi-frame-type streams (#103) ([6420666](https://github.com/mylonics/struct-frame/commit/6420666082a58259b04f209534f850735edcc669) by Copilot).
- Add intent-based framing profiles and interactive calculator to simplify frame format selection (#99) ([eab5b66](https://github.com/mylonics/struct-frame/commit/eab5b66bee186e404c45c7baf68740c039d2e81f) by Copilot).
- Add high-level SDK with transport abstraction for TypeScript, Python, C++, and C# (opt-in via flags) (#95) ([ddf3b74](https://github.com/mylonics/struct-frame/commit/ddf3b7490e4c92027e09f79ee1563880ceeefb1b) by Copilot).
- Added logo ([b301a31](https://github.com/mylonics/struct-frame/commit/b301a317376d47a70f0cf3251721e1fcff6d9a42) by Rijesh Augustine).
- Added C# tests ([65c7330](https://github.com/mylonics/struct-frame/commit/65c7330fb37a0341adb9200e86c3aefffe534f19) by Rijesh Augustine).
- Add C# language with tests (#73) ([cb5292a](https://github.com/mylonics/struct-frame/commit/cb5292a28442c0d856c8b21be93e27a9c21266b9) by Copilot).
- Add boilerplate code generator script and move frame_formats.proto to src (#61) ([c269bf2](https://github.com/mylonics/struct-frame/commit/c269bf29a699d3d88e55f5406aae96149c9ff633) by Copilot).
- Add separate BasicFrame and BasicFrameWithLen implementations for C and C++ (#52) ([2b4938c](https://github.com/mylonics/struct-frame/commit/2b4938cb6301eea8a4b4745a0603ac7348024d9a) by Copilot).
- Add frame format definitions proto file (#48) ([021f7fc](https://github.com/mylonics/struct-frame/commit/021f7fc6efd594edbd179ce8f270957c6f41cbe2) by Copilot).
- Add GitHub Actions workflow to automatically publish wiki on pushes to main (#44) ([9d08404](https://github.com/mylonics/struct-frame/commit/9d084048972736cb76a5dd619cf6a086eca8c70d) by Copilot).
- Add documentation wiki pages (#42) ([cc97976](https://github.com/mylonics/struct-frame/commit/cc979765589690408e52156a6100e1877dfe8b5f) by Copilot).
- Add JavaScript as a language target (#38) ([0340272](https://github.com/mylonics/struct-frame/commit/0340272719483556cbdcb7702384996566994d59) by Copilot).
- Add guard check for module availability in TS array test ([cb405cc](https://github.com/mylonics/struct-frame/commit/cb405cc5e8e449f92d97c92f61bbfebba84445fc) by copilot-swe-agent[bot]).
- Add encoder/decoder compilation for TypeScript pipe tests ([649aea5](https://github.com/mylonics/struct-frame/commit/649aea5c5ac16e4409e639903a3a8bfd9599ff1f) by copilot-swe-agent[bot]).
- Address code review comments: use constants and improve formatting ([cc9475c](https://github.com/mylonics/struct-frame/commit/cc9475c590621dd63e80b0305cd14d7ef019deb7) by copilot-swe-agent[bot]).
- Address code review feedback - improve comments and remove duplicate checks ([a80c781](https://github.com/mylonics/struct-frame/commit/a80c781de265bac718ce262eae7017f3bedeec03) by copilot-swe-agent[bot]).
- Add explicit permissions to GitHub Actions workflow for security ([f8ccc27](https://github.com/mylonics/struct-frame/commit/f8ccc27e7c856726f60828c913a96560cc2b3c13) by copilot-swe-agent[bot]).
- Add CI pipeline documentation to README ([8f7edbd](https://github.com/mylonics/struct-frame/commit/8f7edbd24e61196f9c04524deae5961dda310781) by copilot-swe-agent[bot]).
- Add GitHub Actions workflow for testing pipeline ([381c1af](https://github.com/mylonics/struct-frame/commit/381c1afbf049606785065fea9a02ce8c9372d96a) by copilot-swe-agent[bot]).
- Address code review feedback ([281551e](https://github.com/mylonics/struct-frame/commit/281551eedb515f2c56c1a535b3e1dc8d10639d60) by copilot-swe-agent[bot]).
- Add proper C++ test files following same pattern as C/TS/Python tests ([352b9bf](https://github.com/mylonics/struct-frame/commit/352b9bfbbaca441de0c63923b4e098394957d4d6) by copilot-swe-agent[bot]).
- Add implementation summary and finalize cross-platform tests ([35c06c4](https://github.com/mylonics/struct-frame/commit/35c06c4964106bdad92d815e34fe1be3366b57cb) by copilot-swe-agent[bot]).
- Address code review feedback and improve cross-platform test ([3f5be2c](https://github.com/mylonics/struct-frame/commit/3f5be2c7d930cb4f4968a7fdab41ad66dc011ebe) by copilot-swe-agent[bot]).
- Add cross-platform pipe test with C encoder/decoder ([4c0f86c](https://github.com/mylonics/struct-frame/commit/4c0f86c0f2736676b24936a1d6525735a7822831) by copilot-swe-agent[bot]).
- Add C++ code generation with enum classes and modern C++ style ([fe671ee](https://github.com/mylonics/struct-frame/commit/fe671eecb2899a871b94595d05b66ee706bdb999) by copilot-swe-agent[bot]).
- Add comprehensive C++ documentation to README ([b847f18](https://github.com/mylonics/struct-frame/commit/b847f182dbdefe7d231d598735bd7c17611aeaef) by copilot-swe-agent[bot]).
- Add C++ code generator with enum classes and boilerplate files ([04dd66b](https://github.com/mylonics/struct-frame/commit/04dd66bc3960c32542069d93dd55aaadd695a821) by copilot-swe-agent[bot]).
- Added details on message framinig ([3637b8c](https://github.com/mylonics/struct-frame/commit/3637b8c29abb3795e370ec8287be9ef485d805ca) by Rijesh Augustine).
- Added flatten keyword ([9a8ea2c](https://github.com/mylonics/struct-frame/commit/9a8ea2c5102b253cf4896059d042189791f48058) by Rijesh Augustine).
- Added graphql schema generator ([2076d92](https://github.com/mylonics/struct-frame/commit/2076d928b3b4aa778dfe5fd1446d330876b8111e) by Rijesh Augustine).
- Added python to dict methods ([bae7220](https://github.com/mylonics/struct-frame/commit/bae7220972efb96318f67352624e26ffc97281dd) by Rijesh Augustine).
- Add comprehensive GitHub Copilot instructions ([d89e963](https://github.com/mylonics/struct-frame/commit/d89e9636892d4c438107af63955c9239731cc4d7) by copilot-swe-agent[bot]).
- Added custom printing of python messages ([5bcf582](https://github.com/mylonics/struct-frame/commit/5bcf58252dfe04f8ed6ba7ae5d89dd2a26feeb80) by Rijesh Augustine).
- Added prototype python parser ([db0a265](https://github.com/mylonics/struct-frame/commit/db0a26585f019314adfffab1e0d0d4db5c1311d8) by Rijesh Augustine).
- Added clang-format file ([4917cf1](https://github.com/mylonics/struct-frame/commit/4917cf18167ad0799d2794c12b2e7a32d8bae641) by Rijesh Augustine).
- Added start of new generator ([b3cdf77](https://github.com/mylonics/struct-frame/commit/b3cdf77df52a1243fe3a27aac3acec419eb56dfc) by Rijesh Augustine).

### Fixed

- Fix multi-message serialization/deserialization across C, C++, Python, JavaScript, TypeScript, and C# (#125) ([62e330c](https://github.com/mylonics/struct-frame/commit/62e330c676fb06f62e4add73f984d978eaba7f4e) by Copilot).
- Fix documentation to use correct module name and prioritize pip installation (#91) ([1c400ca](https://github.com/mylonics/struct-frame/commit/1c400ca7e9e65971605a3b82efe820a2f1e82da0) by Copilot).
- fixed docs deploy (#86) ([b49eb9a](https://github.com/mylonics/struct-frame/commit/b49eb9a4a0521f79dfd7c8297bed3211a8266fa1) by Rijesh Augustine).
- Fix docs build by quoting pip install version constraints (#83) ([427acd9](https://github.com/mylonics/struct-frame/commit/427acd952c5712c141cd01eb42170eeec9286bad) by Copilot).
- Fix documentation deployment workflow error (#79) ([70ec0f8](https://github.com/mylonics/struct-frame/commit/70ec0f872c54e9ec3f24829bbdfcc1bed3e40ab1) by Copilot).
- Fixed test reporting issues ([09b177f](https://github.com/mylonics/struct-frame/commit/09b177fe905f3e3dcfb068458e86219cbaafc0ab) by Rijesh Augustine).
- Fixed c# tests ([ce7fe42](https://github.com/mylonics/struct-frame/commit/ce7fe42b07f2c056e552546d83bb55bad88abe10) by Rijesh Augustine).
- Fix Publish Wiki workflow by using clone strategy with preprocess (#49) ([99bd87f](https://github.com/mylonics/struct-frame/commit/99bd87f6152df2cea0b657f265615f28728da117) by Copilot).
- Fix Publish Wiki workflow configuration (#46) ([9a85797](https://github.com/mylonics/struct-frame/commit/9a857979567e22d867e5759114da75658611a9f0) by Copilot).
- Fix TypeScript cross-platform deserialization test path (#35) ([85c79e9](https://github.com/mylonics/struct-frame/commit/85c79e97d7786a7381485773093a6c8d357ea9fd) by Copilot).
- fixed tests ([f89a0ad](https://github.com/mylonics/struct-frame/commit/f89a0ad43fc4b732ea4ce905bf31007d1b50ea3c) by Rijesh Augustine).
- Fix TypeScript test working directory inconsistency (#28) ([a49985d](https://github.com/mylonics/struct-frame/commit/a49985d4743c6a1a830a180094a71c7f60077056) by Copilot).
- Fixed upload issue ([f9dd3be](https://github.com/mylonics/struct-frame/commit/f9dd3be07dcdbbff831775dd096fec49aedf87fd) by Rijesh Augustine).
- Fix TypeScript test execution path in run_test_by_type ([5c5ff46](https://github.com/mylonics/struct-frame/commit/5c5ff464886c4ac629bef8a0af71f25f8cb69fc5) by copilot-swe-agent[bot]).
- Fix TypeScript enum handling and struct array naming ([3619892](https://github.com/mylonics/struct-frame/commit/3619892fc42c36490701840662195779d7a41794) by copilot-swe-agent[bot]).
- Fix TypeScript array generation and skip basic_types test due to typed-struct library bug ([b4ab68f](https://github.com/mylonics/struct-frame/commit/b4ab68f8fc898f2f8917cda3c4b373de07dbe9b1) by copilot-swe-agent[bot]).
- Fix TypeScript compilation errors - Buffer.from API and int64/uint64 type swap ([f9e126d](https://github.com/mylonics/struct-frame/commit/f9e126d1597a558d8e474ff2393fcb0d286f71d5) by copilot-swe-agent[bot]).
- Fix Python cross-language compatibility tests ([751f6af](https://github.com/mylonics/struct-frame/commit/751f6afb82501c40e45eede0a21a8dede74abcde) by copilot-swe-agent[bot]).
- Fix code review issues and re-enable Python cross-platform tests ([941a56b](https://github.com/mylonics/struct-frame/commit/941a56b272e9cad86ae847642dfb0f07666de740) by copilot-swe-agent[bot]).
- Fix handling of fixed arrays of nested messages ([e2c9719](https://github.com/mylonics/struct-frame/commit/e2c971944031328ed92bb207978650f5232a7e31) by copilot-swe-agent[bot]).
- fixing some test issues ([5f5e53b](https://github.com/mylonics/struct-frame/commit/5f5e53b3d11d4233d7dcae28a98f152b69312a0a) by Rijesh Augustine).
- Fix variable-size strings and add C++ to cross-platform tests ([dabcee3](https://github.com/mylonics/struct-frame/commit/dabcee306039b162798a745fb305825f56b9a90a) by copilot-swe-agent[bot]).
- Fix Python array generation with proper structured library syntax ([195f914](https://github.com/mylonics/struct-frame/commit/195f9145a0d37e8cf197bcf783518d6e82dafdcb) by copilot-swe-agent[bot]).
- fixing some cpp issues ([35623bd](https://github.com/mylonics/struct-frame/commit/35623bdd63db6d5ad9972812ad58ff7f449c1641) by Rijesh Augustine).
- Fix comment about empty structs in C++ generator ([2e62fbf](https://github.com/mylonics/struct-frame/commit/2e62fbf40504744b02c03e1964944114231bed52) by copilot-swe-agent[bot]).
- Fixed cpp array test ([b45e352](https://github.com/mylonics/struct-frame/commit/b45e352557862490ca86269e239119d0df230bdb) by Rijesh Augustine).
- fixed debug validate ([f10c2a4](https://github.com/mylonics/struct-frame/commit/f10c2a4c6122552ab2036a73ddf3969f533e57cf) by Rijesh Augustine).

### Changed

- Changes before error encountered ([8b7cf2c](https://github.com/mylonics/struct-frame/commit/8b7cf2c00cbe845a8558d35a185d9d790ae0a320) by copilot-swe-agent[bot]).
- Changes ready for testing ([7e90204](https://github.com/mylonics/struct-frame/commit/7e902043f8e70300bea4513134eb5294584ac84f) by Rijesh Augustine).

### Removed

- Remove legacy code and deprecated features (#131) ([894f1f5](https://github.com/mylonics/struct-frame/commit/894f1f58ddd19a96e1b00317a418c715286586f3) by Copilot).
- Remove hardcoded test values and implement mixed message type testing (all 6 languages complete) (#128) ([1d5ea0c](https://github.com/mylonics/struct-frame/commit/1d5ea0cf386519661f284806f2f5a2c09b523001) by Copilot).
- Remove legacy compatibility layers and deprecated code (#112) ([31145bc](https://github.com/mylonics/struct-frame/commit/31145bce1ccb580300dcfccce9f279b6997ed440) by Copilot).
- removed theme overrides ([1e66c26](https://github.com/mylonics/struct-frame/commit/1e66c2677c7edb17b696db78ff234050de26b34e) by Rijesh Augustine).
- Remove unused boilerplate code, consolidate to frame_parsers_gen files (#63) ([bbbe504](https://github.com/mylonics/struct-frame/commit/bbbe504ec38ce1c7a9c554f1d4a6c0a411c27a3c) by Copilot).
- Remove typed-struct dependency (#33) ([fc75162](https://github.com/mylonics/struct-frame/commit/fc75162ae47379fcf9b3b23f7bbedad949ac439e) by Copilot).
- Remove structured-classes from CI dependencies ([ec83663](https://github.com/mylonics/struct-frame/commit/ec83663a01f4186a052b9f944999985ea25bb12f) by copilot-swe-agent[bot]).
- Remove backup file and add .bak to gitignore ([041b7a4](https://github.com/mylonics/struct-frame/commit/041b7a4d29e4168e9c6ebfba57aaf73567ef7581) by copilot-swe-agent[bot]).
