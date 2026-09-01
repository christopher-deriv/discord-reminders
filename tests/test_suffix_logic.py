import unittest
import sys
from unittest.mock import MagicMock

class TestSuffixLogic(unittest.TestCase):
    def setUp(self):
        # Create mocks
        self.mock_discord = MagicMock()
        self.mock_discord_ui = MagicMock()

        class MockSelect:
            def __init_subclass__(cls, **kwargs):
                pass
            def __init__(self, *args, **kwargs):
                self.placeholder = kwargs.get('placeholder')
                self.options = kwargs.get('options', [])

        class MockSelectOption:
            def __init__(self, *args, **kwargs):
                self.label = kwargs.get('label')
                self.description = kwargs.get('description')
                self.value = kwargs.get('value')

        self.mock_discord_ui.Select = MockSelect
        self.mock_discord_ui.SelectOption = MockSelectOption
        self.mock_discord.ui = self.mock_discord_ui
        self.mock_discord.SelectOption = MockSelectOption

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
        sys.modules['google'] = MagicMock()
        sys.modules['google.cloud'] = MagicMock()
        sys.modules['google.cloud.translate_v2'] = MagicMock()
        sys.modules['google.auth'] = MagicMock()
        sys.modules['google.auth.exceptions'] = MagicMock()

        for mod in list(sys.modules.keys()):
            if 'cogs' in mod or 'bot' in mod:
                del sys.modules[mod]
        import importlib
        import cogs.reminder_cog
        self.reminder_cog = importlib.reload(cogs.reminder_cog)

    def test_monthly_suffix_logic(self):
        test_data = [
            (1, "1st"),
            (2, "2nd"),
            (3, "3rd"),
            (4, "4th"),
            (10, "10th"),
            (11, "11th"),
            (12, "12th"),
            (13, "13th"),
            (21, "21st"),
            (22, "22nd"),
            (23, "23rd"),
            (31, "31st"),
        ]

        for day, expected_suffix in test_data:
            reminders = [(1, "Test Event", "12:00", 123, None, 'monthly', f"2023-01-{day:02d}")]
            edit_select = self.reminder_cog.EditSelect(reminders)
            self.assertTrue(len(edit_select.options) > 0)
            description = edit_select.options[0].description
            expected_desc_part = f" (Monthly on the {expected_suffix})"
            self.assertIn(expected_desc_part, description, f"Day {day} should have suffix {expected_suffix}")

if __name__ == '__main__':
    unittest.main()
