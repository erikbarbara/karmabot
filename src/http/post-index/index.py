import base64
import json

from event import Event
from event_handler import EventHandler
from slack_api import SlackApi


def handler(request, context):
    slack_api = SlackApi()
    event_handler = EventHandler(slack_api)
    request_body = get_request_body(request)

    try:
        if slack_api.event_needs_verification(request_body):
            return slack_api.verify_event(request_body)

        if not slack_api.validate_slack_request(request.get("headers"), request_body):
            return {"statusCode": 401}

        event = make_event(request_body)

        # if event_handler.duplicate_message(event):
        #     return {"statusCode": 200}
        # return {"statusCode": 409}

        if not event_handler.valid_message(event):
            return {"statusCode": 400}

        event_handler.handle_message(event)
        event_handler.log_message(event)

        return {"statusCode": 200}
    except Exception as error:
        print(f"error: {error}")
        return {"statusCode": 400}


def get_request_body(request):
    body = request.get("body", "{}")
    if request.get("isBase64Encoded"):
        # decode but don't parse to json before validating the signature
        body = base64.b64decode(body).decode("utf-8")
    return body


def make_event(request_body):
    request_body = json.loads(request_body)
    event = request_body.get("event", {})
    print(f"event: {event}")

    return Event(
        bot_id=event.get("bot_id"),
        channel=event.get("channel"),
        type=event.get("type"),
        subtype=event.get("subtype"),
        text=event.get("text"),
        user=event.get("user"),
        ts=event.get("ts"),
    )
