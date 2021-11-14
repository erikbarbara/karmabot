import re
import hashlib
import arc.tables

import datetime
from enum import Enum
from random import randrange
from event import Event
from user import User


class EventType(Enum):
    RELOAD_USERS = "shibboleth reload"
    LEADERBOARD = "!leaderboard"

    def __eq__(self, other):
        return self.value == other


class EventHandler:
    def __init__(self, slack_api):
        self.slack_api = slack_api
        self.users_table = arc.tables.table(tablename="users")
        self.karma_table = arc.tables.table(tablename="karma")

    def valid_message(self, event: Event):
        if not event.text:
            return False

        # only respond to messages, that also aren't from bots
        is_message = event.type == "message"
        is_from_human = event.subtype != "bot_message" and not event.bot_id
        return is_message and is_from_human

    def duplicate_message(self, event: Event):
        # Compute hash (user + text)
        # string_to_hash = event.user + event.text
        # computed_hash = hashlib.md5(string_to_hash.encode("utf-8")).hexdigest()
        # print(f"computed_hash: {computed_hash}")
        print(f"event: {event}")

        # Check if event already occurred
        event_history_table = arc.tables.table(tablename="events")
        ddb_item = event_history_table.get_item(Key={"id": "1"})
        print(f"item: {ddb_item}")

        if "Item" not in ddb_item:
            # no existing row
            return False

        # if yes, was is in the last 500ms?
        db_event_timestamp = datetime.datetime.fromtimestamp(ddb_item["Item"]["ts"])
        db_event_treshold_timestamp = db_event_timestamp + datetime.timedelta(
            seconds=30
        )
        event_timestamp = datetime.datetime.fromtimestamp(event.ts)
        print(f"db_event_timestamp: {db_event_timestamp}")
        print(f"db_event_treshold_timestamp: {db_event_treshold_timestamp}")
        print(f"event_timestamp: {event_timestamp}")
        return db_event_timestamp < event_timestamp < db_event_treshold_timestamp

    def handle_message(self, event: Event):
        if event.text == EventType.RELOAD_USERS:
            self._reload_users(event)
        elif event.text == EventType.LEADERBOARD:
            self._show_leaderboard(event)
        else:
            self._update_karma(event)

    def _reload_users(self, event):
        users = self.slack_api.get_slack_users_list()
        for user in users:
            if user.get("name"):
                item = {
                    "name": user["name"],
                    "id": "<@{}>".format(user["id"]),
                }
                self.users_table.put_item(Item=item)
        self.slack_api.post_slack_message(event.channel, f"Reloaded {len(users)} users")

    def _show_leaderboard(self, event: Event):
        response = self.users_table.scan()

        leaderboard = []
        users = response["Items"]
        for user in users:
            user_karma = self.karma_table.get_item(Key={"entity": user["id"]})
            if "Item" not in user_karma:
                # Current user has never had karma
                continue

            user = User(name=user["name"], karma=user_karma["Item"]["karma"])
            leaderboard.append(user)
        leaderboard.sort(reverse=True, key=lambda u: u.karma)

        formatted_leaderboard = "\n".join(
            [f"{user.karma}, {user.name}" for user in leaderboard]
        )

        self.slack_api.post_slack_message(
            event.channel, f"Current leaderboard:\n {formatted_leaderboard}"
        )

    def _update_karma(self, event):
        delta = self._get_delta(event.text)
        user_string = self._get_user_string(event.text)
        user = self._get_user(user_string)

        user_id = user["Item"]["id"]
        self_karma = user_id == f"<@{event.user}>"

        if self_karma:
            message = (
                f"Let go of your ego, {user_id}"
                if delta > 0
                else f"Hang on to your ego, {user_id}"
            )
            self.slack_api.post_slack_message(event.channel, message)
        else:
            delta *= randrange(100)
            ddb_item = self.karma_table.get_item(Key={"entity": user_id})

            item = {}
            if "Item" in ddb_item:
                item = ddb_item["Item"]
                item["karma"] += delta
            else:
                # First time karma!!!
                item = {"entity": user_id, "karma": delta}
            self.karma_table.put_item(Item=item)

            response_text = f"_New karma for_ *{user_string}* `{item['karma']}`"
            self.slack_api.post_slack_message(event.channel, response_text)

    def _get_delta(self, text):
        delta = 1
        # match negative karma (--)
        if re.findall(r"\s?\-\-$", text):
            delta = -1
        return delta

    def _get_user_string(self, text):
        text = text.replace(" ", "")
        text = text.replace("++", "").replace("--", "")
        return text

    def _get_user(self, user_text):
        return self.users_table.get_item(Key={"id": user_text})

    def _is_slack_user_id(self, s):
        return re.match("<@((U|W)\w+)>", s)
