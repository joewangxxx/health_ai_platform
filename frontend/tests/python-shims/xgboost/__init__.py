from .core import Booster, DMatrix, XGBoostError
from .sklearn import XGBClassifier, XGBModel, XGBRegressor

__all__ = [
    "Booster",
    "DMatrix",
    "XGBClassifier",
    "XGBModel",
    "XGBRegressor",
    "XGBoostError",
]


class _ShimObject:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        return self.__class__(*args, **kwargs)

    def __getattr__(self, name):
        return self

    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)

    def __iter__(self):
        return iter(())

    def __bool__(self):
        return False


def __getattr__(name):
    return _ShimObject
