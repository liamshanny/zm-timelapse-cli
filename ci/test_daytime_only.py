""" Test for AD API"""
import json
import unittest
from unittest.mock import patch
import main
from datetime import time, datetime

class TestCLI(unittest.TestCase):

   def test_cli(self):
       date = datetime.now().time()
       main.is_time_between(time(11, 00), time(21, 30), check_time=date)