from typing import Dict, List, Tuple

InputItem = Dict
InputItemBatch = Tuple[Dict, List[InputItem]] # metadata dict + items
IndexItem = Dict
IndexItemBatch = Tuple[Dict, List[IndexItem]]