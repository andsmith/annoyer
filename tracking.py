"""
Track user settings / performance history.
"""
import logging
import numpy as np
import os
import json
from tempfile import mktemp
from tkinter import filedialog as fd
import sys


class HistoryTracker(object):
    """
    Class to save/load & store results.
    """

    def __init__(self, filename):
        """
        :param filename:  load/save to here
        """
        self._filename = filename
        self._read_data()

    def _read_data(self):
        """
        Read all history/settings in file, or start with blank history.
        """
        if os.path.exists(self._filename):
            logging.info("Reading user file:  %s " % (self._filename,))
            with open(self._filename, "r") as infile:
                data = json.load(infile)
            self._history, self._settings = data['history'], data['settings']
            logging.info("\tcontains %i entries." % (len(self._history['durations']),))
            logging.info("\talarm sound file:  %s" % (self._settings['sound_filename'],))
        else:
            logging.info("User file not found, creating:  %s " % (self._filename,))
            self._history = {'durations': [],
                             'outcomes': [],
                             'early': []}
            filetypes = (('wav files', '*.wav'),
                         ('mp3 files', '*.mp3'),
                         ('all files', '*.*'))
            self._settings = {
                'sound_filename': fd.askopenfilename(title='Select alarm sound to play...', filetypes=filetypes,
                                                     initialdir='/')
            }
            self._save_data()

    def get_sound_filename(self):
        return self._settings['sound_filename']

    def _set_alarm_sound(self, audio_file):
        self._settings['sound_filename'] = audio_file

    def get_history(self):
        return self._history

    def _save_data(self):
        """
        Write all history/settings to file.
        """
        data = {'history': self._history,
                'settings': self._settings}
        logging.info("Writing user file:  %s " % (self._filename,))
        with open(self._filename, 'w') as outfile:
            json.dump(data, outfile)

    def update_result(self, duration_sec, outcome_color, is_early=False):
        """
        Called every time the user ends an undistracted period with a (stoplight) button push.
        :param
        """

        self._history['durations'].append(duration_sec)
        self._history['outcomes'].append(outcome_color)
        self._history['early'].append(is_early)
        self._save_data()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) > 1:
        filename = sys.argv[-1]
    else:
        filename = mktemp(suffix="_tracking.json")
    t = HistoryTracker(filename)
