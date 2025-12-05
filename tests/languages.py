"""
Language definitions for struct-frame code generation framework.

This module provides a Language base class with action methods for:
- Compiler checking and compilation
- Interpreter checking and script execution
- Test running

Each language subclass defines its specific behavior.
"""

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Base language used for cross-platform compatibility testing
BASE_LANGUAGE = "c"


class Language:
    """Base class for language definitions with action methods."""

    name: str = ""
    enabled: bool = True
    generation_only: bool = False
    file_prefix: Optional[str] = None

    # Code generation settings
    gen_flag: str = ""
    gen_output_path_flag: str = ""
    gen_output_dir: str = ""

    # Directory settings
    test_dir: str = ""
    build_dir: str = ""

    # Compilation settings
    compiler: Optional[str] = None
    compiler_check_cmd: Optional[str] = None
    source_extension: str = ""
    executable_extension: str = ""
    compiled_extension: str = ""
    compile_command: Optional[str] = None
    compile_working_dir: Optional[str] = None
    compile_output_dir: Optional[str] = None

    # Execution settings
    interpreter: Optional[str] = None
    script_dir: Optional[str] = None
    run_command: Optional[str] = None
    execution_type: Optional[str] = None

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.verbose = False
        self.verbose_failure = False
        # Initialize mutable attributes per instance to avoid shared state
        self.compile_flags: List[str] = self._get_compile_flags()
        self.env_vars: Dict[str, str] = self._get_env_vars()

    def _get_compile_flags(self) -> List[str]:
        """Override in subclass to provide compile flags."""
        return []

    def _get_env_vars(self) -> Dict[str, str]:
        """Override in subclass to provide environment variables."""
        return {}

    def _run_command(self, command: str, cwd: Optional[Path] = None,
                     env: Optional[Dict[str, str]] = None, timeout: int = 30) -> Tuple[bool, str, str]:
        """Run a shell command and return (success, stdout, stderr)."""
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
            return False, "", "Timeout"
        except Exception as e:
            return False, "", str(e)

    # -------------------------------------------------------------------------
    # Tool Checking Methods
    # -------------------------------------------------------------------------

    def check_compiler(self) -> Dict[str, Any]:
        """Check if the compiler is available.

        Returns dict with keys: name, available, version
        """
        if not self.compiler:
            return {'name': None, 'available': True, 'version': ''}

        check_cmd = self.compiler_check_cmd or f"{self.compiler} --version"
        working_dir = None
        if self.compile_working_dir:
            working_dir = self.project_root / self.compile_working_dir

        success, stdout, stderr = self._run_command(check_cmd, cwd=working_dir, timeout=5)

        version = ""
        if success:
            output = stdout or stderr
            version = output.strip().split('\n')[0] if output else ""

        return {
            'name': self.compiler,
            'available': success,
            'version': version
        }

    def check_interpreter(self) -> Dict[str, Any]:
        """Check if the interpreter is available.

        Returns dict with keys: name, available, version
        """
        if not self.interpreter:
            return {'name': None, 'available': True, 'version': ''}

        success, stdout, stderr = self._run_command(f"{self.interpreter} --version", timeout=5)

        version = ""
        if success:
            output = stdout or stderr
            version = output.strip().split('\n')[0] if output else ""

        return {
            'name': self.interpreter,
            'available': success,
            'version': version
        }

    def check_tools(self) -> Dict[str, Any]:
        """Check all required tools for this language.

        Returns dict with keys: name, available, compiler, interpreter, reason
        """
        info = {
            'name': self.name,
            'available': True,
            'compiler': None,
            'interpreter': None,
        }

        if self.generation_only:
            info['generation_only'] = True
            return info

        # Check compiler if needed
        if self.compiler:
            compiler_info = self.check_compiler()
            info['compiler'] = compiler_info
            if not compiler_info['available']:
                info['available'] = False
                info['reason'] = f"Compiler '{self.compiler}' not found"

        # Check interpreter if needed
        if self.interpreter:
            interp_info = self.check_interpreter()
            info['interpreter'] = interp_info
            if not interp_info['available']:
                info['available'] = False
                info['reason'] = f"Interpreter '{self.interpreter}' not found"

        return info

    # -------------------------------------------------------------------------
    # Compilation Methods
    # -------------------------------------------------------------------------

    def compile(self, sources: List[Path], output: Path, gen_dir: Path) -> bool:
        """Compile source files into an executable.

        Args:
            sources: List of source file paths
            output: Output executable path
            gen_dir: Generated code directory (for includes)

        Returns:
            True if compilation succeeded
        """
        if not self.compiler:
            return True  # No compilation needed

        for source in sources:
            if not source.exists():
                return False

        # Build flags, replacing placeholders
        sources_str = ' '.join(f'"{s}"' for s in sources)
        flags = []
        for f in self.compile_flags:
            f = f.replace('{generated_dir}', str(gen_dir))
            f = f.replace('{output}', str(output))
            if '{source}' in f:
                f = sources_str
            flags.append(f)

        cmd = f"{self.compiler} {' '.join(flags)}"
        return self._run_command(cmd)[0]

    def compile_project(self, test_dir: Path, build_dir: Path, gen_dir: Path) -> bool:
        """Compile a project using a custom command (e.g., TypeScript, C#).

        Args:
            test_dir: Test source directory
            build_dir: Build output directory
            gen_dir: Generated code directory

        Returns:
            True if compilation succeeded
        """
        if not self.compile_command:
            return True

        # Format command with placeholders
        output_dir = self.project_root / self.compile_output_dir if self.compile_output_dir else build_dir
        cmd = self.compile_command.format(
            test_dir=test_dir,
            build_dir=build_dir,
            output_dir=output_dir,
            generated_dir=gen_dir
        )

        working_dir = None
        if self.compile_working_dir:
            working_dir = self.project_root / self.compile_working_dir

        return self._run_command(cmd, cwd=working_dir)[0]

    # -------------------------------------------------------------------------
    # Execution Methods
    # -------------------------------------------------------------------------

    def get_env(self, gen_dir: Path) -> Dict[str, str]:
        """Get environment variables for running scripts."""
        if not self.env_vars:
            return {}

        gen_parent_dir = gen_dir.parent
        env = {}
        for k, v in self.env_vars.items():
            v = v.replace('{generated_dir}', str(gen_dir))
            v = v.replace('{generated_parent_dir}', str(gen_parent_dir))
            v = v.replace(':', os.pathsep)
            env[k] = v
        return env

    def run(self, script_path: Path, args: str = "", cwd: Optional[Path] = None,
            gen_dir: Optional[Path] = None) -> bool:
        """Run a script or executable.

        Args:
            script_path: Path to the script or executable
            args: Command-line arguments
            cwd: Working directory
            gen_dir: Generated code directory (for environment vars)

        Returns:
            True if execution succeeded
        """
        if not script_path.exists():
            return False

        env = self.get_env(gen_dir) if gen_dir else {}

        # Compiled executable (no interpreter needed)
        if self.executable_extension and script_path.suffix == self.executable_extension:
            cmd = str(script_path)
            if args:
                cmd = f"{cmd} {args}"
            return self._run_command(cmd, cwd=cwd, env=env)[0]

        # Script with interpreter
        if self.interpreter:
            cmd = f"{self.interpreter} {script_path}"
            if args:
                cmd = f"{cmd} {args}"
            return self._run_command(cmd, cwd=cwd, env=env)[0]

        return False

    def run_project(self, test_dir: Path, args: str = "") -> bool:
        """Run a project using a custom run command (e.g., dotnet run).

        Args:
            test_dir: Project directory
            args: Command-line arguments

        Returns:
            True if execution succeeded
        """
        if not self.run_command:
            return False

        cmd = self.run_command.format(test_dir=test_dir, args=args)
        return self._run_command(cmd, cwd=test_dir)[0]

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def get_test_dir(self) -> Path:
        """Get the test directory path."""
        return self.project_root / self.test_dir

    def get_build_dir(self) -> Path:
        """Get the build directory path."""
        return self.project_root / (self.build_dir or self.test_dir)

    def get_gen_dir(self) -> Path:
        """Get the generated code directory path."""
        return self.project_root / self.gen_output_dir

    def get_script_dir(self) -> Optional[Path]:
        """Get the script execution directory path."""
        if self.script_dir:
            return self.project_root / self.script_dir
        return None

    def to_dict(self) -> dict:
        """Convert to dictionary format for compatibility with existing code."""
        result = {
            'name': self.name,
            'enabled': self.enabled,
            'code_generation': {
                'flag': self.gen_flag,
                'output_path_flag': self.gen_output_path_flag,
                'output_dir': self.gen_output_dir,
            },
            'compilation': {
                'enabled': self.compiler is not None,
            },
        }
        if self.file_prefix:
            result['file_prefix'] = self.file_prefix
        if self.test_dir:
            result['test_dir'] = self.test_dir
        if self.build_dir:
            result['build_dir'] = self.build_dir
        if self.generation_only:
            result['generation_only'] = self.generation_only

        # Add compilation details
        if self.compiler:
            comp_details = {
                'compiler': self.compiler,
                'compiler_check': self.compiler_check_cmd or f"{self.compiler} --version",
            }
            # Only add flags if present
            if self.compile_flags:
                comp_details['flags'] = self.compile_flags
            # Only add source_extension if there's a compiled output extension (e.g., TypeScript)
            if self.compiled_extension:
                comp_details['source_extension'] = self.source_extension
                comp_details['compiled_extension'] = self.compiled_extension
            # Only add executable_extension for native compilers (C, C++)
            if self.executable_extension:
                comp_details['source_extension'] = self.source_extension
                comp_details['executable_extension'] = self.executable_extension
            if self.compile_command:
                comp_details['command'] = self.compile_command
            if self.compile_working_dir:
                comp_details['working_dir'] = self.compile_working_dir
            if self.compile_output_dir:
                comp_details['output_dir'] = self.compile_output_dir
            result['compilation'].update(comp_details)

        # Add execution details
        if self.interpreter or self.run_command:
            result['execution'] = {}
            if self.interpreter:
                result['execution']['interpreter'] = self.interpreter
            if self.source_extension:
                result['execution']['source_extension'] = self.source_extension
            if self.script_dir:
                result['execution']['script_dir'] = self.script_dir
            if self.env_vars:
                result['execution']['env'] = self.env_vars
            if self.run_command:
                result['execution']['run_command'] = self.run_command
            if self.execution_type:
                result['execution']['type'] = self.execution_type

        return result


