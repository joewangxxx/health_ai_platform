class RetryError(Exception):
    pass


class _Marker:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


def stop_after_attempt(*args, **kwargs):
    return _Marker(*args, **kwargs)


def wait_exponential(*args, **kwargs):
    return _Marker(*args, **kwargs)


def retry_if_exception_type(*args, **kwargs):
    return _Marker(*args, **kwargs)


def retry(*decorator_args, **decorator_kwargs):
    def _decorator(fn):
        return fn

    if decorator_args and callable(decorator_args[0]) and len(decorator_args) == 1 and not decorator_kwargs:
        return decorator_args[0]
    return _decorator
