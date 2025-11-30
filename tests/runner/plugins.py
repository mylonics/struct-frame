"""
Test plugins for custom test execution behavior.

Plugins allow tests to define their own execution and output logic.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .test_executor import TestExecutor
    from .output_formatter import OutputFormatter


class TestPlugin(ABC):
    """Base class for test plugins that provide custom execution behavior."""

    # Plugin type identifier - must match 'plugin' field in test_config.json
    plugin_type: str = ""

    def __init__(self, executor: 'TestExecutor', formatter: 'OutputFormatter'):
        self.executor = executor
        self.formatter = formatter
        self.config = executor.config
        self.project_root = executor.project_root
        self.verbose = executor.verbose

    @abstractmethod
    def run(self, suite: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the test suite with custom logic.

        Args:
            suite: The test suite configuration from test_config.json

        Returns:
            Dict containing results. Structure depends on plugin type.
            Standard plugins should return {'results': {lang_id: {test_name: bool}}}
        """
        pass

    def log(self, message: str, level: str = "INFO"):
        """Log a message"""
        self.executor.log(message, level)


class StandardTestPlugin(TestPlugin):
    """Default plugin for standard test suites - runs test per language."""

    plugin_type = "standard"

    def run(self, suite: Dict[str, Any]) -> Dict[str, Any]:
        print(f"\n[TEST] {suite['description']}")

        results = {}
        output_files = {}

        for lang_id in self.executor.get_testable_languages():
            test_config = self.executor.build_test_config(lang_id, suite)
            if not test_config:
                continue

            result = self.executor.run_test_script(lang_id, test_config)
            results[lang_id] = result

            # Track output files if this suite produces them
            if result and 'output_file' in suite:
                output_path = self._get_output_dir(lang_id) / \
                    self._get_output_file_name(suite, lang_id)
                if output_path.exists():
                    output_files[lang_id] = output_path

        self.formatter.print_lang_results(
            self.executor.get_testable_languages(), results)

        return {
            'results': {lang_id: {suite['name']: r} for lang_id, r in results.items()},
            'output_files': output_files
        }

    def _get_output_dir(self, lang_id: str) -> Path:
        """Get the output directory for a language (build_dir for binaries)"""
        lang_config = self.config['languages'][lang_id]
        if lang_id == 'ts':
            return self.project_root / lang_config['execution'].get('script_dir', '')
        # JavaScript also uses script_dir for output
        if lang_id == 'js' and 'execution' in lang_config:
            script_dir = lang_config['execution'].get('script_dir')
            if script_dir:
                return self.project_root / script_dir
        # Use build_dir for output files
        return self.project_root / lang_config.get('build_dir', lang_config['test_dir'])

    def _get_output_file_name(self, suite: Dict[str, Any], lang_id: str) -> str:
        """Get the output file name for a language"""
        lang_config = self.config['languages'][lang_id]
        # Use file_prefix if specified, otherwise lowercase display name
        file_prefix = lang_config.get(
            'file_prefix', lang_config['name'].lower())
        pattern = suite.get('output_file', '{lang_name}_output.bin')
        return pattern.replace('{lang_name}', file_prefix)


