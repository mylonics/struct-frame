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


class FrameFormatEncodePlugin(TestPlugin):
    """
    Plugin for frame format encoding tests.
    
    Runs C to serialize test data using all configured frame formats.
    Produces binary files named c_{frame_format}_test_data.bin.
    """

    plugin_type = "frame_format_encode"

    def run(self, suite: Dict[str, Any]) -> Dict[str, Any]:
        self.formatter.print_section("FRAME FORMAT ENCODING")
        print(f"[TEST] {suite['description']}")

        # Get frame formats from config
        frame_formats = self.config.get('frame_formats', [])
        if not frame_formats:
            self.log("No frame formats configured", "WARNING")
            return {'results': {}, 'output_files': {}}

        # Only C does the encoding
        base_lang = 'c'
        testable = self.executor.get_testable_languages()
        if base_lang not in testable:
            self.log(f"Base language '{base_lang}' is not available", "ERROR")
            return {'results': {}, 'output_files': {}}

        results = {lang_id: {} for lang_id in testable}
        output_files = {}  # frame_format -> Path

        test_config = self.executor.build_test_config(base_lang, suite)
        if not test_config:
            self.log("Could not build test config for C", "ERROR")
            return {'results': results, 'output_files': output_files}

        lang_config = self.config['languages'][base_lang]
        build_dir = self.project_root / lang_config.get('build_dir', lang_config['test_dir'])
        build_dir.mkdir(parents=True, exist_ok=True)

        passed = 0
        failed = 0

        for frame_format in frame_formats:
            # Run C encoder with frame format argument
            result = self.executor.run_test_script(
                base_lang, test_config, args=frame_format)
            
            result_key = f"{suite['name']}_{frame_format}"
            results[base_lang][result_key] = result

            if result:
                # Check for output file
                output_pattern = suite.get('output_file', 'c_{frame_format}_test_data.bin')
                output_name = output_pattern.replace('{frame_format}', frame_format)
                output_path = build_dir / output_name
                if output_path.exists():
                    output_files[frame_format] = output_path
                    passed += 1
                else:
                    failed += 1
            else:
                failed += 1

        print(f"\n  C encoded {passed}/{len(frame_formats)} frame formats successfully")

        return {
            'results': results,
            'output_files': output_files
        }


