"""
Code generation functionality for the test runner.

Handles generating code from proto files for all enabled languages.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List

from .base import TestRunnerBase


class CodeGenerator(TestRunnerBase):
    """Handles code generation from proto files"""

    def __init__(self, config: Dict[str, Any], project_root: Path, verbose: bool = False,
                 verbose_failure: bool = False):
        super().__init__(config, project_root, verbose, verbose_failure)
        self.results: Dict[str, bool] = {}
        for lang_id in self.config['language_ids']:
            self.results[lang_id] = False

    def generate_code(self) -> bool:
        """Generate code for all proto files and enabled languages"""
        from .output_formatter import OutputFormatter
        formatter = OutputFormatter(
            self.config, self.project_root, self.verbose, self.verbose_failure)
        formatter.print_section("CODE GENERATION")

        active = self.get_active_languages()
        all_success = True

        for proto_file in self.config.get('proto_files', []):
            proto_path = self.tests_dir / "proto" / proto_file
            if not proto_path.exists():
                self.log(f"Proto file not found: {proto_file}", "WARNING")
                continue

            # Build generation command
            cmd_parts = [sys.executable, "-m", "struct_frame", str(proto_path)]
            for lang_id in active:
                lang = self.get_lang(lang_id)
                if lang:
                    cmd_parts += [lang.gen_flag, lang.gen_output_path_flag,
                                  str(self.project_root / lang.gen_output_dir)]

            env = {"PYTHONPATH": str(self.project_root / "src")}
            success, _, _ = self.run_command(" ".join(cmd_parts), env=env)

            if success:
                for lang_id in active:
                    self.results[lang_id] = True
            else:
                self.log(f"Code generation failed for {proto_file}", "ERROR")
                all_success = False

        formatter.print_lang_results(active, self.results)
        return all_success
