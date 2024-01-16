import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class Config:
    destination: str
    datasource: dict[str, object] = field(default_factory=dict)
    datasource_file: str = ""
    processors: list[dict[str, object]] = field(default_factory=list)
    min_date: datetime | None = None
    max_date: datetime | None = None
    timezone: str = "Europe/Moscow"

    @staticmethod
    def from_file(path: str | Path) -> "Config":
        # pylint: disable=import-outside-toplevel
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib

        with open(path, "rb") as fp:
            raw_data = tomllib.load(fp)

        config = Config(**raw_data)

        if config.datasource_file:
            if config.datasource:
                raise ValueError("Both datasource and datasource_file defined in config")
            with open(config.datasource_file, "rb") as fp:
                config.datasource = tomllib.load(fp)

        return config
