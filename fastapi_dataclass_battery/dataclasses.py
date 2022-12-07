import contextlib
import dataclasses
import functools
import threading
import typing
import sys
import typing_extensions
import warnings

import pydantic.dataclasses


_T = typing.TypeVar("_T")


_DATACLASS_PATCH_LOCK = threading.Lock()
_PYDANTIC_INITIALIZATION_MARKER = "__pydantic_initialised__"
_PYDANTIC_DEFAULTS_MARKER = "__pydantic_has_field_info_default__"


@contextlib.contextmanager
def _extend_dataclass_slots(
    extra: typing.Sequence[str],
) -> None:
    """
    Patches dataclasses internals (dataclasses.fields) to extend the dataclass __slots__.
    """
    class _Field(typing.NamedTuple):
        name: str

    def _fields_patch(original_):
        def _impl(dc_or_instance):
            return [*original_(dc_or_instance), *[_Field(name) for name in extra]]
        return _impl

    original = dataclasses.fields
    try:
        with _DATACLASS_PATCH_LOCK:
            dataclasses.fields = _fields_patch(dataclasses.fields)
            yield
    finally:
        dataclasses.fields = original


def _make_pydantic_ready_dataclass(
    cls_: typing.Type[_T],
    slots: bool = True,
    **kwargs,
) -> typing.Type[_T]:
    """
    Creates a dataclass that contains special pydantic fields
    :param cls_: source class
    :param slots: should the slots to be used
    :param kwargs:
    :return: dataclass
    """
    if not slots:
        warnings.warn('fastapi_dataclass_battery.dataclasses.dataclass has no reasons to use without slots')
        return dataclasses.dataclass(  # noqa
            cls_,
            slots=slots,
            **kwargs,
        )

    with _extend_dataclass_slots(
        extra=(_PYDANTIC_INITIALIZATION_MARKER, ),
    ):
        return dataclasses.dataclass(  # noqa
            cls_,
            slots=slots,
            **kwargs,
        )


def __pydantic_validate_values__(
    self: typing.Any,
) -> None:
    """
    Re-implementation of pydantic.dataclasses._dataclass_validate_values
    that works properly with slotted dataclasses.
    :param self: dataclass instance
    :return:
    """
    if getattr(self, _PYDANTIC_INITIALIZATION_MARKER, False):
        return

    __dict__ = {f.name: getattr(self, f.name) for f in dataclasses.fields(self)}

    if getattr(self, _PYDANTIC_DEFAULTS_MARKER, False):
        input_data = {k: v for k, v in __dict__.items() if not isinstance(v, pydantic.dataclasses.FieldInfo)}
    else:
        input_data = __dict__

    d, _, validation_error = pydantic.dataclasses.validate_model(self.__pydantic_model__, input_data, cls=self.__class__)

    if validation_error:
        raise validation_error

    for key, value in d.items():
        setattr(self, key, value)
    object.__setattr__(self, _PYDANTIC_INITIALIZATION_MARKER, True)


def __dataclass_validate_assignment_setattr__(
    self: typing.Any,
    name: str,
    value: typing.Any,
) -> None:
    """
    Re-implementation of pydantic.dataclasses._dataclass_validate_assignment_setattr
    that works properly with slotted dataclasses.
    :param self: dataclass instance
    :return:
    """
    __dict__ = {f.name: getattr(self, f.name) for f in dataclasses.fields(self)}

    if getattr(self, _PYDANTIC_INITIALIZATION_MARKER, False):
        d = dict(__dict__)
        d.pop(name, None)
        known_field = self.__pydantic_model__.__fields__.get(name, None)
        if known_field:
            value, error_ = known_field.validate(value, d, loc=name, cls=self.__class__)
            if error_:
                raise pydantic.dataclasses.ValidationError([error_], self.__class__)

    object.__setattr__(self, name, value)


