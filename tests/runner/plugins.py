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
        # Check if this suite should skip display (results shown elsewhere)
        skip_display = suite.get('skip_display', False)

        if not skip_display:
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

        if not skip_display:
            self.formatter.print_lang_results(
                self.executor.get_testable_languages(), results)

        return {
            'results': {lang_id: {suite['name']: r} for lang_id, r in results.items()},
            'output_files': output_files
        }

    def _get_output_dir(self, lang_id: str) -> Path:
        """Get the output directory for a language (build_dir for binaries)"""
        lang_config = self.config['languages'][lang_id]
        # Languages with script_dir in execution use that for output
        if 'execution' in lang_config:
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
    using a configurable base language. Tests:
    - Base language serialization decoded by all languages
    - All language serializations decoded by base language

    The base language can be configured via:
    - Suite-level 'base_language' field
    - Global 'base_language' in test config
    - Defaults to 'c' if not specified
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

        # Get base language from suite config or global config
        base_lang = suite.get(
            'base_language', self.config.get('base_language', 'c'))
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
                # Languages with script_dir need file copied there too
                execution = lang_config.get('execution', {})
                script_dir_path = execution.get('script_dir')
                if script_dir_path:
                    script_dir = self.project_root / script_dir_path
                    script_target = script_dir / data_file.name
                    with self.executor.temp_copy(data_file, script_target):
                        return self.executor.run_test_script(
                            lang_id, test_config, args=data_file.name)
                else:
                    return self.executor.run_test_script(
                        lang_id, test_config, args=target_file.name)
        except Exception as e:
            if self.verbose:
                self.log(f"Decode failed: {e}", "WARNING")
            return False


