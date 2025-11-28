"""
Output formatting for the test runner.

Handles printing sections, results, matrices, and summaries.
"""

from pathlib import Path
from typing import Any, Dict, List

from .base import TestRunnerBase


class OutputFormatter(TestRunnerBase):
    """Handles formatting and printing of test results"""

    def print_section(self, title: str):
        """Print a section header"""
        print(f"\n{'='*60}\n{title}\n{'='*60}")

    def print_lang_results(self, languages: List[str], results: Dict[str, bool]):
        """Print results for each language"""
        print()
        for lang_id in languages:
            name = self.config['languages'][lang_id]['name']
            status = "PASS" if results.get(lang_id, False) else "FAIL"
            print(f"  {name:>10}: {status}")

    def print_compatibility_matrix(self, matrix: Dict[str, Dict[str, bool]]):
        """Print the cross-platform compatibility matrix"""
        if not matrix:
            return

        all_langs = sorted(set(matrix.keys()) | set().union(
            *[set(d.keys()) for d in matrix.values()]))

        print("\nCompatibility Matrix:")
        header = "Encoder\\Decoder".ljust(
            18) + "".join(l[:8].ljust(10) for l in all_langs)
        print(header)
        print("-" * len(header))

        for encoder in all_langs:
            if encoder in matrix:
                row = encoder.ljust(18)
                for d in all_langs:
                    val = matrix[encoder].get(d)
                    if val is None:
                        cell = " N/A "
                    elif val:
                        cell = " OK "
                    else:
                        cell = " FAIL "
                    row += cell.rjust(10)
                print(row)

        # Count only non-None entries for success rate
        total = sum(1 for d in matrix.values()
                    for v in d.values() if v is not None)
        success = sum(1 for d in matrix.values()
                      for v in d.values() if v is True)
        if total:
            print(
                f"\nSuccess rate: {success}/{total} ({100*success/total:.0f}%)\n")

    def print_summary(self, generation_results: Dict[str, bool],
                      compilation_results: Dict[str, bool],
                      test_results: Dict[str, Dict[str, bool]],
                      cross_platform_results: Dict[str, Dict[str, bool]],
                      active_languages: List[str]) -> bool:
        """Print summary of all test results"""
        self.print_section("TEST RESULTS SUMMARY")

        # Count all results
        passed = total = 0

        # Generation
        for lang_id in active_languages:
            total += 1
            passed += generation_results.get(lang_id, False)

        # Compilation
        for lang_id in active_languages:
            if self.config['languages'][lang_id].get('compilation', {}).get('enabled'):
                total += 1
                passed += compilation_results.get(lang_id, False)

        # Tests
        for lang_id in active_languages:
            for result in test_results.get(lang_id, {}).values():
                if result is not None:
                    total += 1
                    passed += result

        # Cross-platform
        for decoders in cross_platform_results.values():
            for result in decoders.values():
                if result is not None:
                    total += 1
                    passed += result

        print(f"\n{passed}/{total} tests passed")

        if total == 0:
            return False

        rate = 100 * passed / total
        if rate >= 80:
            print(f"SUCCESS: {rate:.1f}% pass rate")
            return True
        elif rate >= 50:
            print(f"PARTIAL SUCCESS: {rate:.1f}% pass rate")
            return True
        else:
            print(f"NEEDS WORK: {rate:.1f}% pass rate")
            return False
