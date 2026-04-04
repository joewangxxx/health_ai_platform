class Matrix:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class _Pixmap:
    def tobytes(self, fmt="png"):
        return b""


class _Page:
    def get_pixmap(self, matrix=None):
        return _Pixmap()


class _Document:
    def __init__(self, *args, **kwargs):
        self.page_count = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def load_page(self, index):
        return _Page()


def open(*args, **kwargs):
    return _Document()
