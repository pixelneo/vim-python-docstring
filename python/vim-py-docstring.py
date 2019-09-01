#!/usr/bin/env python3
import re
import ast
from string import Template
class MethodDocGenerator:

    def __init__(self, signature):
        self.signature = signature

    def new_docstring(self):  # generates new docstring no matter what
        pass

    def get_doctring(self, context):  # perform suitable docstring action
        pass
