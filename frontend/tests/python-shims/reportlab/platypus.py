class SimpleDocTemplate:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def build(self, story):
        self.story = story


class Paragraph:
    def __init__(self, text, style):
        self.text = text
        self.style = style


class Spacer:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class Table:
    def __init__(self, data, *args, **kwargs):
        self.data = data
        self.args = args
        self.kwargs = kwargs

    def setStyle(self, style):
        self.style = style


class TableStyle:
    def __init__(self, commands):
        self.commands = commands


class PageBreak:
    pass


class Image:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class ListFlowable:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class ListItem:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
