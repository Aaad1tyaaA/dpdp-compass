from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParsedPage:
    page_number: int
    text: str


@dataclass
class ParsedDocument:
    document_id: str
    document_name: str
    document_type: str
    pages: list[ParsedPage] = field(default_factory=list)
    raw_text: str = ""
    metadata: dict = field(default_factory=dict)

    @property
    def total_pages(self) -> int:
        return len(self.pages)

    @property
    def total_chars(self) -> int:
        return sum(len(p.text) for p in self.pages)


class BaseParser(ABC):
    @abstractmethod
    def parse(self, content: bytes, filename: str, document_id: str) -> ParsedDocument:
        ...

    @abstractmethod
    def can_parse(self, filename: str) -> bool:
        ...
