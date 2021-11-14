import json
import hashlib
import hmac
import time

from os import environ
from urllib import parse, request

SLACK_API_BASE_URL = "https://slack.com/api/"
SLACK_OAUTH_ACCESS_TOKEN = environ["SLACK_OAUTH_ACCESS_TOKEN"]
SLACK_SIGNING_SECRET = environ["SLACK_SIGNING_SECRET"]


class SlackApi:
    def event_needs_verification(self, body):
        return body and "challenge" in body

    def verify_event(self, body):
        # https://api.slack.com/events/url_verification
        return {
            "headers": {
                "cache-control": "no-cache, no-store, must-revalidate, max-age=0, s-maxage=0",
                "content-type": "text/json; charset=utf8",
            },
            "statusCode": 200,
            "body": json.dumps({"challenge": body["challenge"]}),
        }

    def validate_slack_request(self, headers, body):
        # https://api.slack.com/post_slack_messageauthentication/verifying-requests-from-slack#a_recipe_for_security
        if (
            "X-Slack-Request-Timestamp" not in headers
            or "X-Slack-Signature" not in headers
        ):
            return False
        timestamp = headers["X-Slack-Request-Timestamp"]
        if abs(time.time() - int(timestamp)) > 60 * 5:
            return False
        sig_basestring = "v0:" + timestamp + ":" + body
        req_hash = (
            "v0="
            + hmac.new(
                str.encode(SLACK_SIGNING_SECRET),
                str.encode(sig_basestring),
                hashlib.sha256,
            ).hexdigest()
        )
        if not hmac.compare_digest(req_hash, headers["X-Slack-Signature"]):
            return False
        return True

    def get_slack_users_list(self, cursor=None):
        users = []
        data = {}
        if cursor:
            data["cursor"] = cursor
        res = json.loads(
            self._slack_api_call(
                "{}{}".format(SLACK_API_BASE_URL, "users.list"), data
            ).decode("utf-8")
        )
        if res.get("members"):
            users += res["members"]
        if res.get("response_metadata", {}).get("next_cursor", None):
            users += self.get_slack_users_list(res["response_metadata"]["next_cursor"])
        return users

    def post_slack_message(self, channel, text):
        print("called post_slack_message")
        data = {
            "channel": channel,
            "text": text,
        }
        self._slack_api_call(
            "{}{}".format(SLACK_API_BASE_URL, "chat.postMessage"), data
        )

    def _slack_api_call(self, url, data):
        # https://api.slack.com/web#basics
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data["token"] = SLACK_OAUTH_ACCESS_TOKEN
        data = parse.urlencode(data).encode("utf-8")
        slack_req = request.Request(
            url,
            data=data,
            method="POST",
            headers=headers,
        )
        return request.urlopen(slack_req).read()
