import functools
import multiprocessing
import random
import string
import time
import tracemalloc
import typing

import pydantic.dataclasses
import fastapi_dataclass_battery.dataclasses


class _Cls(typing.Protocol):
    field1: int
    field2: str


@pydantic.dataclasses.dataclass
class _RegularPydanticCls:
    field1: int
    field2: str


@fastapi_dataclass_battery.dataclasses.dataclass
class _PatchedPydanticCls:
    field1: int
    field2: str


def _fetch_allocated_bytes(
    memory_snapshot: tracemalloc.Snapshot,
) -> int:
    top_stats = memory_snapshot.statistics('lineno')
    return sum(stat.size for stat in top_stats)


def _get_dataclass_params(
) -> dict:
    return dict(
        field1=random.randint(1, 100),
        field2=''.join(random.choice(string.ascii_lowercase) for _ in range(10)),
    )


def _measure_dataclass_stats(
    cls_: typing.Type[_Cls],
    count: int = 10_000,
):
    print(f'Checking - {cls_.__name__}')
    tracemalloc.start()
    timer_start = time.time()

    _ = [
        cls_(**_get_dataclass_params())  # noqa
        for _ in range(count)
    ]

    timer_duration = time.time() - timer_start
    allocated_bytes = _fetch_allocated_bytes(
        memory_snapshot=tracemalloc.take_snapshot(),
    )

    print(f'Time spent - {timer_duration:.2f} seconds')
    print(f'Total allocated - {allocated_bytes / 1024:.2f} kilobytes')
    print(f'Check done - {cls_.__name__}')


def main(
    count: int = 10_000,
):
    for cls_ in (_RegularPydanticCls, _PatchedPydanticCls):
        process_ = multiprocessing.Process(
            target=functools.partial(
                _measure_dataclass_stats,
                cls_=cls_,
                count=count,
            ),
        )
        process_.start()
        process_.join()


if __name__ == '__main__':
    main()
