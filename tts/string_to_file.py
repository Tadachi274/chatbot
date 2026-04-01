#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

#text_file_path
file_path_style_change = "log_style_change.txt"
file_path_simpler = "simpler_log.txt"

class StringFile(object):
    def __init__(self, file_type):
        if file_type == 1:
            self.file_path = file_path_style_change
        elif file_type == 2:
            self.file_path = file_path_simpler

    def add(self, utterance, response):
        with open(self.file_path, 'a', encoding='utf-8') as w_file:
            w_file.write(f"input: {utterance}\n")
            w_file.write(f"output: {response}\n")
            w_file.write("\n")