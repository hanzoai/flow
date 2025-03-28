from typing_extensions import override

from hanzoflow.services.factory import ServiceFactory
from hanzoflow.services.task.service import TaskService


class TaskServiceFactory(ServiceFactory):
    def __init__(self) -> None:
        super().__init__(TaskService)

    @override
    def create(self):
        # Here you would have logic to create and configure a TaskService
        return TaskService()
