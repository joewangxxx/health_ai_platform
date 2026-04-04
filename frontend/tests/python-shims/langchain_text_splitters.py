class RecursiveCharacterTextSplitter:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def split_documents(self, documents):
        return list(documents)
