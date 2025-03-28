from __future__ import annotations

from typing import TYPE_CHECKING

from typing_extensions import override

from hanzoflow.services.factory import ServiceFactory
from hanzoflow.services.tracing.service import TracingService

if TYPE_CHECKING:
    from hanzoflow.services.settings.service import SettingsService


class TracingServiceFactory(ServiceFactory):
    def __init__(self) -> None:
        super().__init__(TracingService)

    @override
    def create(self, settings_service: SettingsService):
        return TracingService(settings_service)
