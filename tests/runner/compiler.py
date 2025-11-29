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

        compiled = [l for l in self.get_active_languages()
                    if self.config['languages'][l].get('compilation', {}).get('enabled')]

        if not compiled:
            print("  No languages require compilation")
            return True

        for lang_id in compiled:
            self._compile_language(lang_id)

        formatter.print_lang_results(compiled, self.results)
        return all(self.results.get(l, False) for l in compiled)

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

        # Compile test files from all suites
        for suite in self.config['test_suites']:
            test_name = suite.get('test_name')
            if not test_name:
                continue

            test_files = self.get_test_files(lang_id, test_name)
            if 'executable' in test_files:
                source = test_dir / test_files['source_file']
                output = build_dir / test_files['executable']
                if source.exists():
                    if not self._compile_file(lang_id, source, output, gen_dir):
                        all_success = False

        # TypeScript special handling
        if lang_id == 'ts' and comp.get('command'):
            # Copy test files to generated directory
            for ts_file in test_dir.glob("*.ts"):
                shutil.copy2(ts_file, gen_dir / ts_file.name)

            # Create tsconfig.json in generated dir to resolve modules from tests/ts/node_modules
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
                    "include": ["./*.ts"]
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