# =============================================================================
# Language Implementations
# =============================================================================

class CLanguage(Language):
    """C language configuration and actions."""

    name = "C"
    gen_flag = "--build_c"
    gen_output_path_flag = "--c_path"
    gen_output_dir = "tests/generated/c"

    compiler = "gcc"
    compiler_check_cmd = "gcc --version"
    source_extension = ".c"
    executable_extension = ".exe"

    test_dir = "tests/c"
    build_dir = "tests/c/build"

    def _get_compile_flags(self) -> List[str]:
        return ["-I{generated_dir}", "-o", "{output}", "{source}", "-lm"]


class CppLanguage(Language):
    """C++ language configuration and actions."""

    name = "C++"
    file_prefix = "cpp"
    gen_flag = "--build_cpp"
    gen_output_path_flag = "--cpp_path"
    gen_output_dir = "tests/generated/cpp"

    compiler = "g++"
    compiler_check_cmd = "g++ --version"
    source_extension = ".cpp"
    executable_extension = ".exe"

    test_dir = "tests/cpp"
    build_dir = "tests/cpp/build"

    def _get_compile_flags(self) -> List[str]:
        return ["-std=c++14", "-I{generated_dir}", "-o", "{output}", "{source}"]


class PythonLanguage(Language):
    """Python language configuration and actions."""

    name = "Python"
    gen_flag = "--build_py"
    gen_output_path_flag = "--py_path"
    gen_output_dir = "tests/generated/py"

    interpreter = "python"
    source_extension = ".py"

    test_dir = "tests/py"
    build_dir = "tests/py/build"

    def _get_env_vars(self) -> Dict[str, str]:
        return {"PYTHONPATH": "{generated_dir}:{generated_parent_dir}"}


