"""
Test execution functionality for the test runner.

Handles running test suites using a plugin system for custom test behavior.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import TestRunnerBase


class TestExecutor(TestRunnerBase):
    """Handles execution of test suites using plugins for custom behavior."""

    def __init__(self, config: Dict[str, Any], project_root: Path, verbose: bool = False):
        super().__init__(config, project_root, verbose)
        self.results: Dict[str, Dict[str, bool]] = {}
        for lang_id in self.config['languages']:
            self.results[lang_id] = {}
        self.cross_platform_results: Dict[str, Dict[str, bool]] = {}
        # Store output files from suites for other suites to consume
        self._output_files: Dict[str, Dict[str, Path]] = {}

    def get_output_files(self, suite_name: str) -> Dict[str, Path]:
        """Get output files produced by a suite (for use by plugins)."""
        return self._output_files.get(suite_name, {})

    def store_output_files(self, suite_name: str, files: Dict[str, Path]):
        """Store output files from a suite (for use by plugins)."""
        self._output_files[suite_name] = files

    def run_test_suites(self):
        """Run all test suites using appropriate plugins."""
        from .output_formatter import OutputFormatter
        from .plugins import get_plugin

        formatter = OutputFormatter(
            self.config, self.project_root, self.verbose)

        formatter.print_section("TEST EXECUTION")

        for suite in self.config['test_suites']:
            # Determine plugin type - default to 'standard',
            # auto-detect 'cross_platform_matrix' if 'input_from' is present
            plugin_type = suite.get('plugin', 'standard')
            if 'input_from' in suite and plugin_type == 'standard':
                plugin_type = 'cross_platform_matrix'

            # Get and run the plugin
            plugin = get_plugin(plugin_type, self, formatter)
            result = plugin.run(suite)

            # Merge results
            for lang_id, lang_results in result.get('results', {}).items():
                self.results[lang_id].update(lang_results)

            # Store output files if produced
            if result.get('output_files'):
                self.store_output_files(suite['name'], result['output_files'])

            # Store cross-platform matrix if produced
            if result.get('matrix'):
                self.cross_platform_results = result['matrix']

    def run_cross_platform_tests(self) -> bool:
        """Check if cross-platform tests passed (called from runner for summary)."""
        # Cross-platform tests are now run as part of run_test_suites via plugins
        return sum(sum(d.values()) for d in self.cross_platform_results.values()) > 0
