"""
Language definitions for struct-frame code generation framework.

This module replaces languages.json with direct Python definitions for
cleaner code and direct access to language configurations.
"""

# Base language used for cross-platform compatibility testing
BASE_LANGUAGE = "c"


class LanguageConfig:
    """Configuration for a single language."""

    def __init__(self, name: str, enabled: bool = True, **kwargs):
        self.name = name
        self.enabled = enabled
        self.file_prefix = kwargs.get('file_prefix')
        self.code_generation = kwargs.get('code_generation', {})
        self.compilation = kwargs.get('compilation', {})
        self.execution = kwargs.get('execution', {})
        self.test_dir = kwargs.get('test_dir')
        self.build_dir = kwargs.get('build_dir')
        self.generation_only = kwargs.get('generation_only', False)

    def to_dict(self) -> dict:
        """Convert to dictionary format for compatibility with existing code."""
        result = {
            'name': self.name,
            'enabled': self.enabled,
            'code_generation': self.code_generation,
            'compilation': self.compilation,
        }
        if self.file_prefix:
            result['file_prefix'] = self.file_prefix
        if self.execution:
            result['execution'] = self.execution
        if self.test_dir:
            result['test_dir'] = self.test_dir
        if self.build_dir:
            result['build_dir'] = self.build_dir
        if self.generation_only:
            result['generation_only'] = self.generation_only
        return result


# Language definitions
LANGUAGES = {
    "c": LanguageConfig(
        name="C",
        enabled=True,
        code_generation={
            "flag": "--build_c",
            "output_path_flag": "--c_path",
            "output_dir": "tests/generated/c"
        },
        compilation={
            "enabled": True,
            "compiler": "gcc",
            "compiler_check": "gcc --version",
            "flags": ["-I{generated_dir}", "-o", "{output}", "{source}", "-lm"],
            "source_extension": ".c",
            "executable_extension": ".exe"
        },
        test_dir="tests/c",
        build_dir="tests/c/build"
    ),

    "cpp": LanguageConfig(
        name="C++",
        file_prefix="cpp",
        enabled=True,
        code_generation={
            "flag": "--build_cpp",
            "output_path_flag": "--cpp_path",
            "output_dir": "tests/generated/cpp"
        },
        compilation={
            "enabled": True,
            "compiler": "g++",
            "compiler_check": "g++ --version",
            "flags": ["-std=c++14", "-I{generated_dir}", "-o", "{output}", "{source}"],
            "source_extension": ".cpp",
            "executable_extension": ".exe"
        },
        test_dir="tests/cpp",
        build_dir="tests/cpp/build"
    ),

    "py": LanguageConfig(
        name="Python",
        enabled=True,
        code_generation={
            "flag": "--build_py",
            "output_path_flag": "--py_path",
            "output_dir": "tests/generated/py"
        },
        compilation={
            "enabled": False
        },
        execution={
            "interpreter": "python",
            "source_extension": ".py",
            "env": {
                "PYTHONPATH": "{generated_dir}:{generated_parent_dir}"
            }
        },
        test_dir="tests/py",
        build_dir="tests/py/build"
    ),

    "ts": LanguageConfig(
        name="TypeScript",
        enabled=True,
        code_generation={
            "flag": "--build_ts",
            "output_path_flag": "--ts_path",
            "output_dir": "tests/generated/ts"
        },
        compilation={
            "enabled": True,
            "compiler": "npx tsc",
            "compiler_check": "npx tsc --version",
            "command": "npx tsc --project {generated_dir}/tsconfig.json",
            "output_dir": "tests/generated/ts/js",
            "source_extension": ".ts",
            "compiled_extension": ".js",
            "working_dir": "tests/ts"
        },
        execution={
            "interpreter": "node",
            "script_dir": "tests/generated/ts/js"
        },
        test_dir="tests/ts",
        build_dir="tests/ts/build"
    ),

    "js": LanguageConfig(
        name="JavaScript",
        enabled=True,
        code_generation={
            "flag": "--build_js",
            "output_path_flag": "--js_path",
            "output_dir": "tests/generated/js"
        },
        compilation={
            "enabled": False
        },
        execution={
            "interpreter": "node",
            "source_extension": ".js",
            "script_dir": "tests/generated/js"
        },
        test_dir="tests/js",
        build_dir="tests/js/build"
    ),

    "gql": LanguageConfig(
        name="GraphQL",
        enabled=True,
        code_generation={
            "flag": "--build_gql",
            "output_path_flag": "--gql_path",
            "output_dir": "tests/generated/gql"
        },
        compilation={
            "enabled": False
        },
        generation_only=True
    ),

    "csharp": LanguageConfig(
        name="C#",
        enabled=True,
        code_generation={
            "flag": "--build_csharp",
            "output_path_flag": "--csharp_path",
            "output_dir": "tests/generated/csharp"
        },
        compilation={
            "enabled": True,
            "compiler": "dotnet",
            "compiler_check": "dotnet --version",
            "command": "dotnet build \"{test_dir}/StructFrameTests.csproj\" -c Release -o \"{build_dir}\" --verbosity quiet"
        },
        execution={
            "type": "dotnet",
            "interpreter": "dotnet",
            "source_extension": ".cs",
            "run_command": "dotnet run --project \"{test_dir}/StructFrameTests.csproj\" --no-build --verbosity quiet -- {args}"
        },
        test_dir="tests/csharp",
        build_dir="tests/csharp/bin/Release/net10.0"
    )
}


def get_languages_dict() -> dict:
    """Get all language configurations as a dictionary for compatibility."""
    return {lang_id: lang.to_dict() for lang_id, lang in LANGUAGES.items()}


def get_language(lang_id: str) -> LanguageConfig:
    """Get a specific language configuration."""
    return LANGUAGES.get(lang_id)


def get_enabled_languages() -> list:
    """Get list of enabled language IDs."""
    return [lang_id for lang_id, lang in LANGUAGES.items() if lang.enabled]


def get_testable_languages() -> list:
    """Get list of enabled languages that can run tests (excludes generation_only)."""
    return [lang_id for lang_id, lang in LANGUAGES.items()
            if lang.enabled and not lang.generation_only]
