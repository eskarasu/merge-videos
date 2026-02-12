from __future__ import annotations

import json

from channels.generic.websocket import AsyncWebsocketConsumer

from video_merge.presentation.ws_groups import user_jobs_group_name


class JobStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self) -> None:
        user = self.scope.get("user")
        if user is None or user.is_anonymous:
            await self.close()
            return

        self.group_name = user_jobs_group_name(user.id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def job_status_event(self, event: dict[str, object]) -> None:
        payload = event.get("payload", {})
        await self.send(text_data=json.dumps(payload))