class FrameFormatMatrixPlugin(TestPlugin):
    """
    Plugin for consolidated frame format compatibility testing.

    Runs serialization and deserialization tests for multiple frame formats
    and displays results in a single matrix with frame formats as rows
    and languages as columns.

    Uses unified test_runner executable that accepts:
      test_runner encode <frame_format> <output_file>
      test_runner decode <frame_format> <input_file>

    Each cell shows:
    - OK: Both serialization and deserialization passed
    - SER: Serialization failed
    - DES: Deserialization failed  
    - BOTH: Both serialization and deserialization failed
    - N/A: Test could not be run
    """

    plugin_type = "frame_format_matrix"

    def run(self, suite: Dict[str, Any]) -> Dict[str, Any]:
        """Run frame format matrix tests and display consolidated results."""
        # Only print the test description, not redundant section headers
        print(f"[TEST] {suite['description']}")

        # Get frame formats
        frame_formats = suite.get('frame_formats', [])
        if not frame_formats:
            self.log(
                "frame_format_matrix plugin requires 'frame_formats' field", "ERROR")
            return {'results': {}, 'matrix': {}}

        testable = self.executor.get_testable_languages()
        results = {lang_id: {} for lang_id in testable}

        # Matrix: frame_format (rows) vs language (columns)
        # Each cell is a dict with 'encode' and 'decode' results
        matrix = {}

        # Get base language from suite config or global config
        base_lang = suite.get(
            'base_language', self.config.get('base_language', 'c'))

        # Print header once before processing frame formats
        self._print_matrix_header(testable)

        for frame_format in frame_formats:
            format_name = frame_format.get('name')
            output_file_pattern = frame_format.get(
                'output_file', '{lang_name}_output.bin')
            display_name = frame_format.get('display_name', format_name)

            matrix[display_name] = {}
            encoded_files = {}

            # First pass: run all encode tests and collect output files
            for lang_id in testable:
                lang_name = self.config['languages'][lang_id]['name']
                output_file = self._get_output_file(
                    lang_id, output_file_pattern)

                # Run encode using test_runner
                encode_result = self._run_test_runner(
                    lang_id, 'encode', format_name, output_file)

                # Check for output file
                if encode_result and output_file and output_file.exists():
                    encoded_files[lang_id] = output_file

                # Initialize matrix entry
                matrix[display_name][lang_name] = {
                    'encode': encode_result,
                    'decode': None  # Will be set in second pass
                }

                results[lang_id][f"{display_name}_encode"] = encode_result

            # Second pass: run decode tests using base language's encoded file
            base_data_file = encoded_files.get(base_lang)

            for lang_id in testable:
                lang_name = self.config['languages'][lang_id]['name']

                if base_data_file is None or not base_data_file.exists():
                    matrix[display_name][lang_name]['decode'] = None
                    continue

                # Run decoder with base language's encoded file
                decode_result = self._run_decode_with_file(
                    lang_id, format_name, base_data_file)
                matrix[display_name][lang_name]['decode'] = decode_result

                results[lang_id][f"{display_name}_decode"] = decode_result

            # Print this row immediately after all tests for this format complete
            self._print_matrix_row(
                display_name, matrix[display_name], testable)

        # Print summary
        self._print_matrix_summary(matrix)

        return {
            'results': results,
            'matrix': matrix
        }

    def _run_test_runner(self, lang_id: str, mode: str, format_name: str,
                         output_file: Path) -> bool:
        """Run the unified test_runner for a language."""
        lang_config = self.config['languages'][lang_id]
        build_dir = self.project_root / \
            lang_config.get('build_dir', lang_config['test_dir'])

        # Ensure build directory exists
        build_dir.mkdir(parents=True, exist_ok=True)

        # Get test_runner executable/script path
        exe_ext = lang_config.get('compilation', {}).get(
            'executable_extension', '')
        source_ext = lang_config.get(
            'compilation', {}).get('source_extension', '')
        execution = lang_config.get('execution', {})

        # For compiled languages (C, C++)
        if exe_ext:
            runner_path = build_dir / f"test_runner{exe_ext}"
            if not runner_path.exists():
                return False
            cmd = f'"{runner_path}" {mode} {format_name} "{output_file}"'
            return self.executor.run_command(cmd, cwd=build_dir)[0]

        # For C# (dotnet run)
        if execution.get('type') == 'dotnet':
            test_dir = self.project_root / lang_config['test_dir']
            csproj_path = test_dir / 'StructFrameTests.csproj'
            if not csproj_path.exists():
                return False
            cmd = f'dotnet run --project "{csproj_path}" --verbosity quiet -- {mode} {format_name} "{output_file}"'
            return self.executor.run_command(cmd, cwd=test_dir)[0]

        # For TypeScript (compiles to JS)
        if lang_config.get('compilation', {}).get('compiled_extension'):
            script_dir = self.project_root / execution.get('script_dir', '')
            runner_path = script_dir / 'test_runner.js'
            if not runner_path.exists():
                return False
            interpreter = execution.get('interpreter', 'node')
            cmd = f'{interpreter} "{runner_path}" {mode} {format_name} "{output_file}"'
            return self.executor.run_command(cmd, cwd=script_dir)[0]

        # For interpreted languages (Python, JavaScript)
        if 'interpreter' in execution:
            script_dir_path = execution.get('script_dir')
            if script_dir_path:
                # JS runs from generated dir
                script_dir = self.project_root / script_dir_path
                runner_path = script_dir / 'test_runner.js'
            else:
                # Python runs from test dir
                test_dir = self.project_root / lang_config['test_dir']
                source_ext = execution.get('source_extension', '.py')
                runner_path = test_dir / f'test_runner{source_ext}'

            if not runner_path.exists():
                return False

            interpreter = execution['interpreter']
            cwd = runner_path.parent

            # Handle Python's PYTHONPATH
            env_vars = execution.get('env', {})
            env_prefix = ''
            if env_vars:
                gen_dir = self.project_root / \
                    lang_config['code_generation']['output_dir']
                for key, val in env_vars.items():
                    val = val.replace('{generated_dir}', str(gen_dir))
                    val = val.replace(
                        '{generated_parent_dir}', str(gen_dir.parent))
                    # Use cross-platform path separator
                    import os
                    val = val.replace(':', os.pathsep)
                    env_prefix = f'set {key}={val} && ' if os.name == 'nt' else f'{key}={val} '

            cmd = f'{env_prefix}{interpreter} "{runner_path}" {mode} {format_name} "{output_file}"'
            return self.executor.run_command(cmd, cwd=cwd)[0]

        return False

    def _run_decode_with_file(self, lang_id: str, format_name: str,
                              data_file: Path) -> bool:
        """Run decoder with a specific input file."""
        lang_config = self.config['languages'][lang_id]
        build_dir = self.project_root / \
            lang_config.get('build_dir', lang_config['test_dir'])
        target_file = build_dir / data_file.name

        build_dir.mkdir(parents=True, exist_ok=True)

        try:
            with self.executor.temp_copy(data_file, target_file):
                # For script languages, also copy to script_dir
                execution = lang_config.get('execution', {})
                script_dir_path = execution.get('script_dir')
                if script_dir_path:
                    script_dir = self.project_root / script_dir_path
                    script_target = script_dir / data_file.name
                    with self.executor.temp_copy(data_file, script_target):
                        return self._run_test_runner(lang_id, 'decode', format_name, script_target)
                else:
                    return self._run_test_runner(lang_id, 'decode', format_name, target_file)
        except Exception as e:
            if self.verbose:
                self.log(f"Decode failed: {e}", "WARNING")
            return False

    def _get_output_file(self, lang_id: str, pattern: str) -> Optional[Path]:
        """Get the output file path for a language."""
        lang_config = self.config['languages'][lang_id]
        file_prefix = lang_config.get(
            'file_prefix', lang_config['name'].lower())
        filename = pattern.replace('{lang_name}', file_prefix)

        # Check script_dir first (for JS/TS)
        if 'execution' in lang_config:
            script_dir = lang_config['execution'].get('script_dir')
            if script_dir:
                return self.project_root / script_dir / filename

        # Use build_dir
        build_dir = lang_config.get('build_dir', lang_config['test_dir'])
        return self.project_root / build_dir / filename

    def _print_matrix_header(self, testable: list):
        """Print the matrix header with language columns."""
        all_langs = [self.config['languages'][lang_id]['name']
                     for lang_id in testable]
        self._matrix_langs = all_langs
        self._matrix_col_width = 12

        print("\nFrame Format Language Test Matrix:")
        print("Legend: OK=pass, SER=serialization failed, DES=deserialization failed, BOTH=both failed")
        header = "Frame Format".ljust(
            20) + "".join(l.center(self._matrix_col_width) for l in all_langs)
        print(header)
        print("-" * len(header))

    def _print_matrix_row(self, frame_format: str, lang_results: Dict[str, Dict[str, Optional[bool]]], testable: list):
        """Print a single row of the matrix."""
        all_langs = [self.config['languages'][lang_id]['name']
                     for lang_id in testable]
        col_width = 12

        row = frame_format.ljust(20)
        for lang in all_langs:
            val = lang_results.get(lang)
            if val is None:
                cell = "N/A"
            elif isinstance(val, dict):
                encode_ok = val.get('encode')
                decode_ok = val.get('decode')

                if encode_ok is None and decode_ok is None:
                    cell = "N/A"
                elif encode_ok and decode_ok:
                    cell = "OK"
                elif not encode_ok and (decode_ok is False or decode_ok is None):
                    cell = "BOTH"
                elif not encode_ok:
                    cell = "SER"
                elif not decode_ok:
                    cell = "DES"
                else:
                    cell = "N/A"
            elif val:
                cell = "OK"
            else:
                cell = "FAIL"
            row += cell.center(col_width)
        print(row)

    def _print_matrix_summary(self, matrix: Dict[str, Dict[str, Dict[str, Optional[bool]]]]):
        """Print the matrix summary with success rate."""
        success_count = 0
        total_count = 0

        for frame_format, lang_results in matrix.items():
            for lang, val in lang_results.items():
                if val is None:
                    continue
                elif isinstance(val, dict):
                    encode_ok = val.get('encode')
                    decode_ok = val.get('decode')

                    if encode_ok is None and decode_ok is None:
                        continue
                    elif encode_ok and decode_ok:
                        success_count += 1
                        total_count += 1
                    else:
                        total_count += 1
                elif val:
                    success_count += 1
                    total_count += 1
                else:
                    total_count += 1

        if total_count > 0:
            print(
                f"\nSuccess rate: {success_count}/{total_count} ({100*success_count/total_count:.1f}%)\n")

    def _print_frame_format_matrix(self, matrix: Dict[str, Dict[str, Dict[str, Optional[bool]]]]):
        """Print the frame format compatibility matrix with detailed status."""
        if not matrix:
            return

        # Get all language columns
        all_langs = sorted(set().union(
            *[set(d.keys()) for d in matrix.values()]))

        col_width = 12
        print("\nFrame Format Language Test Matrix:")
        print("Legend: OK=pass, SER=serialization failed, DES=deserialization failed, BOTH=both failed")
        header = "Frame Format".ljust(
            20) + "".join(l.center(col_width) for l in all_langs)
        print(header)
        print("-" * len(header))

        success_count = 0
        total_count = 0

        for frame_format, lang_results in matrix.items():
            row = frame_format.ljust(20)
            for lang in all_langs:
                val = lang_results.get(lang)
                if val is None:
                    cell = "N/A"
                elif isinstance(val, dict):
                    encode_ok = val.get('encode')
                    decode_ok = val.get('decode')

                    if encode_ok is None and decode_ok is None:
                        cell = "N/A"
                    elif encode_ok and decode_ok:
                        cell = "OK"
                        success_count += 1
                        total_count += 1
                    elif not encode_ok and (decode_ok is False or decode_ok is None):
                        cell = "BOTH"
                        total_count += 1
                    elif not encode_ok:
                        cell = "SER"
                        total_count += 1
                    elif not decode_ok:
                        cell = "DES"
                        total_count += 1
                    else:
                        cell = "N/A"
                elif val:
                    cell = "OK"
                    success_count += 1
                    total_count += 1
                else:
                    cell = "FAIL"
                    total_count += 1
                row += cell.center(col_width)
            print(row)

        if total_count > 0:
            print(
                f"\nSuccess rate: {success_count}/{total_count} ({100*success_count/total_count:.1f}%)\n")


# Registry of available plugins
PLUGIN_REGISTRY: Dict[str, type] = {
    'standard': StandardTestPlugin,
    'cross_platform_matrix': CrossPlatformMatrixPlugin,
    'frame_format_matrix': FrameFormatMatrixPlugin,
}


def get_plugin(plugin_type: str, executor: 'TestExecutor',
               formatter: 'OutputFormatter') -> TestPlugin:
    """Get a plugin instance by type."""
    plugin_class = PLUGIN_REGISTRY.get(plugin_type, StandardTestPlugin)
    return plugin_class(executor, formatter)


def register_plugin(plugin_class: type):
    """Register a custom plugin class."""
    PLUGIN_REGISTRY[plugin_class.plugin_type] = plugin_class
