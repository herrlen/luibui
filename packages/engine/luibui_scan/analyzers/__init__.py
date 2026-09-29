"""Analyzer protocol and registry."""

from luibui_scan.analyzers.base import Analyzer, AnalyzerInfo
from luibui_scan.analyzers.registry import AnalyzerRegistry, default_registry, register

__all__ = ["Analyzer", "AnalyzerInfo", "AnalyzerRegistry", "default_registry", "register"]

# Built-in analyzers register themselves on import.
from luibui_scan.analyzers import (  # noqa: F401
    a_dateien,
    a_schadsoftware,
    b_inhalte,
    b_muster,
    c_code,
    c_konfig,
    d_abhaengigkeiten,
    e_konfig,
    e_mcp,
    g_dsgvo,
    secrets,
)
