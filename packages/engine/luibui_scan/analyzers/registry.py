"""Registry of analyzers. The pipeline runs analyzers in registration order."""

from collections.abc import Iterator

from luibui_scan.analyzers.base import Analyzer


class AnalyzerRegistry:
    def __init__(self) -> None:
        self._analyzers: dict[str, Analyzer] = {}

    def add(self, analyzer: Analyzer) -> Analyzer:
        if not isinstance(analyzer, Analyzer):
            raise TypeError(f"{analyzer!r} implementiert das Analyzer-Protokoll nicht")
        name = analyzer.info.name
        if name in self._analyzers:
            raise ValueError(f"Analyzer {name!r} ist bereits registriert")
        self._analyzers[name] = analyzer
        return analyzer

    def get(self, name: str) -> Analyzer:
        return self._analyzers[name]

    def __iter__(self) -> Iterator[Analyzer]:
        return iter(self._analyzers.values())

    def __len__(self) -> int:
        return len(self._analyzers)

    def __contains__(self, name: object) -> bool:
        return name in self._analyzers


default_registry = AnalyzerRegistry()


def register[T: Analyzer](cls: type[T]) -> type[T]:
    """Class decorator: instantiate the analyzer and add it to the default registry."""
    default_registry.add(cls())
    return cls
