"""
Tool availability checking for the test runner.

Checks which compilers/interpreters are available for each language.
"""

from pathlib import Path
from typing import Any, Dict, List

from .base import TestRunnerBase


class ToolChecker(TestRunnerBase):
    """Checks availability of compilers and interpreters for each language"""

    def check_tool_availability(self) -> Dict[str, Dict[str, Any]]:
        """Check which compilers/interpreters are available for each language.

        Returns a dict mapping lang_id to availability info:
        {
            'lang_id': {
                'name': 'Language Name',
                'available': True/False,
                'compiler': {'name': 'gcc', 'available': True, 'version': '...'},
                'interpreter': {'name': 'python', 'available': True, 'version': '...'},
                'reason': 'why unavailable' (only if not available)
            }
        }
        """
        results = {}

        for lang_id, lang_config in self.config['languages'].items():
            if not lang_config.get('enabled', True):
                continue

            info = {
                'name': lang_config['name'],
                'available': True,
                'compiler': None,
                'interpreter': None,
            }

            # Generation-only languages don't need tools checked
            if lang_config.get('generation_only'):
                info['generation_only'] = True
                results[lang_id] = info
                continue

            # Check compiler if compilation is enabled
            info = self._check_compiler(lang_config, info)

            # Check interpreter if execution config exists
            info = self._check_interpreter(lang_config, info)

            results[lang_id] = info

        return results

    def _check_compiler(self, lang_config: Dict[str, Any], info: Dict[str, Any]) -> Dict[str, Any]:
        """Check compiler availability for a language"""
        comp = lang_config.get('compilation', {})
        if not comp.get('enabled'):
            return info

        compiler = comp.get('compiler', '')
        check_cmd = comp.get('compiler_check', f"{compiler} --version")

        # Use working_dir if specified (for npm/npx commands)
        working_dir = None
        if comp.get('working_dir'):
            working_dir = self.project_root / comp['working_dir']

        success, stdout, stderr = self.run_command(
            check_cmd, cwd=working_dir, timeout=5)

        version = ""
        if success:
            output = stdout or stderr
            version = output.strip().split('\n')[0] if output else ""

        info['compiler'] = {
            'name': compiler,
            'available': success,
            'version': version
        }

        if not success:
            info['available'] = False
            info['reason'] = f"Compiler '{compiler}' not found"

        return info

    def _check_interpreter(self, lang_config: Dict[str, Any], info: Dict[str, Any]) -> Dict[str, Any]:
        """Check interpreter availability for a language"""
        execution = lang_config.get('execution', {})
        if not execution.get('interpreter'):
            return info

        interpreter = execution['interpreter']
        success, stdout, stderr = self.run_command(
            f"{interpreter} --version", timeout=5)

        version = ""
        if success:
            output = stdout or stderr
            version = output.strip().split('\n')[0] if output else ""

        info['interpreter'] = {
            'name': interpreter,
            'available': success,
            'version': version
        }

        if not success:
            info['available'] = False
            info['reason'] = f"Interpreter '{interpreter}' not found"

        return info

    def print_tool_availability(self) -> bool:
        """Print a summary of available tools and return True if all tools available."""
        from .output_formatter import OutputFormatter
        formatter = OutputFormatter(
            self.config, self.project_root, self.verbose)
        formatter.print_section("TOOL AVAILABILITY CHECK")

        availability = self.check_tool_availability()
        all_available = True

        for lang_id, info in availability.items():
            status = "[OK]" if info['available'] else "[FAIL]"
            print(f"\n  {status} {info['name']}")

            # Generation-only languages just show that status
            if info.get('generation_only'):
                print(f"      (generation only)")
                continue

            if info['compiler']:
                comp = info['compiler']
                comp_status = "[OK]" if comp['available'] else "[FAIL]"
                version_str = f" ({comp['version']})" if comp['version'] else ""
                print(
                    f"      Compiler:    {comp_status} {comp['name']}{version_str}")

            if info['interpreter']:
                interp = info['interpreter']
                interp_status = "[OK]" if interp['available'] else "[FAIL]"
                version_str = f" ({interp['version']})" if interp['version'] else ""
                print(
                    f"      Interpreter: {interp_status} {interp['name']}{version_str}")

            if not info['available']:
                all_available = False
                print(f"      [WARN] {info.get('reason', 'Unknown issue')}")

        print()
        return all_available

    def get_available_languages(self) -> List[str]:
        """Get list of languages that have all required tools available."""
        availability = self.check_tool_availability()
        return [lang_id for lang_id, info in availability.items()
                if info['available'] and lang_id not in self.skipped_languages]
