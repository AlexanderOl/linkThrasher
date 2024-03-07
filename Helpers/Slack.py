import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class Slack:
    def __init__(self):
        slack_token = os.environ.get("slack_token")
        self._channel_id = "r04chf4ck"
        self._client = WebClient(token=slack_token)

    def send_msg(self, msg: str):
        try:
            self._client.chat_postMessage(channel=self._channel_id, text=msg)
        except SlackApiError as e:
            print(f"Slack ERROR: {e.response['error']}")
