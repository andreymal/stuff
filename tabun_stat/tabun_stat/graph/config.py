import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class GraphConfig:
    source: str
    destination: str
    graph: list[dict[str, object]] = field(default_factory=list)

    @staticmethod
    def from_file(path: str | Path) -> "GraphConfig":
        # pylint: disable=import-outside-toplevel
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib

        with open(path, "rb") as fp:
            raw_data = tomllib.load(fp)

        return GraphConfig(**raw_data)
