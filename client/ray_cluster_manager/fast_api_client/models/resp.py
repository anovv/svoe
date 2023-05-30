from typing import Any, Dict, List, Type, TypeVar, Union

import attr

from ..types import UNSET, Unset

T = TypeVar("T", bound="Resp")


@attr.s(auto_attribs=True)
class Resp:
    """
    Attributes:
        result (Union[Unset, Any]):
        error (Union[Unset, str]):
    """

    result: Union[Unset, Any] = UNSET
    error: Union[Unset, str] = UNSET
    additional_properties: Dict[str, Any] = attr.ib(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = self.result
        error = self.error

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if result is not UNSET:
            field_dict["result"] = result
        if error is not UNSET:
            field_dict["error"] = error

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        result = d.pop("result", UNSET)

        error = d.pop("error", UNSET)

        resp = cls(
            result=result,
            error=error,
        )

        resp.additional_properties = d
        return resp

    @property
    def additional_keys(self) -> List[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
