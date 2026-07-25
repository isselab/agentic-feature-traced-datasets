"""Shared parsing helpers for the dataset submodule catalog."""

from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class Dataset:
    section: str
    name: str
    path: str
    url: str


def read_datasets(root: Path) -> list[Dataset]:
    modules = root / ".gitmodules"
    if not modules.exists():
        return []
    parser = configparser.ConfigParser()
    parser.read(modules, encoding="utf-8")
    result: list[Dataset] = []
    for section in parser.sections():
        if not section.startswith('submodule "') or not section.endswith('"'):
            raise ValueError(f"invalid .gitmodules section: {section}")
        name = section[len('submodule "') : -1]
        result.append(
            Dataset(
                section=section,
                name=name,
                path=parser.get(section, "path"),
                url=parser.get(section, "url"),
            )
        )
    return sorted(result, key=lambda item: item.name.casefold())


def repository_name(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    name = path.rsplit("/", 1)[-1]
    return name[:-4] if name.endswith(".git") else name
