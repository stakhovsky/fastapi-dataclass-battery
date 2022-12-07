import pydantic.dataclasses
import pytest

import fastapi_dataclass_battery.dataclasses


@fastapi_dataclass_battery.dataclasses.dataclass
class _Base:
    field1: int = pydantic.dataclasses.Field(
        default=555,
        ge=100,
        le=1000,
    )


@fastapi_dataclass_battery.dataclasses.dataclass
class _FirstChild(_Base):
    field2: str = pydantic.dataclasses.Field(
        max_length=5,
    )


def test_base_default():
    assert _Base().field1 == 555


def test_base_ge():
    with pytest.raises(pydantic.dataclasses.ValidationError):
        _Base(
            field1=99,
        )


def test_base_le():
    with pytest.raises(pydantic.dataclasses.ValidationError):
        _Base(
            field1=1001,
        )


def test_inheritance():
    assert issubclass(_FirstChild, _Base)


def test_first_child_required_field():
    with pytest.raises(pydantic.dataclasses.ValidationError):
        _FirstChild()


def test_first_child_max_length():
    with pytest.raises(pydantic.dataclasses.ValidationError):
        _FirstChild(
            field2='123456',
        )