class CrossPlatformMatrixPlugin(TestPlugin):
    """
    Plugin for cross-platform compatibility testing.

    Runs a decoder test against output files from a linked encoder suite,
    using C as the base language. Tests:
    - C serialization decoded by all languages
    - All language serializations decoded by C
    """

    plugin_type = "cross_platform_matrix"

    def run(self, suite: Dict[str, Any]) -> Dict[str, Any]:
        self.formatter.print_section("CROSS-PLATFORM COMPATIBILITY")
        print(f"[TEST] {suite['description']}")

        # Get encoded files from the linked suite
        input_suite = suite.get('input_from')
        if not input_suite:
            self.log(
                "cross_platform_matrix plugin requires 'input_from' field", "ERROR")
            return {'results': {}, 'matrix': {}}

        encoded_files = self.executor.get_output_files(input_suite)

        testable = self.executor.get_testable_languages()
        matrix = {}
        results = {lang_id: {} for lang_id in testable}

        # Use C as the base language for cross-platform testing
        base_lang = 'c'
        if base_lang not in testable:
            self.log(
                f"Base language '{base_lang}' is not available for testing", "ERROR")
            return {'results': {}, 'matrix': {}}

        # Test all encoders against C decoder, and C encoder against all decoders
        for enc_lang in testable:
            enc_name = self.config['languages'][enc_lang]['name']
            matrix[enc_name] = {}

            # Check if this encoder produced a file
            data_file = encoded_files.get(enc_lang)

            for dec_lang in testable:
                dec_name = self.config['languages'][dec_lang]['name']

                # Only test: C encodes → all decode, OR all encode → C decodes
                if enc_lang != base_lang and dec_lang != base_lang:
                    # Skip non-C to non-C combinations
                    matrix[enc_name][dec_name] = None
                    continue

                # If encoder didn't produce a file, mark as N/A
                if data_file is None:
                    matrix[enc_name][dec_name] = None
                    result_key = f"{suite['name']}_{enc_lang}"
                    results[dec_lang][result_key] = False
                    continue

                decode_config = self.executor.build_test_config(
                    dec_lang, suite)
                if not decode_config:
                    matrix[enc_name][dec_name] = None
                    continue

                result = self._run_decoder_with_file(
                    dec_lang, decode_config, data_file)
                matrix[enc_name][dec_name] = result

                # Track individual results
                result_key = f"{suite['name']}_{enc_lang}"
                results[dec_lang][result_key] = result

        self.formatter.print_compatibility_matrix(matrix)

        return {
            'results': results,
            'matrix': matrix
        }

    def _run_decoder_with_file(self, lang_id: str, test_config: Dict[str, Any],
                               data_file: Path) -> bool:
        """Run a decoder test with a specific input file"""
        lang_config = self.config['languages'][lang_id]
        build_dir = self.project_root / \
            lang_config.get('build_dir', lang_config['test_dir'])
        target_file = build_dir / data_file.name

        # Ensure build directory exists
        build_dir.mkdir(parents=True, exist_ok=True)

        try:
            with self.executor.temp_copy(data_file, target_file):
                # TypeScript needs file in JS directory too
                if lang_id == 'ts' and 'compiled_file' in test_config:
                    script_dir = self.project_root / \
                        lang_config['execution'].get('script_dir', '')
                    ts_target = script_dir / data_file.name
                    with self.executor.temp_copy(data_file, ts_target):
                        return self.executor.run_test_script(
                            lang_id, test_config, args=data_file.name)
                # JavaScript also needs file in script_dir
                elif lang_id == 'js' and 'script_dir' in lang_config.get('execution', {}):
                    script_dir = self.project_root / \
                        lang_config['execution'].get('script_dir', '')
                    js_target = script_dir / data_file.name
                    with self.executor.temp_copy(data_file, js_target):
                        return self.executor.run_test_script(
                            lang_id, test_config, args=data_file.name)
                else:
                    return self.executor.run_test_script(
                        lang_id, test_config, args=target_file.name)
        except Exception as e:
            if self.verbose:
                self.log(f"Decode failed: {e}", "WARNING")
            return False


# Registry of available plugins
PLUGIN_REGISTRY: Dict[str, type] = {
    'standard': StandardTestPlugin,
    'cross_platform_matrix': CrossPlatformMatrixPlugin,
}


def get_plugin(plugin_type: str, executor: 'TestExecutor',
               formatter: 'OutputFormatter') -> TestPlugin:
    """Get a plugin instance by type."""
    plugin_class = PLUGIN_REGISTRY.get(plugin_type, StandardTestPlugin)
    return plugin_class(executor, formatter)


def register_plugin(plugin_class: type):
    """Register a custom plugin class."""
    PLUGIN_REGISTRY[plugin_class.plugin_type] = plugin_class
