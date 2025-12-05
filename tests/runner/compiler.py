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
        for lang_id in self.config['languages']:
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
                    if self.config['languages'][l].get('compilation', {}).get('enabled')]

        if not compiled:
            print("  No languages require compilation")
            return True

        for lang_id in compiled:
            self._compile_language(lang_id)

        formatter.print_lang_results(compiled, self.results)
        return all(self.results.get(l, False) for l in compiled)

    def _copy_js_test_files(self):
        """Copy JavaScript test files to the generated JS directory."""
        if 'js' not in self.config['languages']:
            return

        lang_config = self.config['languages']['js']
        if not lang_config.get('enabled', True):
            return

        test_dir = self.project_root / lang_config['test_dir']
        execution = lang_config.get('execution', {})
        script_dir_path = execution.get('script_dir')

        if script_dir_path:
            script_dir = self.project_root / script_dir_path
            script_dir.mkdir(parents=True, exist_ok=True)
            for filename in ['test_runner.js', 'test_codec.js']:
                source_file = test_dir / filename
                if source_file.exists():
                    shutil.copy2(source_file, script_dir / filename)

    def _compile_language(self, lang_id: str) -> bool:
        """Compile code for a specific language"""
        lang_config = self.config['languages'][lang_id]
        comp = lang_config.get('compilation', {})

        # Check compiler availability
        if comp.get('compiler_check'):
            # Use working_dir if specified
            working_dir = None
            if comp.get('working_dir'):
                working_dir = self.project_root / comp['working_dir']
            if not self.run_command(comp['compiler_check'], cwd=working_dir)[0]:
                self.log(
                    f"{lang_config['name']} compiler not found - skipping", "WARNING")
                return True

        test_dir = self.project_root / lang_config['test_dir']
        build_dir = self.project_root / \
            lang_config.get('build_dir', lang_config['test_dir'])
        gen_dir = self.project_root / \
            lang_config['code_generation']['output_dir']
        all_success = True

        # Ensure build directory exists
        build_dir.mkdir(parents=True, exist_ok=True)

        # Compile the unified test_runner with test_codec for C/C++
        source_ext = comp.get('source_extension', '')
        exe_ext = comp.get('executable_extension', '')

        if exe_ext and source_ext in ['.c', '.cpp']:
            # For C: compile test_runner.c with test_codec.c
            # For C++: compile test_runner.cpp with test_codec.cpp
            runner_source = test_dir / f"test_runner{source_ext}"
            codec_source = test_dir / f"test_codec{source_ext}"
            runner_output = build_dir / f"test_runner{exe_ext}"

            if runner_source.exists() and codec_source.exists():
                if not self._compile_multi_source(lang_id, [runner_source, codec_source],
                                                  runner_output, gen_dir):
                    all_success = False

        # Special handling for languages with 'command' (project-based compilation like TypeScript)
        # These languages copy test files to generated dir and run a project-level compile command
        source_ext = comp.get('source_extension', '')
        if comp.get('command') and source_ext:
            # Copy test files to generated directory
            for source_file in test_dir.glob(f"*{source_ext}"):
                shutil.copy2(source_file, gen_dir / source_file.name)

            # Create tsconfig.json in generated dir for TypeScript projects
            # This is needed to resolve modules from tests dir node_modules
            if source_ext == '.ts':
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

            output_dir = self.project_root / comp['output_dir']
            cmd = comp['command'].format(
                output_dir=output_dir, generated_dir=gen_dir)

            # Use working_dir if specified (for running npm/npx from tests dir)
            working_dir = None
            if comp.get('working_dir'):
                working_dir = str(self.project_root / comp['working_dir'])
            all_success = self.run_command(cmd, cwd=working_dir)[
                0] and all_success

        self.results[lang_id] = all_success
        return all_success

    def _compile_file(self, lang_id: str, source: Path, output: Path, gen_dir: Path) -> bool:
        """Compile a single source file"""
        if not source.exists():
            return False
        comp = self.config['languages'][lang_id]['compilation']
        flags = [f.replace('{generated_dir}', str(gen_dir))
                  .replace('{output}', str(output))
                  .replace('{source}', str(source)) for f in comp.get('flags', [])]
        return self.run_command(f"{comp['compiler']} {' '.join(flags)}")[0]

    def _compile_multi_source(self, lang_id: str, sources: List[Path], output: Path,
                              gen_dir: Path) -> bool:
        """Compile multiple source files into a single executable"""
        for source in sources:
            if not source.exists():
                return False
        comp = self.config['languages'][lang_id]['compilation']

        # Build flags, replacing {source} with all source files
        sources_str = ' '.join(f'"{s}"' for s in sources)
        flags = []
        for f in comp.get('flags', []):
            f = f.replace('{generated_dir}', str(gen_dir))
            f = f.replace('{output}', str(output))
            if '{source}' in f:
                # Replace {source} with all sources
                f = sources_str
            flags.append(f)

        cmd = f"{comp['compiler']} {' '.join(flags)}"
        return self.run_command(cmd)[0]
