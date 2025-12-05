"""
Base utilities for the test runner.

Provides common functionality like logging, command execution, and config loading.
"""

import json
import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class TestRunnerBase:
    """Base class with common utilities for test runner components"""

    def __init__(self, config: Dict[str, Any], project_root: Path, verbose: bool = False,
                 verbose_failure: bool = False):
        self.config = config
        self.project_root = project_root
        self.tests_dir = project_root / "tests"
        self.verbose = verbose
        self.verbose_failure = verbose_failure
        self.skipped_languages: List[str] = []

    @classmethod
    def load_config(cls, config_path: Path, verbose: bool = False) -> Dict[str, Any]:
        """Load the test configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            cls._static_log(
                f"Configuration file not found: {config_path}", "ERROR")
            sys.exit(1)
        except json.JSONDecodeError as e:
            cls._static_log(
                f"Invalid JSON in configuration file: {e}", "ERROR")
            sys.exit(1)

    @staticmethod
    def _static_log(message: str, level: str = "INFO"):
        """Static logging method for class-level operations"""
        prefix = {"INFO": "[INFO] ", "ERROR": "[ERROR]",
                  "SUCCESS": "[OK]", "WARNING": "[WARN] "}.get(level, "  ")
        print(f"{prefix} {message}")

    def log(self, message: str, level: str = "INFO"):
        """Log a message with optional verbose output"""
        if level in ("ERROR", "SUCCESS") or self.verbose:
            prefix = {"INFO": "[INFO] ", "ERROR": "[ERROR]",
                      "SUCCESS": "[OK]", "WARNING": "[WARN] "}.get(level, "  ")
            print(f"{prefix} {message}")

    def run_command(self, command: str, cwd: Optional[Path] = None,
                    env: Optional[Dict[str, str]] = None, timeout: int = 30) -> Tuple[bool, str, str]:
        """Run a shell command and return (success, stdout, stderr)"""
        cmd_env = {**os.environ, **(env or {})}
        try:
            result = subprocess.run(
                command, shell=True, cwd=cwd or self.project_root,
                capture_output=True, text=True, timeout=timeout, env=cmd_env
            )
            success = result.returncode == 0
            if self.verbose:
                if result.stdout:
                    print(f"  STDOUT: {result.stdout}")
                if result.stderr:
                    print(f"  STDERR: {result.stderr}")
            elif self.verbose_failure and not success:
                if result.stdout:
                    print(f"  STDOUT: {result.stdout}")
                if result.stderr:
                    print(f"  STDERR: {result.stderr}")
            return success, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            self.log(f"Command timed out after {timeout}s", "ERROR")
            return False, "", "Timeout"
        except Exception as e:
            self.log(f"Command execution failed: {e}", "ERROR")
            return False, "", str(e)

    def get_lang_env(self, lang_id: str) -> Dict[str, str]:
        """Get environment variables for a language"""
        lang_config = self.config['languages'][lang_id]
        execution = lang_config.get('execution', {})
        env = {}
        if 'env' in execution:
            gen_dir = str(self.project_root /
                          lang_config['code_generation']['output_dir'])
            gen_parent_dir = str(Path(gen_dir).parent)
            env = {}
            for k, v in execution['env'].items():
                v = v.replace('{generated_dir}', gen_dir)
                v = v.replace('{generated_parent_dir}', gen_parent_dir)
                # Handle cross-platform path separators (: on Linux, ; on Windows)
                v = v.replace(':', os.pathsep)
                env[k] = v
        return env

    def get_active_languages(self) -> List[str]:
        """Get list of enabled languages that are not skipped"""
        return [lang_id for lang_id, cfg in self.config['languages'].items()
                if cfg.get('enabled', True) and lang_id not in self.skipped_languages]

    def get_testable_languages(self) -> List[str]:
        """Get list of enabled languages that can run tests (excludes generation_only)"""
        return [lang_id for lang_id, cfg in self.config['languages'].items()
                if cfg.get('enabled', True)
                and lang_id not in self.skipped_languages
                and not cfg.get('generation_only', False)]

    @contextmanager
    def temp_copy(self, src: Path, dst: Path):
        """Context manager to temporarily copy a file and clean up"""
        copied = False
        try:
            if src.resolve() != dst.resolve():
                shutil.copy2(src, dst)
                copied = True
            yield
        finally:
            if copied and dst.exists():
                try:
                    dst.unlink()
                except:
                    pass

    # -------------------------------------------------------------------------
    # File name resolution from test_name + language extensions
    # -------------------------------------------------------------------------

    def get_source_extension(self, lang_id: str) -> str:
        """Get source file extension for a language"""
        lang_config = self.config['languages'][lang_id]
        # Check compilation first, then execution
        ext = lang_config.get('compilation', {}).get('source_extension')
        if not ext:
            ext = lang_config.get('execution', {}).get('source_extension', '')
        return ext

    def get_executable_extension(self, lang_id: str) -> str:
        """Get executable extension for compiled languages"""
        return self.config['languages'][lang_id].get('compilation', {}).get('executable_extension', '')

    def get_compiled_extension(self, lang_id: str) -> str:
        """Get compiled output extension (e.g., .js for TypeScript)"""
        return self.config['languages'][lang_id].get('compilation', {}).get('compiled_extension', '')

    def get_test_files(self, lang_id: str, test_name: str) -> Dict[str, str]:
        """Get all file names for a test based on test_name and language extensions.

        Returns dict with keys: source_file, executable (if compiled), compiled_file (if transpiled)
        """
        lang_config = self.config['languages'][lang_id]
        files = {}

        # Source file
        source_ext = self.get_source_extension(lang_id)
        files['source_file'] = f"{test_name}{source_ext}"

        # Executable (for C, C++)
        exe_ext = self.get_executable_extension(lang_id)
        if exe_ext:
            files['executable'] = f"{test_name}{exe_ext}"

        # Compiled file (for TypeScript -> JS)
        compiled_ext = self.get_compiled_extension(lang_id)
        if compiled_ext:
            files['compiled_file'] = f"{test_name}{compiled_ext}"

        return files

    def build_test_config(self, lang_id: str, suite: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Build a test config dict from suite's test_name and language extensions.

        Args:
            lang_id: Language identifier
            suite: Test suite configuration

        Returns:
            Dict with source_file, executable, compiled_file as appropriate, or None if no test_name
        """
        test_name = suite.get('test_name')
        if not test_name:
            return None
        return self.get_test_files(lang_id, test_name)

    def run_test_script(self, lang_id: str, test_config: Dict[str, Any],
                        test_dir: Path = None, args: str = "") -> bool:
        """Run a test script for any language - unified execution logic

        Args:
            lang_id: Language identifier
            test_config: Test configuration with file paths
            test_dir: Optional test directory override
            args: Optional command-line arguments to pass to the test
        """
        lang_config = self.config['languages'][lang_id]
        test_dir = test_dir or (self.project_root / lang_config['test_dir'])
        build_dir = self.project_root / \
            lang_config.get('build_dir', lang_config['test_dir'])
        execution = lang_config.get('execution', {})

        # Compiled executable (C, C++)
        if 'executable' in test_config:
            exe_path = build_dir / test_config['executable']
            cmd = str(exe_path)
            if args:
                cmd = f"{cmd} {args}"
            return exe_path.exists() and self.run_command(cmd, cwd=build_dir)[0]

        # TypeScript (runs compiled JS)
        if lang_id == 'ts' and 'compiled_file' in test_config:
            script_dir = self.project_root / execution.get('script_dir', '')
            script_path = script_dir / test_config['compiled_file']
            if not script_path.exists():
                return False
            cmd = f"{execution['interpreter']} {script_path.name}"
            if args:
                cmd = f"{cmd} {args}"
            return self.run_command(cmd, cwd=script_dir)[0]

        # JavaScript (runs test files from script_dir - generated code directory)
        if lang_id == 'js' and 'script_dir' in execution:
            script_dir = self.project_root / execution.get('script_dir', '')
            source_path = test_dir / test_config['source_file']
            # Copy test file to generated directory for execution
            target_path = script_dir / test_config['source_file']
            if source_path.exists():
                script_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target_path)
            if not target_path.exists():
                return False
            cmd = f"{execution['interpreter']} {target_path.name}"
            if args:
                cmd = f"{cmd} {args}"
            return self.run_command(cmd, cwd=script_dir)[0]

        # Interpreted language (Python, etc.)
        if 'source_file' in test_config:
            source_path = test_dir / test_config['source_file']
            if not source_path.exists():
                return False
            interpreter = execution.get('interpreter')
            if not interpreter:
                return False
            # Ensure build_dir exists and run from there
            build_dir.mkdir(parents=True, exist_ok=True)
            cmd = f"{interpreter} {source_path}"
            if args:
                cmd = f"{cmd} {args}"
            return self.run_command(
                cmd,
                cwd=build_dir, env=self.get_lang_env(lang_id))[0]

        return False
