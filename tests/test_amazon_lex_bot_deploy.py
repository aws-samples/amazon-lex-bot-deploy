#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `lex_bot_deploy` package."""


import unittest
import json
import os

from amazon_lex_bot_deploy import amazon_lex_bot_deploy
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class TestLex_bot_deploy(unittest.TestCase):
    """Tests for `lex_bot_deploy` package."""

    def setUp(self):
        """Set up test fixtures, if any."""
        with open(os.path.join(SCRIPT_DIR, 'ScheduleAppointment_Export-Lambda_Endpoint.json')) as lex_schema_file:
            self.schedule_appointment_json_schema = json.load(lex_schema_file)

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_something(self):
        """Test something."""
        assert len(amazon_lex_bot_deploy.get_lambda_endpoints(full_schema=self.schedule_appointment_json_schema)) == 1

