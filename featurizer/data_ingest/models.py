from dataclasses import dataclass
from typing import Dict, List, Tuple

InputItem = Dict


@dataclass
class InputItemBatch:
    batch_id: int
    items: List[InputItem]