import unittest
from event_handler import EventHandler


class TestEventHandler(unittest.TestCase):
    def setUp(self):
        self.event_handler = EventHandler()

    def test_delta_simple_parsing(self):
        self.assertEqual(1, self.event_handler._get_delta("test.user ++"))
        self.assertEqual(-1, self.event_handler._get_delta("test.user --"))

    def test_delta_message_with_karma(self):
        self.assertEqual(
            1, self.event_handler._get_delta("test.user ++ he's a great guy")
        )
        self.assertEqual(
            -1, self.event_handler._get_delta("test.user -- he's a great guy")
        )

    def test_get_user_string(self):
        self.assertEqual(
            "test.user", self.event_handler._get_user_string("test.user ++")
        )
        self.assertEqual(
            "test.user", self.event_handler._get_user_string("test.user++")
        )
        self.assertEqual(
            "test.user", self.event_handler._get_user_string("test.user --")
        )
        self.assertEqual(
            "test.user", self.event_handler._get_user_string("test.user--")
        )

    def test_get_user_string_with_message(self):
        self.assertEqual(
            "test.user",
            self.event_handler._get_user_string("test.user ++ he's the best"),
        )
        self.assertEqual(
            "test.user",
            self.event_handler._get_user_string("test.user++ he's the best"),
        )
        self.assertEqual(
            "test.user",
            self.event_handler._get_user_string("test.user --he's the best"),
        )
        self.assertEqual(
            "test.user",
            self.event_handler._get_user_string("test.user-- he's the best"),
        )