def _make_pydantic_dataclass(
    cls_: typing.Type[_T],
    slots: bool = True,
    config: typing.Any = None,
    validate_on_init: bool = True,
    **kwargs,
) -> typing.Type[_T]:
    """
    Creates pydantic.dataclasses.dataclass that works properly with slots.
    :param cls_: source class
    :param slots: should the slots to be used
    :param config: pydantic config
    :param validate_on_init: should the class to be validated on init
    :param kwargs:
    :return: pydantic dataclass
    """
    if not slots:
        warnings.warn('fastapi_dataclass_battery.dataclasses.dataclass has no reasons to use without slots')
        return pydantic.dataclasses.dataclass(
            cls_,
            validate_on_init=validate_on_init,
            config=config,
            **kwargs,
        )

    pydantic_ready_dc = _make_pydantic_ready_dataclass(
        cls_=cls_,
        slots=slots,
        **kwargs,
    )
    # copying member descriptor for initialization marker,
    # so we can add it later to the result class
    pydantic_ready_descriptor = getattr(pydantic_ready_dc, _PYDANTIC_INITIALIZATION_MARKER)

    dc_proxy = pydantic.dataclasses.dataclass(
        pydantic_ready_dc,
        validate_on_init=validate_on_init,
        config=config,
        **kwargs,
    )
    actual_dc = dc_proxy.__dataclass__

    # patch validation call
    actual_dc.__pydantic_validate_values__ = __pydantic_validate_values__
    if actual_dc.__pydantic_model__.__config__.validate_assignment and not actual_dc.__dataclass_params__.frozen:
        # patch validation on attribute change
        actual_dc.__setattr__ = __dataclass_validate_assignment_setattr__
    # re-assign initialization marker descriptor
    actual_dc.__pydantic_initialised__ = pydantic_ready_descriptor

    return actual_dc


@typing_extensions.dataclass_transform(
    field_descriptors=(
        dataclasses.Field,
        pydantic.dataclasses.FieldInfo,
    ),
)
@functools.wraps(pydantic.dataclasses.dataclass)
def dataclass(
    _cls: typing.Optional[typing.Type[_T]] = None,
    slots: bool = True,
    config: typing.Any = None,
    validate_on_init: bool = True,
    **kwargs,
) -> typing.Union[typing.Callable[[typing.Type[_T]], typing.Type[_T]], typing.Type[_T]]:
    """
    Creates slotted pydantic dataclass
    :param _cls: source class
    :param slots: should the slots to be used
    :param config: pydantic config
    :param validate_on_init: should the class to be validated on init
    :param kwargs:
    :return: pydantic dataclass
    """
    if sys.version_info < (3, 10):
        warnings.warn('fastapi_dataclass_battery.dataclasses.dataclass can not be used for Python under 3.10')
        return pydantic.dataclasses.dataclass(
            _cls,
            config=config,
            validate_on_init=validate_on_init,
            **kwargs,
        )

    if not slots:
        warnings.warn('fastapi_dataclass_battery.dataclasses.dataclass has no reasons to use without slots')
        return pydantic.dataclasses.dataclass(
            _cls,
            config=config,
            validate_on_init=validate_on_init,
            **kwargs,
        )

    the_config = pydantic.dataclasses.get_config(config)
    if the_config.extra == pydantic.dataclasses.Extra.allow:
        warnings.warn('fastapi_dataclass_battery.dataclasses.dataclass can not be used with extra values')
        return pydantic.dataclasses.dataclass(
            _cls,
            config=the_config,
            validate_on_init=validate_on_init,
            **kwargs,
        )

    def inner(
        cls_: typing.Type[_T],
    ) -> typing.Type[_T]:
        if dataclasses.is_dataclass(cls_):
            warnings.warn('fastapi_dataclass_battery.dataclasses.dataclass can not be used on dataclass')
            return pydantic.dataclasses.dataclass(
                _cls,
                config=the_config,
                validate_on_init=validate_on_init,
                **kwargs,
            )

        return _make_pydantic_dataclass(
            cls_=cls_,
            slots=slots,
            config=the_config,
            validate_on_init=validate_on_init,
            **kwargs,
        )

    if _cls is None:
        return inner

    return inner(_cls)
