from .Party import Party
from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    name: str
    party: Party
    id: int = 0