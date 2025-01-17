import asyncio
from unittest.mock import Mock

import pytest

from toga.handlers import AsyncResult, NativeHandler, wrapped_handler


def test_noop_handler():
    """None can be wrapped as a valid handler"""
    obj = Mock()

    wrapped = wrapped_handler(obj, None)

    assert wrapped._raw is None

    # This does nothing, but doesn't raise an error.
    wrapped("arg1", "arg2", kwarg1=3, kwarg2=4)


def test_function_handler():
    """A function can be used as a handler"""
    obj = Mock()
    handler_call = {}

    def handler(*args, **kwargs):
        handler_call["args"] = args
        handler_call["kwargs"] = kwargs

    wrapped = wrapped_handler(obj, handler)

    # Raw handler is the original function
    assert wrapped._raw == handler

    # Invoke wrapper
    wrapped("dummy", "arg1", "arg2", kwarg1=3, kwarg2=4)

    # Handler arguments are as expected.
    assert handler_call == {
        "args": (obj, "arg1", "arg2"),
        "kwargs": {"kwarg1": 3, "kwarg2": 4},
    }


def test_function_handler_error(capsys):
    """A function handler can raise an error"""
    obj = Mock()
    handler_call = {}

    def handler(*args, **kwargs):
        handler_call["args"] = args
        handler_call["kwargs"] = kwargs
        raise Exception("Problem in handler")

    wrapped = wrapped_handler(obj, handler)

    assert wrapped._raw == handler

    # Invoke handler. The exception is swallowed
    wrapped("dummy", "arg1", "arg2", kwarg1=3, kwarg2=4)

    # Handler arguments are as expected.
    assert handler_call == {
        "args": (obj, "arg1", "arg2"),
        "kwargs": {"kwarg1": 3, "kwarg2": 4},
    }

    # Evidence of the handler error is in the log.
    assert (
        "Error in handler: Problem in handler\nTraceback (most recent call last):\n"
        in capsys.readouterr().err
    )


def test_function_handler_with_cleanup():
    """A function handler can have a cleanup method"""
    obj = Mock()
    cleanup = Mock()
    handler_call = {}

    def handler(*args, **kwargs):
        handler_call["args"] = args
        handler_call["kwargs"] = kwargs
        return 42

    wrapped = wrapped_handler(obj, handler, cleanup=cleanup)

    # Raw handler is the original function
    assert wrapped._raw == handler

    # Invoke handler
    wrapped("dummy", "arg1", "arg2", kwarg1=3, kwarg2=4)

    # Handler arguments are as expected.
    assert handler_call == {
        "args": (obj, "arg1", "arg2"),
        "kwargs": {"kwarg1": 3, "kwarg2": 4},
    }

    # Cleanup method was invoked
    cleanup.assert_called_once_with(obj, 42)


def test_function_handler_with_cleanup_error(capsys):
    """A function handler can have a cleanup method that raises an error."""
    obj = Mock()
    cleanup = Mock(side_effect=Exception("Problem in cleanup"))
    handler_call = {}

    def handler(*args, **kwargs):
        handler_call["args"] = args
        handler_call["kwargs"] = kwargs
        return 42

    wrapped = wrapped_handler(obj, handler, cleanup=cleanup)

    # Raw handler is the original function
    assert wrapped._raw == handler

    # Invoke handler. The exception in cleanup is swallowed
    wrapped("dummy", "arg1", "arg2", kwarg1=3, kwarg2=4)

    # Handler arguments are as expected.
    assert handler_call == {
        "args": (obj, "arg1", "arg2"),
        "kwargs": {"kwarg1": 3, "kwarg2": 4},
    }

    # Cleanup method was invoked
    cleanup.assert_called_once_with(obj, 42)

    # Evidence of the handler cleanup error is in the log.
    assert (
        "Error in handler cleanup: Problem in cleanup\nTraceback (most recent call last):\n"
        in capsys.readouterr().err
    )


def test_generator_handler():
    """A generator can be used as a handler"""
    obj = Mock()
    handler_call = {}

    loop = asyncio.new_event_loop()

    def handler(*args, **kwargs):
        handler_call["args"] = args
        handler_call["kwargs"] = kwargs
        yield 0.01  # A short sleep
        handler_call["slept"] = True
        yield  # A yield without a sleep
        handler_call["done"] = True

    wrapped = wrapped_handler(obj, handler)

    # Raw handler is the original generator
    assert wrapped._raw == handler

    # Invoke wrapper inside an active run loop.
    async def waiter():
        wrapped("dummy", "arg1", "arg2", kwarg1=3, kwarg2=4)
        count = 0
        while not handler_call.get("done", False) and count < 5:
            await asyncio.sleep(0.01)
            count += 1

    loop.run_until_complete(waiter())

    # Handler arguments are as expected.
    assert handler_call == {
        "args": (obj, "arg1", "arg2"),
        "kwargs": {"kwarg1": 3, "kwarg2": 4},
        "slept": True,
        "done": True,
    }


