import base64
import hashlib
import hmac
import json
import re
import time

from os import environ
from urllib import parse, request

import arc.tables

SLACK_API_BASE_URL = "https://slack.com/api/"
SLACK_OAUTH_ACCESS_TOKEN = environ["SLACK_OAUTH_ACCESS_TOKEN"]
SLACK_SIGNING_SECRET = environ["SLACK_SIGNING_SECRET"]

# https://api.slack.com/authentication/verifying-requests-from-slack#a_recipe_for_security
def validate_slack_request(headers, body):
    if "X-Slack-Request-Timestamp" not in headers or "X-Slack-Signature" not in headers:
        return False
    timestamp = headers["X-Slack-Request-Timestamp"]
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False
    sig_basestring = "v0:" + timestamp + ":" + body
    req_hash = (
        "v0="
        + hmac.new(
            str.encode(SLACK_SIGNING_SECRET), str.encode(sig_basestring), hashlib.sha256
        ).hexdigest()
    )
    if not hmac.compare_digest(req_hash, headers["X-Slack-Signature"]):
        return False
    return True


# https://api.slack.com/web#basics
def _slack_api_call(url, data):
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


def post_slack_message(channel, text):
    data = {
        "channel": channel,
        "text": text,
    }
    _slack_api_call("{}{}".format(SLACK_API_BASE_URL, "chat.postMessage"), data)


def get_slack_users_list(cursor=None):
    users = []
    data = {}
    if cursor:
        data["cursor"] = cursor
    res = json.loads(
        _slack_api_call("{}{}".format(SLACK_API_BASE_URL, "users.list"), data).decode(
            "utf-8"
        )
    )
    if res.get("members"):
        users += res["members"]
    if res.get("response_metadata", {}).get("next_cursor", None):
        users += get_slack_users_list(res["response_metadata"]["next_cursor"])
    return users


def is_slack_user_id(s):
    return re.match("<@((U|W)\w+)>", s)


def handler(req, context):
    body = req.get("body", "")
    if not body:
        body = "{}"
    if req.get("isBase64Encoded"):
        # decode but don't parse to json before validating the signature
        body = base64.b64decode(body).decode("utf-8")

    # validate signature
    if not validate_slack_request(req.get("headers"), body):
        return {"statusCode": 401}

    body = json.loads(body)

    # https://api.slack.com/events/url_verification
    if body and "challenge" in body:
        return {
            "headers": {
                "cache-control": "no-cache, no-store, must-revalidate, max-age=0, s-maxage=0",
                "content-type": "text/json; charset=utf8",
            },
            "statusCode": 200,
            "body": json.dumps({"challenge": body["challenge"]}),
        }

    event = body.get("event", {})
    event_bot_id = event.get("bot_id", None)
    event_channel = event.get("channel", None)
    event_type = event.get("type", None)
    event_subtype = event.get("subtype", None)
    event_text = event.get("text", None)
    event_user = "<@{}>".format(event.get("user", None))
    # only respond to messages, that also aren't from bots, and that do contains ++ or --
    if event_type == "message" and (
        event_subtype != "bot_message" and not event_bot_id
    ):
        print(event_text)
        event_text_matches = [
            re.sub('"|"|"', "", m[0])
            for m in re.findall(r'((\s+|".*"|".*")?(\+\+|--))', event_text)
        ]
        if event_text_matches:
            print(f"event_text_matches: {event_text_matches}")
            for i in event_text_matches:
                delta = 1
                if re.findall(r"\s?\-\-$", i):
                    delta = -1
                i = re.sub(r"\s?\+\+", "", i)
                i = re.sub(r"\s?\-\-", "", i)

                # look up potential users
                if is_slack_user_id(i):
                    users_table = arc.tables.table(tablename="users")
                    ddb_item = users_table.get_item(Key={"id": i})
                    print(f"user tables: {users_table}")
                    if "Item" in ddb_item:
                        item = ddb_item["Item"]
                        print(f"ddb_item[Item]: {ddb_item['Item']}")
                        print(f"is_slack_user_id (i) - before: {i}")
                        i = item["name"]
                        print(f"is_slack_user_id (i) - after: {i}")

                # don't allow for modification of self-karma
                print(f"i: {i}")
                print(f"event_user: {event_user}")
                if i == event_user:
                    response_text = "{}, {}".format(
                        "Let go of your ego!!"
                        if delta > 0
                        else "Hang on to your ego!!",
                        event_user,
                    )
                # get and modify karma
                else:
                    karma_table = arc.tables.table(tablename="karma")
                    ddb_item = karma_table.get_item(Key={"entity": i})
                    item = {}
                    if "Item" in ddb_item:
                        item = ddb_item["Item"]
                        item["karma"] += delta
                    else:
                        item = {"entity": i, "karma": delta}
                    karma_table.put_item(Item=item)
                    response_text = "_New karma for_ *{}* `{}`".format(i, item["karma"])
                # post to channel
                post_slack_message(event_channel, response_text)
        # reload all users
        elif event_text == "shibboleth reload":
            users = get_slack_users_list()
            users_table = arc.tables.table(tablename="users")
            for i in users:
                if i.get("name"):
                    item = {
                        "name": i["name"],
                        "id": "<@{}>".format(i["id"]),
                    }
                    users_table.put_item(Item=item)
            post_slack_message(event_channel, "Reloaded {} users".format(len(users)))
    return {"statusCode": 200}
