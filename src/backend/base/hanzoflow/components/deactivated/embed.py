from hanzoflow.custom import CustomComponent
from hanzoflow.field_typing import Embeddings
from hanzoflow.schema import Data


class EmbedComponent(CustomComponent):
    display_name = "Embed Texts"
    name = "Embed"

    def build_config(self):
        return {"texts": {"display_name": "Texts"}, "embbedings": {"display_name": "Embeddings"}}

    def build(self, texts: list[str], embbedings: Embeddings) -> Data:
        vectors = Data(vector=embbedings.embed_documents(texts))
        self.status = vectors
        return vectors
