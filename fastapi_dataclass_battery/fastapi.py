import contextlib
import copy
import threading
import typing

import fastapi
import fastapi.routing
import orjson


_PATCH_ROUTER_LOCK = threading.Lock()


class JSONRequest(fastapi.Request):
    """
    Request class that uses orjson to parse the request body.
    """
    async def json(self) -> typing.Any:
        if not hasattr(self, "_json"):
            body = await self.body()
            self._json = orjson.loads(body)  # noqa
        return self._json


class JSONResponse(fastapi.Response):
    """
    JSON response class that uses orjson to serialize the result content.
    """
    media_type = "application/json"
    orjson_option = orjson.OPT_NON_STR_KEYS | orjson.OPT_NAIVE_UTC | orjson.OPT_UTC_Z

    def render(self, content: typing.Any) -> bytes:
        return orjson.dumps(
            content,
            option=self.orjson_option,
        )


async def _pass_through_serializer(
    *,
    response_content: typing.Any,
    **_,
) -> typing.Any:
    """
    Dummy serializer that makes nothing with the response content.
    :param response_content:
    :param _:
    :return:
    """
    return response_content


@contextlib.contextmanager
def _patch_fastapi_router(
    validate_response: bool = False,
    request_class: typing.Type[fastapi.Request] = JSONRequest,
) -> None:
    """
    Patch that replacing the router class to the one that uses dummy serializer.
    :return:
    """
    original = fastapi.routing.APIRouter

    class _APIRoute(fastapi.routing.APIRoute):
        __init__ = copy.deepcopy(fastapi.routing.APIRoute.__init__)
        get_route_handler = copy.deepcopy(fastapi.routing.APIRoute.get_route_handler)

    # patching "serialize_response"
    if not validate_response:
        _APIRoute.get_route_handler.__globals__.update({"serialize_response": _pass_through_serializer})

    # patching "request_response"
    _request_response = copy.deepcopy(fastapi.routing.request_response)
    _request_response.__globals__.update({"Request": request_class})
    _APIRoute.__init__.__globals__.update({"request_response": _request_response})

    class _APIRouter(fastapi.routing.APIRouter):
        def __init__(
            self,
            *args,
            route_class: typing.Type[_APIRoute] = _APIRoute,
            **kwargs,
        ):
            super().__init__(
                *args,
                route_class=route_class,
                **kwargs,
            )

    try:
        with _PATCH_ROUTER_LOCK:
            fastapi.routing.APIRouter = _APIRouter
            yield
    finally:
        fastapi.routing.APIRouter = original


class FastAPI(fastapi.FastAPI):
    """
    Creates FastAPI app instance that uses orjson to work with json and
    can pass through the endpoint content to response class without validation and modification.
    """
    def __init__(
        self,
        *args,
        request_class: typing.Type[fastapi.Request] = JSONRequest,
        validate_response: bool = False,
        default_response_class: typing.Type[fastapi.Response] = JSONResponse,
        **kwargs,
    ):
        with _patch_fastapi_router(
            validate_response=validate_response,
            request_class=request_class,
        ):
            super().__init__(
                *args,
                default_response_class=default_response_class,
                **kwargs,
            )
