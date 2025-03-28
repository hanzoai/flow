from fastapi_pagination import Page

from hanzoflow.helpers.base_model import BaseModel
from hanzoflow.services.database.models.flow.model import Flow
from hanzoflow.services.database.models.folder.model import FolderRead


class FolderWithPaginatedFlows(BaseModel):
    folder: FolderRead
    flows: Page[Flow]
