"""
Main test runner that composes all components.

This is the main entry point that orchestrates code generation, compilation,
and test execution.
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import TestRunnerBase
from .tool_checker import ToolChecker
from .code_generator import CodeGenerator
from .compiler import Compiler
from .test_executor import TestExecutor
from .output_formatter import OutputFormatter


class ConfigDrivenTestRunner:
    """A completely generic test runner driven by JSON configuration.

    This class composes multiple specialized components to handle different
    aspects of the test workflow:
    - ToolChecker: Verifies compiler/interpreter availability
    - CodeGenerator: Generates code from proto files
    - Compiler: Compiles generated code
    - TestExecutor: Runs test suites
    - OutputFormatter: Formats and prints results
    """

    def __init__(self, config_path: str, verbose: bool = False):
        self.verbose = verbose
        self.project_root = Path(__file__).parent.parent.parent
        self.tests_dir = self.project_root / "tests"
        self.config = TestRunnerBase.load_config(Path(config_path), verbose)
        self.skipped_languages: List[str] = []

        # Initialize component instances
        self._init_components()

    def _init_components(self):
        """Initialize all component instances"""
        self.tool_checker = ToolChecker(
            self.config, self.project_root, self.verbose)
        self.code_generator = CodeGenerator(
            self.config, self.project_root, self.verbose)
        self.compiler = Compiler(
            self.config, self.project_root, self.verbose)
        self.test_executor = TestExecutor(
            self.config, self.project_root, self.verbose)
        self.formatter = OutputFormatter(
            self.config, self.project_root, self.verbose)

    def _sync_skipped_languages(self):
        """Sync skipped languages to all components"""
        for component in [self.tool_checker, self.code_generator,
                          self.compiler, self.test_executor]:
            component.skipped_languages = self.skipped_languages

    def _get_active_languages(self) -> List[str]:
        """Get list of enabled languages that are not skipped"""
        return [lang_id for lang_id, cfg in self.config['languages'].items()
                if cfg.get('enabled', True) and lang_id not in self.skipped_languages]

    # -------------------------------------------------------------------------
    # Delegated Methods (for backward compatibility)
    # -------------------------------------------------------------------------

    def check_tool_availability(self) -> Dict[str, Dict[str, Any]]:
        """Check which compilers/interpreters are available"""
        return self.tool_checker.check_tool_availability()

    def print_tool_availability(self) -> bool:
        """Print a summary of available tools"""
        return self.tool_checker.print_tool_availability()

    def get_available_languages(self) -> List[str]:
        """Get list of languages that have all required tools available"""
        self._sync_skipped_languages()
        return self.tool_checker.get_available_languages()

    def generate_code(self) -> bool:
        """Generate code for all proto files and enabled languages"""
        self._sync_skipped_languages()
        return self.code_generator.generate_code()

    def compile_all(self) -> bool:
        """Compile code for all languages that require compilation"""
        self._sync_skipped_languages()
        return self.compiler.compile_all()

    def run_test_suites(self):
        """Run all non-cross-platform test suites"""
        self._sync_skipped_languages()
        self.test_executor.run_test_suites()

    def run_cross_platform_tests(self) -> bool:
        """Run cross-platform encode/decode tests"""
        self._sync_skipped_languages()
        return self.test_executor.run_cross_platform_tests()

    def print_summary(self) -> bool:
        """Print summary of all test results"""
        return self.formatter.print_summary(
            self.code_generator.results,
            self.compiler.results,
            self.test_executor.results,
            self.test_executor.cross_platform_results,
            self._get_active_languages()
        )

    # -------------------------------------------------------------------------
    # Results Access (for backward compatibility)
    # -------------------------------------------------------------------------

    @property
    def results(self) -> Dict[str, Any]:
        """Get combined results from all components (backward compatibility)"""
        return {
            'generation': self.code_generator.results,
            'compilation': self.compiler.results,
            'tests': self.test_executor.results,
            'cross_platform': self.test_executor.cross_platform_results
        }

    # -------------------------------------------------------------------------
    # Main Entry Point
    # -------------------------------------------------------------------------

    def run_all_tests(self, generate_only: bool = False) -> bool:
        """Run the complete test suite"""
        print("Starting struct-frame Test Suite")
        print(f"Project root: {self.project_root}")

        self._sync_skipped_languages()

        # Check tool availability first
        self.print_tool_availability()
        available_langs = self.get_available_languages()

        if not available_langs:
            print("[ERROR] No languages have all required tools available")
            return False

        # Filter to only available languages
        active = [l for l in self._get_active_languages()
                  if l in available_langs]
        lang_names = [self.config['languages'][l]['name'] for l in active]
        print(f"Testing languages: {', '.join(lang_names)}")

        start_time = time.time()

        try:
            # Create output directories
            for lang_id, cfg in self.config['languages'].items():
                if cfg.get('enabled', True):
                    (self.project_root / cfg['code_generation']
                     ['output_dir']).mkdir(parents=True, exist_ok=True)

            if not self.generate_code():
                print("[ERROR] Code generation failed - aborting remaining tests")
                return False

            if generate_only:
                print("[OK] Code generation completed successfully")
                return True

            self.compile_all()
            self.run_test_suites()
            success = self.print_summary()

            print(
                f"\nTotal test time: {time.time() - start_time:.2f} seconds")
            return success

        except KeyboardInterrupt:
            print("\n[WARN] Test run interrupted by user")
            return False
        except Exception as e:
            print(f"\n[ERROR] Test run failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False
