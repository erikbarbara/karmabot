import re
import arc.tables

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

    def valid_message(self, event: Event):
        if not event.text:
            return False

        # only respond to messages, that also aren't from bots
        is_message = event.type == "message"
        is_from_human = event.subtype != "bot_message" and not event.bot_id
        return is_message and is_from_human

    def handle_message(self, event: Event):
        if event.text == EventType.RELOAD_USERS:
            self._reload_users(event)
        elif event.text == EventType.LEADERBOARD:
            self._show_leaderboard(event)
            # self.slack_api.post_slack_message(event.channel, "just testing...")
        else:
            self._handle_legacy_karma_actions(event)

    def _reload_users(self, event):
        users = self.slack_api.get_slack_users_list()
        users_table = arc.tables.table(tablename="users")
        for i in users:
            if i.get("name"):
                item = {
                    "name": i["name"],
                    "id": "<@{}>".format(i["id"]),
                }
                users_table.put_item(Item=item)
        self.slack_api.post_slack_message(event.channel, f"Reloaded {len(users)} users")

    def _show_leaderboard(self, event: Event):
        karma_table = arc.tables.table(tablename="karma")
        users_table = arc.tables.table(tablename="users")
        response = users_table.scan()
        users = response["Items"]

        leaderboard = []
        for user in users:
            user_karma = karma_table.get_item(Key={"entity": user["id"]})
            if "Item" not in user_karma:
                continue

            user = User(name=user["name"], karma=user_karma["Item"]["karma"])
            leaderboard.append(user)

        leaderboard.sort(reverse=True, key=lambda u: u.karma)

        formatted_leaderboard = [
            f"{user.karma}, {user.name}" for user in leaderboard
        ].join("/n")

        self.slack_api.post_slack_message(event.channel, formatted_leaderboard)

    def _handle_legacy_karma_actions(self, event):
        actions = self._get_event_actions(event.text)

        if not actions:
            return

        for i in actions:
            delta = 1
            if re.findall(r"\s?\-\-$", i):
                delta = -1
            # hack all the things
            i = i.replace(" ", "")
            i = i.replace("++", "").replace("--", "")
            # endhack
            # look up potential users

            delta *= randrange(100)
            if self._is_slack_user_id(i):
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
            event_user = f"<@{event.user}>"
            print(f"i: {i}")
            print(f"event_user: {event_user}")
            print(f"item: {item['id']}")
            if item["id"] == event_user:
                response_text = "{}, {}".format(
                    "Let go of your ego" if delta > 0 else "Hang on to your ego",
                    event_user,
                )
            # get and modify karma
            else:
                karma_table = arc.tables.table(tablename="karma")
                print(f"What is i: {i}")
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
            self.slack_api.post_slack_message(event.channel, response_text)

    def _get_event_actions(self, event_text):
        event_text = event_text.replace(" ", "")
        return [
            re.sub('"|"|"', "", m[0])
            for m in re.findall(r'((\S+|".*"|".*")(\+\+|--))', event_text)
        ]

    def _is_slack_user_id(self, s):
        return re.match("<@((U|W)\w+)>", s)
