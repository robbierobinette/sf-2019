from dataclasses import dataclass
@dataclass(frozen=True)
class Party:
    name: str
    short_name: str


Republicans = Party("Republican", "rep")
Democrats = Party("Democrat", "dem")
Independents = Party("Independent", "ind")
NoParty = Party("NoParty", "none")
