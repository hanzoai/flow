from hanzoflow.services.base import Service
from hanzoflow.services.factory import ServiceFactory
from hanzoflow.services.job_queue.service import JobQueueService


class JobQueueServiceFactory(ServiceFactory):
    def __init__(self):
        super().__init__(JobQueueService)

    def create(self) -> Service:
        return JobQueueService()
