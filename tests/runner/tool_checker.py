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

        for lang_id in self.config['language_ids']:
            lang = self.get_lang(lang_id)
            if not lang or not lang.enabled:
                continue

            # Use the Language class's check_tools() method
            info = lang.check_tools()
            results[lang_id] = info

        return results

    def print_tool_availability(self) -> bool:
        """Print a summary of available tools and return True if all tools available."""
        from .output_formatter import OutputFormatter
        formatter = OutputFormatter(
            self.config, self.project_root, self.verbose, self.verbose_failure)
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
