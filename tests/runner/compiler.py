"""
Compilation functionality for the test runner.

Handles compiling code for languages that require compilation (C, C++, TypeScript).
"""

import shutil
from pathlib import Path
from typing import Any, Dict, List

from .base import TestRunnerBase


class Compiler(TestRunnerBase):
    """Handles compilation of generated code"""

    def __init__(self, config: Dict[str, Any], project_root: Path, verbose: bool = False,
                 verbose_failure: bool = False):
        super().__init__(config, project_root, verbose, verbose_failure)
        self.results: Dict[str, bool] = {}
        for lang_id in self.config['language_ids']:
            self.results[lang_id] = False

    def compile_all(self) -> bool:
        """Compile code for all languages that require compilation"""
        from .output_formatter import OutputFormatter
        formatter = OutputFormatter(
            self.config, self.project_root, self.verbose, self.verbose_failure)
        formatter.print_section("COMPILATION (all test files)")

        # Copy JS test files first (no compilation needed but files must be in place)
        self._copy_js_test_files()

        compiled = [l for l in self.get_active_languages()
                    if self.get_lang(l) and self.get_lang(l).compiler]

        if not compiled:
            print("  No languages require compilation")
            return True

        for lang_id in compiled:
            self._compile_language(lang_id)

        formatter.print_lang_results(compiled, self.results)
        return all(self.results.get(l, False) for l in compiled)

    def _copy_js_test_files(self):
        """Copy JavaScript test files to the generated JS directory."""
        lang = self.get_lang('js')
        if not lang or not lang.enabled:
            return

        test_dir = lang.get_test_dir()
        script_dir = lang.get_script_dir()

        if script_dir:
            script_dir.mkdir(parents=True, exist_ok=True)
            for filename in ['test_runner.js', 'test_codec.js']:
                source_file = test_dir / filename
                if source_file.exists():
                    shutil.copy2(source_file, script_dir / filename)

    def _compile_language(self, lang_id: str) -> bool:
        """Compile code for a specific language"""
        lang = self.get_lang(lang_id)
        if not lang:
            return False

        # Check compiler availability using Language's check_compiler method
        compiler_info = lang.check_compiler()
        if not compiler_info['available']:
            self.log(f"{lang.name} compiler not found - skipping", "WARNING")
            return True

        test_dir = lang.get_test_dir()
        build_dir = lang.get_build_dir()
        gen_dir = lang.get_gen_dir()
        all_success = True

        # Ensure build directory exists
        build_dir.mkdir(parents=True, exist_ok=True)

        # Compile the unified test_runner with test_codec for C/C++
        source_ext = lang.source_extension
        exe_ext = lang.executable_extension

        if exe_ext and source_ext in ['.c', '.cpp']:
            # For C: compile test_runner.c with test_codec.c
            # For C++: compile test_runner.cpp with test_codec.cpp
            runner_source = test_dir / f"test_runner{source_ext}"
            codec_source = test_dir / f"test_codec{source_ext}"
            runner_output = build_dir / f"test_runner{exe_ext}"

            if runner_source.exists() and codec_source.exists():
                if not lang.compile([runner_source, codec_source], runner_output, gen_dir):
                    all_success = False

        # Special handling for languages with compile_command (project-based compilation like TypeScript, C#)
        if lang.compile_command and source_ext:
            # Copy test files to generated directory (for TypeScript)
            if source_ext == '.ts':
                for source_file in test_dir.glob(f"*{source_ext}"):
                    shutil.copy2(source_file, gen_dir / source_file.name)

                # Create tsconfig.json in generated dir for TypeScript projects
                tsconfig_path = gen_dir / 'tsconfig.json'
                if not tsconfig_path.exists():
                    import json
                    tsconfig = {
                        "extends": "../../ts/tsconfig.json",
                        "compilerOptions": {
                            "rootDir": ".",
                            "outDir": "./js",
                            "baseUrl": "../../ts",
                            "paths": {
                                "typed-struct": ["node_modules/typed-struct"],
                                "*": ["node_modules/*", "node_modules/@types/*"]
                            },
                            "types": ["node"],
                            "typeRoots": ["../../ts/node_modules/@types"]
                        },
                        "include": [f"./*{source_ext}"]
                    }
                    tsconfig_path.write_text(json.dumps(tsconfig, indent=2))

            # Use the Language's compile_project method
            if not lang.compile_project(test_dir, build_dir, gen_dir):
                all_success = False

        self.results[lang_id] = all_success
        return all_success
