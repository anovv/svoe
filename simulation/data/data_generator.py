from typing import Dict


class DataGenerator:


    def next(self) -> Dict:
        raise NotImplementedError


    def has_next(self) -> bool:
        raise NotImplementedError
