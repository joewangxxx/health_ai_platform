class XGBoostError(Exception):
    pass


class DMatrix:
    def __init__(self, data=None, label=None, **kwargs):
        self.data = data
        self.label = label
        self.kwargs = kwargs


class Booster:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.attributes = {}
        self.model_state = {}

    def __setstate__(self, state):
        self.model_state = state or {}

    def __getstate__(self):
        return self.model_state

    def predict(self, data, **kwargs):
        if hasattr(data, "__len__"):
            return [0 for _ in range(len(data))]
        return [0]

    def get_score(self, importance_type="weight"):
        return {}

    def save_model(self, *args, **kwargs):
        return None

    def load_model(self, *args, **kwargs):
        return None

    def set_attr(self, **kwargs):
        self.attributes.update(kwargs)

    def attr(self, key):
        return self.attributes.get(key)

    def feature_names(self):
        return []