class TypeScriptLanguage(Language):
    """TypeScript language configuration and actions."""

    name = "TypeScript"
    gen_flag = "--build_ts"
    gen_output_path_flag = "--ts_path"
    gen_output_dir = "tests/generated/ts"

    compiler = "npx tsc"
    compiler_check_cmd = "npx tsc --version"
    compile_command = "npx tsc --project {generated_dir}/tsconfig.json"
    compile_output_dir = "tests/generated/ts/js"
    compile_working_dir = "tests/ts"
    source_extension = ".ts"
    compiled_extension = ".js"

    interpreter = "node"
    script_dir = "tests/generated/ts/js"

    test_dir = "tests/ts"
    build_dir = "tests/ts/build"


class JavaScriptLanguage(Language):
    """JavaScript language configuration and actions."""

    name = "JavaScript"
    gen_flag = "--build_js"
    gen_output_path_flag = "--js_path"
    gen_output_dir = "tests/generated/js"

    interpreter = "node"
    source_extension = ".js"
    script_dir = "tests/generated/js"

    test_dir = "tests/js"
    build_dir = "tests/js/build"


class GraphQLLanguage(Language):
    """GraphQL language configuration (generation only)."""

    name = "GraphQL"
    generation_only = True
    gen_flag = "--build_gql"
    gen_output_path_flag = "--gql_path"
    gen_output_dir = "tests/generated/gql"