def test_generator_handler_error(capsys):
    """A generator can raise an error"""
    obj = Mock()
    handler_call = {}

    loop = asyncio.new_event_loop()

    def handler(*args, **kwargs):
        handler_call["args"] = args
        handler_call["kwargs"] = kwargs
        yield 0.01  # A short sleep
        raise Exception("Problem in handler")

    wrapped = wrapped_handler(obj, handler)

    # Raw handler is the original generator
    assert wrapped._raw == handler

    # Invoke wrapper inside an active run loop.
    async def waiter():
        wrapped("dummy", "arg1", "arg2", kwarg1=3, kwarg2=4)
        count = 0
        while not handler_call.get("done", False) and count < 5:
            await asyncio.sleep(0.01)
            count += 1

    loop.run_until_complete(waiter())

    # Handler arguments are as expected.
    assert handler_call == {
        "args": (obj, "arg1", "arg2"),
        "kwargs": {"kwarg1": 3, "kwarg2": 4},
    }

    # Evidence of the handler cleanup error is in the log.
    assert (
        "Error in long running handler: Problem in handler\nTraceback (most recent call last):\n"
        in capsys.readouterr().err
    )


def test_generator_handler_with_cleanup():
    """A generator can have cleanup"""
    obj = Mock()
    cleanup = Mock()
    handler_call = {}

    loop = asyncio.new_event_loop()

    def handler(*args, **kwargs):
        handler_call["args"] = args
        handler_call["kwargs"] = kwargs
        yield 0.01  # A short sleep
        handler_call["slept"] = True
        yield  # A yield without a sleep
        handler_call["done"] = True
        return 42

    wrapped = wrapped_handler(obj, handler, cleanup=cleanup)

    # Raw handler is the original generator
    assert wrapped._raw == handler

    # Invoke wrapper inside an active run loop.
    async def waiter():
        wrapped("dummy", "arg1", "arg2", kwarg1=3, kwarg2=4)
        count = 0
        while not handler_call.get("done", False) and count < 5:
            await asyncio.sleep(0.01)
            count += 1

    loop.run_until_complete(waiter())

    # Handler arguments are as expected.
    assert handler_call == {
        "args": (obj, "arg1", "arg2"),
        "kwargs": {"kwarg1": 3, "kwarg2": 4},
        "slept": True,
        "done": True,
    }

    # Cleanup method was invoked
    cleanup.assert_called_once_with(obj, 42)


def test_generator_handler_with_cleanup_error(capsys):
    """A generator can raise an error during cleanup"""
    obj = Mock()
    cleanup = Mock(side_effect=Exception("Problem in cleanup"))
    handler_call = {}

    loop = asyncio.new_event_loop()

    def handler(*args, **kwargs):
        handler_call["args"] = args
        handler_call["kwargs"] = kwargs
        yield 0.01  # A short sleep
        handler_call["slept"] = True
        yield  # A yield without a sleep
        handler_call["done"] = True
        return 42

    wrapped = wrapped_handler(obj, handler, cleanup=cleanup)

    # Raw handler is the original generator
    assert wrapped._raw == handler

    # Invoke wrapper inside an active run loop.
    async def waiter():
        wrapped("dummy", "arg1", "arg2", kwarg1=3, kwarg2=4)
        count = 0
        while not handler_call.get("done", False) and count < 5:
            await asyncio.sleep(0.01)
            count += 1

    loop.run_until_complete(waiter())

    # Handler arguments are as expected.
    assert handler_call == {
        "args": (obj, "arg1", "arg2"),
        "kwargs": {"kwarg1": 3, "kwarg2": 4},
        "slept": True,
        "done": True,
    }

    # Cleanup method was invoked
    cleanup.assert_called_once_with(obj, 42)

    # Evidence of the handler cleanup error is in the log.
    assert (
        "Error in long running handler cleanup: Problem in cleanup\nTraceback (most recent call last):\n"
        in capsys.readouterr().err
    )


def test_coroutine_handler():
    """A coroutine can be used as a handler"""
    obj = Mock()
    handler_call = {}

    loop = asyncio.new_event_loop()

    async def handler(*args, **kwargs):
        handler_call["args"] = args
        handler_call["kwargs"] = kwargs
        await asyncio.sleep(0.01)  # A short sleep
        handler_call["done"] = True

    wrapped = wrapped_handler(obj, handler)

    # Raw handler is the original coroutine
    assert wrapped._raw == handler

    # Invoke wrapper inside an active run loop.
    async def waiter():
        wrapped("dummy", "arg1", "arg2", kwarg1=3, kwarg2=4)
        count = 0
        while not handler_call.get("done", False) and count < 5:
            await asyncio.sleep(0.01)
            count += 1

    loop.run_until_complete(waiter())

    # Handler arguments are as expected.
    assert handler_call == {
        "args": (obj, "arg1", "arg2"),
        "kwargs": {"kwarg1": 3, "kwarg2": 4},
        "done": True,
    }


