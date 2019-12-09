""" Test for AD API"""
import json
import unittest
from unittest.mock import patch
from timelapse_generator import is_time_between
from datetime import time, datetime

class TestCLI(unittest.TestCase):

   def test_cli(self):
       date = datetime.now().time()
       is_time_between(time(11, 00), time(21, 30), check_time=date)
