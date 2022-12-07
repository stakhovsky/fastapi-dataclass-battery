import dataclasses
import typing

import dacite
import pydantic.dataclasses
import fastapi
import orjson


_DC = typing.TypeVar('_DC')


@pydantic.dataclasses.dataclass
class ResponseRecord:
    field1: str
    field2: int


@pydantic.dataclasses.dataclass
class ResponseData:
    records: typing.Sequence[ResponseRecord] = dataclasses.field(
        default_factory=list,
    )


def _read_data(
    dc: typing.Type[_DC],
) -> _DC:
    with open('data.json', 'rb') as f:
        return dacite.from_dict(dc, orjson.loads(f.read()))


app = fastapi.FastAPI()


@app.get('/record')
def records() -> ResponseData:
    return _read_data(ResponseData)


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app)