def test_coroutine_handler_error(capsys):
    """A coroutine can raise an error"""
    obj = Mock()
    handler_call = {}

    loop = asyncio.new_event_loop()

    async def handler(*args, **kwargs):
        handler_call["args"] = args
        handler_call["kwargs"] = kwargs
        await asyncio.sleep(0.01)  # A short sleep
        raise Exception("Problem in handler")

    wrapped = wrapped_handler(obj, handler)

    # Raw handler is the original coroutine
    assert wrapped._raw == handler

    # Invoke wrapper inside an active run loop.
    async def waiter():
        wrapped("dummy", "arg1", "arg2", kwarg1=3, kwarg2=4)
        count = 0
        while not handler_call.get("done", False) and count < 5:
            await asyncio.sleep(0.01)
            count += 1

    loop.run_until_complete(waiter())

    # Handler arguments are as expected.
    assert handler_call == {
        "args": (obj, "arg1", "arg2"),
        "kwargs": {"kwarg1": 3, "kwarg2": 4},
    }

    # Evidence of the handler cleanup error is in the log.
    assert (
        "Error in async handler: Problem in handler\nTraceback (most recent call last):\n"
        in capsys.readouterr().err
    )


def test_coroutine_handler_with_cleanup():
    """A coroutine can have cleanup"""
    obj = Mock()
    cleanup = Mock()
    handler_call = {}

    loop = asyncio.new_event_loop()

    async def handler(*args, **kwargs):
        handler_call["args"] = args
        handler_call["kwargs"] = kwargs
        await asyncio.sleep(0.01)  # A short sleep
        handler_call["done"] = True
        return 42

    wrapped = wrapped_handler(obj, handler, cleanup=cleanup)

    # Raw handler is the original coroutine
    assert wrapped._raw == handler

    # Invoke wrapper inside an active run loop.
    async def waiter():
        wrapped("dummy", "arg1", "arg2", kwarg1=3, kwarg2=4)
        count = 0
        while not handler_call.get("done", False) and count < 5:
            await asyncio.sleep(0.01)
            count += 1

    loop.run_until_complete(waiter())

    # Handler arguments are as expected.
    assert handler_call == {
        "args": (obj, "arg1", "arg2"),
        "kwargs": {"kwarg1": 3, "kwarg2": 4},
        "done": True,
    }

    # Cleanup method was invoked
    cleanup.assert_called_once_with(obj, 42)


def test_coroutine_handler_with_cleanup_error(capsys):
    """A coroutine can raise an error during cleanup"""
    obj = Mock()
    cleanup = Mock(side_effect=Exception("Problem in cleanup"))
    handler_call = {}

    loop = asyncio.new_event_loop()

    async def handler(*args, **kwargs):
        handler_call["args"] = args
        handler_call["kwargs"] = kwargs
        await asyncio.sleep(0.01)  # A short sleep
        handler_call["done"] = True
        return 42

    wrapped = wrapped_handler(obj, handler, cleanup=cleanup)

    # Raw handler is the original coroutine
    assert wrapped._raw == handler

    # Invoke wrapper inside an active run loop.
    async def waiter():
        wrapped("dummy", "arg1", "arg2", kwarg1=3, kwarg2=4)
        count = 0
        while not handler_call.get("done", False) and count < 5:
            await asyncio.sleep(0.01)
            count += 1

    loop.run_until_complete(waiter())

    # Handler arguments are as expected.
    assert handler_call == {
        "args": (obj, "arg1", "arg2"),
        "kwargs": {"kwarg1": 3, "kwarg2": 4},
        "done": True,
    }

    # Cleanup method was invoked
    cleanup.assert_called_once_with(obj, 42)

    # Evidence of the handler cleanup error is in the log.
    assert (
        "Error in async handler cleanup: Problem in cleanup\nTraceback (most recent call last):\n"
        in capsys.readouterr().err
    )


def test_native_handler():
    """A native function can be used as a handler"""
    obj = Mock()
    native_method = Mock()

    handler = NativeHandler(native_method)

    wrapped = wrapped_handler(obj, handler)

    # Native method is returned as the handler.
    assert wrapped == native_method


def test_async_result():
    class TestAsyncResult(AsyncResult):
        RESULT_TYPE = "Test"

    result = TestAsyncResult()

    # repr for the result is useful
    assert repr(result) == "<Async Test result; future=<Future pending>>"

    # Result cannot be compared.

    with pytest.raises(
        RuntimeError,
        match=r"Can't check Test result directly; use await or an on_result handler",
    ):
        result == 42

    with pytest.raises(
        RuntimeError,
        match=r"Can't check Test result directly; use await or an on_result handler",
    ):
        result < 42

    with pytest.raises(
        RuntimeError,
        match=r"Can't check Test result directly; use await or an on_result handler",
    ):
        result <= 42

    with pytest.raises(
        RuntimeError,
        match=r"Can't check Test result directly; use await or an on_result handler",
    ):
        result > 42

    with pytest.raises(
        RuntimeError,
        match=r"Can't check Test result directly; use await or an on_result handler",
    ):
        result >= 42

    with pytest.raises(
        RuntimeError,
        match=r"Can't check Test result directly; use await or an on_result handler",
    ):
        result != 42