class CSharpLanguage(Language):
    """C# language configuration and actions."""

    name = "C#"
    gen_flag = "--build_csharp"
    gen_output_path_flag = "--csharp_path"
    gen_output_dir = "tests/generated/csharp"

    compiler = "dotnet"
    compiler_check_cmd = "dotnet --version"
    compile_command = 'dotnet build "{test_dir}/StructFrameTests.csproj" -c Release -o "{build_dir}" --verbosity quiet'

    interpreter = "dotnet"
    execution_type = "dotnet"
    source_extension = ".cs"
    run_command = 'dotnet run --project "{test_dir}/StructFrameTests.csproj" --no-build --verbosity quiet -- {args}'

    test_dir = "tests/csharp"
    build_dir = "tests/csharp/bin/Release/net10.0"


# =============================================================================
# Language Registry
# =============================================================================

# Language class registry
LANGUAGE_CLASSES = {
    "c": CLanguage,
    "cpp": CppLanguage,
    "py": PythonLanguage,
    "ts": TypeScriptLanguage,
    "js": JavaScriptLanguage,
    "gql": GraphQLLanguage,
    "csharp": CSharpLanguage,
}


def get_language(lang_id: str, project_root: Path) -> Optional[Language]:
    """Get a language instance.

    Args:
        lang_id: Language identifier (e.g., 'c', 'py', 'ts')
        project_root: Path to the project root directory

    Returns:
        Language instance or None if language not found
    """
    lang_class = LANGUAGE_CLASSES.get(lang_id)
    if lang_class:
        return lang_class(project_root)
    return None


def get_languages_dict() -> dict:
    """Get all language configurations as a dictionary for compatibility."""
    # Use a dummy project root for config generation
    dummy_root = Path(".")
    return {lang_id: lang_class(dummy_root).to_dict()
            for lang_id, lang_class in LANGUAGE_CLASSES.items()}


def get_enabled_languages() -> list:
    """Get list of enabled language IDs."""
    dummy_root = Path(".")
    return [lang_id for lang_id, lang_class in LANGUAGE_CLASSES.items()
            if lang_class(dummy_root).enabled]


def get_testable_languages() -> list:
    """Get list of enabled languages that can run tests (excludes generation_only)."""
    dummy_root = Path(".")
    return [lang_id for lang_id, lang_class in LANGUAGE_CLASSES.items()
            if lang_class(dummy_root).enabled and not lang_class(dummy_root).generation_only]
