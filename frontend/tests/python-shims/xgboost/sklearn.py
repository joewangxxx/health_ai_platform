from .core import Booster


class XGBModel:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self._booster = Booster()

    def fit(self, *args, **kwargs):
        return self

    def predict(self, data, **kwargs):
        if hasattr(data, "__len__"):
            return [0 for _ in range(len(data))]
        return [0]

    def get_booster(self):
        return self._booster

    def save_model(self, *args, **kwargs):
        return None

    def load_model(self, *args, **kwargs):
        return None

    def __setstate__(self, state):
        self.__dict__.update(state or {})

    def __getstate__(self):
        return dict(self.__dict__)


class XGBClassifier(XGBModel):
    pass


class XGBRegressor(XGBModel):
    pass

