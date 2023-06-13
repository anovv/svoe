from http import HTTPStatus
from typing import Any, Dict, Optional, Union, cast

import httpx

from ... import errors
from ...client import Client
from ...models.body_upload_feature_definition_feature_definition_post import (
    BodyUploadFeatureDefinitionFeatureDefinitionPost,
)
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response


def _get_kwargs(
    *,
    client: Client,
    multipart_data: BodyUploadFeatureDefinitionFeatureDefinitionPost,
    owner_id: str,
    feature_group: str,
    feature_definition: str,
    version: str,
) -> Dict[str, Any]:
    url = "{}/feature_definition/".format(client.base_url)

    headers: Dict[str, str] = client.get_headers()
    cookies: Dict[str, Any] = client.get_cookies()

    params: Dict[str, Any] = {}
    params["owner_id"] = owner_id

    params["feature_group"] = feature_group

    params["feature_definition"] = feature_definition

    params["version"] = version

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    multipart_multipart_data = multipart_data.to_multipart()

    return {
        "method": "post",
        "url": url,
        "headers": headers,
        "cookies": cookies,
        "timeout": client.get_timeout(),
        "follow_redirects": client.follow_redirects,
        "files": multipart_multipart_data,
        "params": params,
    }


def _parse_response(*, client: Client, response: httpx.Response) -> Optional[Union[HTTPValidationError, str]]:
    if response.status_code == HTTPStatus.OK:
        response_200 = cast(str, response.json())
        return response_200
    if response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: Client, response: httpx.Response) -> Response[Union[HTTPValidationError, str]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Client,
    multipart_data: BodyUploadFeatureDefinitionFeatureDefinitionPost,
    owner_id: str,
    feature_group: str,
    feature_definition: str,
    version: str,
) -> Response[Union[HTTPValidationError, str]]:
    """Upload Feature Definition

    Args:
        owner_id (str):
        feature_group (str):
        feature_definition (str):
        version (str):
        multipart_data (BodyUploadFeatureDefinitionFeatureDefinitionPost):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, str]]
    """

    kwargs = _get_kwargs(
        client=client,
        multipart_data=multipart_data,
        owner_id=owner_id,
        feature_group=feature_group,
        feature_definition=feature_definition,
        version=version,
    )

    response = httpx.request(
        verify=client.verify_ssl,
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Client,
    multipart_data: BodyUploadFeatureDefinitionFeatureDefinitionPost,
    owner_id: str,
    feature_group: str,
    feature_definition: str,
    version: str,
) -> Optional[Union[HTTPValidationError, str]]:
    """Upload Feature Definition

    Args:
        owner_id (str):
        feature_group (str):
        feature_definition (str):
        version (str):
        multipart_data (BodyUploadFeatureDefinitionFeatureDefinitionPost):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, str]
    """

    return sync_detailed(
        client=client,
        multipart_data=multipart_data,
        owner_id=owner_id,
        feature_group=feature_group,
        feature_definition=feature_definition,
        version=version,
    ).parsed


async def asyncio_detailed(
    *,
    client: Client,
    multipart_data: BodyUploadFeatureDefinitionFeatureDefinitionPost,
    owner_id: str,
    feature_group: str,
    feature_definition: str,
    version: str,
) -> Response[Union[HTTPValidationError, str]]:
    """Upload Feature Definition

    Args:
        owner_id (str):
        feature_group (str):
        feature_definition (str):
        version (str):
        multipart_data (BodyUploadFeatureDefinitionFeatureDefinitionPost):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, str]]
    """

    kwargs = _get_kwargs(
        client=client,
        multipart_data=multipart_data,
        owner_id=owner_id,
        feature_group=feature_group,
        feature_definition=feature_definition,
        version=version,
    )

    async with httpx.AsyncClient(verify=client.verify_ssl) as _client:
        response = await _client.request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Client,
    multipart_data: BodyUploadFeatureDefinitionFeatureDefinitionPost,
    owner_id: str,
    feature_group: str,
    feature_definition: str,
    version: str,
) -> Optional[Union[HTTPValidationError, str]]:
    """Upload Feature Definition

    Args:
        owner_id (str):
        feature_group (str):
        feature_definition (str):
        version (str):
        multipart_data (BodyUploadFeatureDefinitionFeatureDefinitionPost):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, str]
    """

    return (
        await asyncio_detailed(
            client=client,
            multipart_data=multipart_data,
            owner_id=owner_id,
            feature_group=feature_group,
            feature_definition=feature_definition,
            version=version,
        )
    ).parsed
