import os

import inject
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from Common.Logger import Logger


class Slack:
    def __init__(self):
        slack_token = os.environ.get("slack_token")
        self._channel_id = "r04chf4ck"
        self._client = WebClient(token=slack_token)
        self._logger = inject.instance(Logger)

    def send_msg(self, msg: str):
        try:
            self._client.chat_postMessage(channel=self._channel_id, text=msg)
        except SlackApiError as e:
            self._logger.log_error(f"Slack ERROR: {e.response['error']}")
