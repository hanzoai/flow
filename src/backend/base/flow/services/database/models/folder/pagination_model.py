from fastapi_pagination import Page

from flow.helpers.base_model import BaseModel
from flow.services.database.models.flow.model import Flow
from flow.services.database.models.folder.model import FolderRead


class FolderWithPaginatedFlows(BaseModel):
    folder: FolderRead
    flows: Page[Flow]