class FrameFormatMatrixPlugin(TestPlugin):
    """
    Plugin for frame format cross-compatibility matrix testing.

    Tests language vs frame format matrix:
    - C serializes data for each frame format (from frame_format_encode)
    - All languages deserialize C's binary files
    - All languages serialize, C deserializes
    """

    plugin_type = "frame_format_matrix"

    def run(self, suite: Dict[str, Any]) -> Dict[str, Any]:
        self.formatter.print_section("FRAME FORMAT COMPATIBILITY MATRIX")
        print(f"[TEST] {suite['description']}")

        # Get encoded files from the linked suite
        input_suite = suite.get('input_from')
        if not input_suite:
            self.log("frame_format_matrix plugin requires 'input_from' field", "ERROR")
            return {'results': {}, 'matrix': {}}

        encoded_files = self.executor.get_output_files(input_suite)
        frame_formats = self.config.get('frame_formats', [])

        testable = self.executor.get_testable_languages()
        base_lang = 'c'
        
        if base_lang not in testable:
            self.log(f"Base language '{base_lang}' is not available", "ERROR")
            return {'results': {}, 'matrix': {}}

        results = {lang_id: {} for lang_id in testable}
        
        # Matrix: language (rows) vs frame_format (columns)
        matrix = {}

        for lang_id in testable:
            lang_name = self.config['languages'][lang_id]['name']
            matrix[lang_name] = {}

            for frame_format in frame_formats:
                # Get the C-encoded file for this frame format
                data_file = encoded_files.get(frame_format)

                if data_file is None or not data_file.exists():
                    matrix[lang_name][frame_format] = None
                    continue

                # Build decode test config
                decode_config = self.executor.build_test_config(lang_id, suite)
                if not decode_config:
                    matrix[lang_name][frame_format] = None
                    continue

                # Run decoder with frame format and file
                result = self._run_decoder_with_format(
                    lang_id, decode_config, data_file, frame_format)
                matrix[lang_name][frame_format] = result

                result_key = f"{suite['name']}_{frame_format}"
                results[lang_id][result_key] = result

        self._print_frame_format_matrix(matrix, frame_formats)

        return {
            'results': results,
            'matrix': matrix
        }

    def _run_decoder_with_format(self, lang_id: str, test_config: Dict[str, Any],
                                  data_file: Path, frame_format: str) -> bool:
        """Run a decoder test with a specific frame format and input file"""
        lang_config = self.config['languages'][lang_id]
        build_dir = self.project_root / \
            lang_config.get('build_dir', lang_config['test_dir'])
        target_file = build_dir / data_file.name

        build_dir.mkdir(parents=True, exist_ok=True)

        try:
            with self.executor.temp_copy(data_file, target_file):
                # Arguments: frame_format and filename
                args = f"{frame_format} {target_file.name}"

                # TypeScript needs file in JS directory too
                if lang_id == 'ts' and 'compiled_file' in test_config:
                    script_dir = self.project_root / \
                        lang_config['execution'].get('script_dir', '')
                    ts_target = script_dir / data_file.name
                    with self.executor.temp_copy(data_file, ts_target):
                        return self.executor.run_test_script(
                            lang_id, test_config, args=f"{frame_format} {data_file.name}")
                # JavaScript also needs file in script_dir
                elif lang_id == 'js' and 'script_dir' in lang_config.get('execution', {}):
                    script_dir = self.project_root / \
                        lang_config['execution'].get('script_dir', '')
                    js_target = script_dir / data_file.name
                    with self.executor.temp_copy(data_file, js_target):
                        return self.executor.run_test_script(
                            lang_id, test_config, args=f"{frame_format} {data_file.name}")
                else:
                    return self.executor.run_test_script(
                        lang_id, test_config, args=args)
        except Exception as e:
            if self.verbose:
                self.log(f"Decode with format {frame_format} failed: {e}", "WARNING")
            return False

    def _print_frame_format_matrix(self, matrix: Dict[str, Dict[str, Optional[bool]]],
                                    frame_formats: List[str]):
        """Print the frame format compatibility matrix"""
        print("\nFrame Format Compatibility Matrix:")
        
        # Abbreviate frame format names for display
        def abbrev(name: str) -> str:
            # Convert basic_default -> BD, tiny_extended_msg_ids -> TEMI, etc.
            parts = name.split('_')
            if parts[0] == 'basic':
                prefix = 'B'
            elif parts[0] == 'tiny':
                prefix = 'T'
            else:
                prefix = parts[0][0].upper()
            suffix = ''.join(p[0].upper() for p in parts[1:])
            return prefix + suffix

        # Create column headers
        col_headers = [abbrev(ff) for ff in frame_formats]
        col_width = max(len(h) for h in col_headers + ['Language'])
        col_width = max(col_width, 4)

        # Print header row
        header = f"{'Language':<12}"
        for h in col_headers:
            header += f"{h:^{col_width}}"
        print(header)
        print("-" * len(header))

        # Print legend
        print(f"\nLegend: BD=basic_default, BM=basic_minimal, BS=basic_seq, etc.")
        print(f"        TD=tiny_default, TM=tiny_minimal, TS=tiny_seq, etc.\n")

        # Print each language row
        success_count = 0
        total_count = 0

        for lang_name, format_results in matrix.items():
            row = f"{lang_name:<12}"
            for ff in frame_formats:
                result = format_results.get(ff)
                if result is True:
                    row += f"{'OK':^{col_width}}"
                    success_count += 1
                    total_count += 1
                elif result is False:
                    row += f"{'FAIL':^{col_width}}"
                    total_count += 1
                else:
                    row += f"{'N/A':^{col_width}}"
            print(row)

        if total_count > 0:
            print(f"\nSuccess rate: {success_count}/{total_count} ({100*success_count/total_count:.1f}%)")


# Registry of available plugins
PLUGIN_REGISTRY: Dict[str, type] = {
    'standard': StandardTestPlugin,
    'cross_platform_matrix': CrossPlatformMatrixPlugin,
    'frame_format_encode': FrameFormatEncodePlugin,
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
