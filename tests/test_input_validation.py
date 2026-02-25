import unittest
import sys
from unittest.mock import MagicMock

class TestInputValidation(unittest.TestCase):
    def setUp(self):
        # Create mocks
        self.mock_discord = MagicMock()
        self.mock_discord_ui = MagicMock()
        self.mock_text_input = MagicMock()

        # Define a real class for Modal so subclasses work as expected
        class MockModal:
            def __init_subclass__(cls, **kwargs):
                pass
            def __init__(self, *args, **kwargs):
                pass
            def add_item(self, item):
                pass

        self.mock_discord_ui.Modal = MockModal
        self.mock_discord_ui.TextInput = self.mock_text_input
        self.mock_discord.ui = self.mock_discord_ui

        # Mock modules
        sys.modules['discord'] = self.mock_discord
        sys.modules['discord.ui'] = self.mock_discord_ui
        sys.modules['discord.ext'] = MagicMock()
        sys.modules['discord.ext.tasks'] = MagicMock()
        sys.modules['discord.ext.commands'] = MagicMock()
        sys.modules['discord.app_commands'] = MagicMock()
        sys.modules['dotenv'] = MagicMock()
        sys.modules['database'] = MagicMock()
        sys.modules['giphy_client'] = MagicMock()

        # Reload bot to apply mocks and re-execute class definitions
        if 'bot' in sys.modules:
            del sys.modules['bot']
        import bot
        self.bot = bot

    def test_reminder_modal_event_name_length(self):
        # Check ReminderModal (class level)
        # Note: Since we reload bot, the class definition runs again.
        # We check the calls made during import/class definition.

        calls = self.mock_text_input.call_args_list

        found = False
        for call in calls:
            kwargs = call.kwargs
            if kwargs.get('label') == 'Event Name':
                # We might find multiple calls (one from ReminderModal, one from EditReminderModal probably not instantiated yet but maybe referenced?)
                # Actually, both classes are defined at import time.
                # ReminderModal defines event_name at class level.
                # EditReminderModal defines event_name in __init__.

                # So we expect to find the one from ReminderModal here.
                # If we find one, we check it.
                if 'placeholder' in kwargs: # ReminderModal has placeholder
                     self.assertEqual(kwargs.get('max_length'), 100, "ReminderModal Event Name should have max_length=100")
                     found = True

        self.assertTrue(found, "ReminderModal Event Name input not found")

    def test_edit_reminder_modal_event_name_length(self):
        # Clear previous calls from import
        self.mock_text_input.reset_mock()

        try:
            modal = self.bot.EditReminderModal(1, "Test", "12:00")
        except Exception as e:
            self.fail(f"Failed to instantiate EditReminderModal: {e}")

        calls = self.mock_text_input.call_args_list
        found = False
        for call in calls:
            kwargs = call.kwargs
            if kwargs.get('label') == 'Event Name':
                self.assertEqual(kwargs.get('max_length'), 100, "EditReminderModal Event Name should have max_length=100")
                found = True

        self.assertTrue(found, "EditReminderModal Event Name input not found")

if __name__ == '__main__':
    unittest.main()
