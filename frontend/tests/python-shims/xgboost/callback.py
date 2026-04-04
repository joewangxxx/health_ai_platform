class TrainingCallback:
    pass


class EarlyStopping(TrainingCallback):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

