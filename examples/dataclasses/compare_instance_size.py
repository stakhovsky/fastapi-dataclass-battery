import pydantic.dataclasses
import pympler.asizeof
import fastapi_dataclass_battery.dataclasses


@pydantic.dataclasses.dataclass
class _RegularPydanticCls:
    field1: int
    field2: str


@fastapi_dataclass_battery.dataclasses.dataclass
class _PatchedPydanticCls:
    field1: int
    field2: str


def main():
    regular_instance = _RegularPydanticCls(1, 'test')
    patched_instance = _PatchedPydanticCls(1, 'test')

    print(f'Size of regular instance is {pympler.asizeof.asizeof(regular_instance)}')  # 464
    print(f'Size of patched instance is {pympler.asizeof.asizeof(patched_instance)}')  # 144


if __name__ == '__main__':
    main()
