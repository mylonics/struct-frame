"""
Test Runner Package for struct-frame Project

This package provides a modular, configuration-driven test runner.
"""

from .base import TestRunnerBase
from .tool_checker import ToolChecker
from .code_generator import CodeGenerator
from .compiler import Compiler
from .test_executor import TestExecutor
from .output_formatter import OutputFormatter
from .runner import ConfigDrivenTestRunner
from .plugins import TestPlugin, StandardTestPlugin, CrossPlatformMatrixPlugin, register_plugin

__all__ = [
    'TestRunnerBase',
    'ToolChecker',
    'CodeGenerator',
    'Compiler',
    'TestExecutor',
    'OutputFormatter',
    'ConfigDrivenTestRunner',
    'TestPlugin',
    'StandardTestPlugin',
    'CrossPlatformMatrixPlugin',
    'register_plugin',
]
