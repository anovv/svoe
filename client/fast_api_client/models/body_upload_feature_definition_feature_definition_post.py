import json
from io import BytesIO
from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

import attr

from ..types import File

if TYPE_CHECKING:
    from ..models.body_upload_feature_definition_feature_definition_post_tags_item import (
        BodyUploadFeatureDefinitionFeatureDefinitionPostTagsItem,
    )


T = TypeVar("T", bound="BodyUploadFeatureDefinitionFeatureDefinitionPost")


@attr.s(auto_attribs=True)
class BodyUploadFeatureDefinitionFeatureDefinitionPost:
    """
    Attributes:
        tags (List['BodyUploadFeatureDefinitionFeatureDefinitionPostTagsItem']):
        files (List[File]):
    """

    tags: List["BodyUploadFeatureDefinitionFeatureDefinitionPostTagsItem"]
    files: List[File]
    additional_properties: Dict[str, Any] = attr.ib(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        tags = []
        for tags_item_data in self.tags:
            tags_item = tags_item_data.to_dict()

            tags.append(tags_item)

        files = []
        for files_item_data in self.files:
            files_item = files_item_data.to_tuple()

            files.append(files_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "tags": tags,
                "files": files,
            }
        )

        return field_dict

    def to_multipart(self) -> Dict[str, Any]:
        _temp_tags = []
        for tags_item_data in self.tags:
            tags_item = tags_item_data.to_dict()

            _temp_tags.append(tags_item)
        tags = (None, json.dumps(_temp_tags).encode(), "application/json")

        _temp_files = []
        for files_item_data in self.files:
            files_item = files_item_data.to_tuple()

            _temp_files.append(files_item)
        files = (None, json.dumps(_temp_files).encode(), "application/json")

        field_dict: Dict[str, Any] = {}
        field_dict.update(
            {key: (None, str(value).encode(), "text/plain") for key, value in self.additional_properties.items()}
        )
        field_dict.update(
            {
                "tags": tags,
                "files": files,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.body_upload_feature_definition_feature_definition_post_tags_item import (
            BodyUploadFeatureDefinitionFeatureDefinitionPostTagsItem,
        )

        d = src_dict.copy()
        tags = []
        _tags = d.pop("tags")
        for tags_item_data in _tags:
            tags_item = BodyUploadFeatureDefinitionFeatureDefinitionPostTagsItem.from_dict(tags_item_data)

            tags.append(tags_item)

        files = []
        _files = d.pop("files")
        for files_item_data in _files:
            files_item = File(payload=BytesIO(files_item_data))

            files.append(files_item)

        body_upload_feature_definition_feature_definition_post = cls(
            tags=tags,
            files=files,
        )

        body_upload_feature_definition_feature_definition_post.additional_properties = d
        return body_upload_feature_definition_feature_definition_post

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
