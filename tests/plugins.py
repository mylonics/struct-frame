"""
Test plugins for custom test execution behavior.

Plugins allow tests to define their own execution and output logic.
Simplified version that works with the consolidated runner.
"""

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from runner import TestRunner


class TestPlugin(ABC):
    """Base class for test plugins that provide custom execution behavior."""

    plugin_type: str = ""

    def __init__(self, runner: 'TestRunner'):
        self.runner = runner
        self.config = runner.config
        self.project_root = runner.project_root
        self.verbose = runner.verbose

    @abstractmethod
    def run(self, suite: Dict[str, Any]) -> Dict[str, Any]:
        """Run the test suite with custom logic."""
        pass

    def log(self, message: str, level: str = "INFO"):
        """Log a message."""
        self.runner.log(message, level)


class FrameFormatMatrixPlugin(TestPlugin):
    """
    Plugin for consolidated frame format compatibility testing.

    Runs serialization and deserialization tests for multiple frame formats
    and displays results in a single matrix.
    """

    plugin_type = "frame_format_matrix"

    def _get_expected_message_count(self) -> int:
        """Get the expected message count from test_messages.json."""
        test_messages_path = self.project_root / "tests" / "test_messages.json"
        try:
            with open(test_messages_path, 'r') as f:
                data = json.load(f)
                return len(data.get('MixedMessages', []))
        except Exception:
            return 0

    def run(self, suite: Dict[str, Any]) -> Dict[str, Any]:
        """Run frame format matrix tests and display consolidated results."""
        print(f"[TEST] {suite['description']}")

        frame_formats = suite.get('frame_formats', [])
        if not frame_formats:
            self.log(
                "frame_format_matrix plugin requires 'frame_formats' field", "ERROR")
            return {'results': {}, 'matrix': {}}

        testable = self.runner.get_testable_languages()
        results = {lang_id: {} for lang_id in testable}
        matrix = {}

        base_lang = suite.get(
            'base_language', self.config.get('base_language', 'c'))
        
        # Fall back to first testable language if base_lang is not available
        if base_lang not in testable and testable:
            base_lang = testable[0]
        
        expected_message_count = self._get_expected_message_count()
        
        lang_names = [self.runner.get_lang(l).name for l in testable if self.runner.get_lang(l)]
        print(f"  Testing {len(frame_formats)} frame format(s) across {len(testable)} language(s): {', '.join(lang_names)}")
        print(f"  Expected messages per format: {expected_message_count}")

        self._print_matrix_header(testable)

        for idx, frame_format in enumerate(frame_formats, 1):
            format_name = frame_format.get('name')
            output_file_pattern = frame_format.get(
                'output_file', '{lang_name}_output.bin')
            display_name = frame_format.get('display_name', format_name)

            matrix[display_name] = {}
            encoded_files = {}

            # First pass: run all encode tests
            for lang_id in testable:
                lang = self.runner.get_lang(lang_id)
                lang_name = lang.name if lang else lang_id
                output_file = self._get_output_file(
                    lang_id, output_file_pattern)

                encode_result, _ = self.runner.run_test_runner(
                    lang_id, 'encode', format_name, output_file)

                if encode_result and output_file and output_file.exists():
                    encoded_files[lang_id] = output_file

                matrix[display_name][lang_name] = {
                    'encode': encode_result,
                    'decode': None,
                    'message_count': 0,
                    'expected_count': expected_message_count
                }
                results[lang_id][f"{display_name}_encode"] = encode_result

            # Second pass: run decode tests using base language's encoded file
            base_data_file = encoded_files.get(base_lang)

            for lang_id in testable:
                lang = self.runner.get_lang(lang_id)
                lang_name = lang.name if lang else lang_id

                if base_data_file is None or not base_data_file.exists():
                    matrix[display_name][lang_name]['decode'] = None
                    continue

                decode_result, message_count = self._run_decode_with_file(
                    lang_id, format_name, base_data_file)
                
                # Consider decode failed if not all expected messages were decoded
                decode_success = decode_result and (expected_message_count == 0 or message_count >= expected_message_count)
                
                matrix[display_name][lang_name]['decode'] = decode_success
                matrix[display_name][lang_name]['message_count'] = message_count
                matrix[display_name][lang_name]['expected_count'] = expected_message_count
                results[lang_id][f"{display_name}_decode"] = decode_success

            self._print_matrix_row(
                display_name, matrix[display_name], testable)

        self._print_matrix_summary(matrix)

        return {'results': results, 'matrix': matrix}

    def _run_decode_with_file(self, lang_id: str, format_name: str, data_file: Path) -> tuple[bool, int]:
        """Run decoder with a specific input file.
        
        Returns:
            (success, message_count): success status and number of messages decoded
        """
        lang = self.runner.get_lang(lang_id)
        if not lang:
            return False, 0

        build_dir = lang.get_build_dir()
        target_file = build_dir / data_file.name
        build_dir.mkdir(parents=True, exist_ok=True)

        try:
            with self.runner.temp_copy(data_file, target_file):
                script_dir = lang.get_script_dir()
                if script_dir:
                    script_target = script_dir / data_file.name
                    with self.runner.temp_copy(data_file, script_target):
                        return self.runner.run_test_runner(lang_id, 'decode', format_name, script_target)
                else:
                    return self.runner.run_test_runner(lang_id, 'decode', format_name, target_file)
        except Exception as e:
            if self.verbose:
                self.log(f"Decode failed: {e}", "WARNING")
            return False, 0

    def _get_output_file(self, lang_id: str, pattern: str) -> Optional[Path]:
        """Get the output file path for a language."""
        lang = self.runner.get_lang(lang_id)
        if not lang:
            return None

        file_prefix = lang.file_prefix or lang.name.lower()
        filename = pattern.replace('{lang_name}', file_prefix)

        script_dir = lang.get_script_dir()
        if script_dir:
            return script_dir / filename

        return lang.get_build_dir() / filename

    def _print_matrix_header(self, testable: list):
        """Print the matrix header with language columns."""
        all_langs = []
        for lang_id in testable:
            lang = self.runner.get_lang(lang_id)
            all_langs.append(lang.name if lang else lang_id)

        col_width = 12
        print("\nFrame Format Language Test Matrix:")
        print("Legend: OK(N)=pass with N messages, MISS(N/E)=missing messages (N decoded, E expected), SER=serialization failed, DES(N)=deserialization failed (N decoded), BOTH=both failed")
        header = "Frame Format".ljust(
            20) + "".join(l.center(col_width) for l in all_langs)
        print(header)
        print("-" * len(header))

    def _print_matrix_row(self, frame_format: str, lang_results: Dict[str, Dict[str, any]], testable: list):
        """Print a single row of the matrix."""
        all_langs = []
        for lang_id in testable:
            lang = self.runner.get_lang(lang_id)
            all_langs.append(lang.name if lang else lang_id)
        col_width = 12

        row = frame_format.ljust(20)
        for lang_name in all_langs:
            val = lang_results.get(lang_name)
            if val is None:
                cell = "N/A"
            elif isinstance(val, dict):
                encode_ok = val.get('encode')
                decode_ok = val.get('decode')
                message_count = val.get('message_count', 0)
                expected_count = val.get('expected_count', 0)
                
                # Check for missing messages (decode ran but didn't get all messages)
                has_missing_messages = expected_count > 0 and message_count < expected_count

                if encode_ok is None and decode_ok is None:
                    cell = "N/A"
                elif encode_ok and decode_ok:
                    # Full success
                    if message_count > 0:
                        cell = f"OK({message_count})"
                    else:
                        cell = "OK"
                elif encode_ok and not decode_ok and has_missing_messages:
                    # Encode OK but missing messages during decode
                    cell = f"MISS({message_count}/{expected_count})"
                elif not encode_ok and (decode_ok is False or decode_ok is None):
                    cell = "BOTH"
                elif not encode_ok:
                    cell = "SER"
                elif not decode_ok:
                    cell = f"DES({message_count})" if message_count > 0 else "DES"
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
                    
                    # Count encode/decode as separate tests
                    if encode_ok is not None:
                        total_count += 1
                        if encode_ok:
                            success_count += 1
                    if decode_ok is not None:
                        total_count += 1
                        if decode_ok:
                            success_count += 1
                elif val:
                    success_count += 1
                    total_count += 1
                else:
                    total_count += 1

        if total_count > 0:
            print(
                f"\nSuccess rate: {success_count}/{total_count} ({100*success_count/total_count:.1f}%)\n")


# Registry of available plugins
PLUGIN_REGISTRY: Dict[str, type] = {
    'frame_format_matrix': FrameFormatMatrixPlugin,
}


def get_plugin(plugin_type: str, runner: 'TestRunner') -> TestPlugin:
    """Get a plugin instance by type."""
    plugin_class = PLUGIN_REGISTRY.get(plugin_type)
    if not plugin_class:
        raise ValueError(f"Unknown plugin type: {plugin_type}")
    return plugin_class(runner)
