"""Analyzer protocol and registry."""

from luibui_scan.analyzers.base import Analyzer, AnalyzerInfo
from luibui_scan.analyzers.registry import AnalyzerRegistry, default_registry, register

__all__ = ["Analyzer", "AnalyzerInfo", "AnalyzerRegistry", "default_registry", "register"]

# Built-in analyzers register themselves on import.
from luibui_scan.analyzers import a_dateien, b_inhalte  # noqa: F401
