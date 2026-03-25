from flow.services.base import Service
from flow.services.factory import ServiceFactory
from flow.services.job_queue.service import JobQueueService


class JobQueueServiceFactory(ServiceFactory):
    def __init__(self):
        super().__init__(JobQueueService)

    def create(self) -> Service:
        return JobQueueService()
