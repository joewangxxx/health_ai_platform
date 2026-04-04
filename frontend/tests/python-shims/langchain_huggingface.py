class HuggingFaceEmbeddings:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def embed_query(self, text):
        return []

    def embed_documents(self, texts):
        return [[] for _ in texts]

