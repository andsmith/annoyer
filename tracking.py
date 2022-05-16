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

    def __init__(self, filename, settings=None):
        """
        :param filename:  load/save to here
        """

        self._filename = filename
        self._history, self._settings = None, None
        self._clear_data()
        self._read_data()  # or make empty
        if settings is None:
            self._settings.update(settings)

    def get_option(self, name):
        return self._settings[name]

    def set_option(self, name, value):
        self._settings[name] = value

    def _clear_data(self):
        logging.info("Clearing user data.")
        self.clear_history()
        self._settings = {'sound_filename': None,
                          'show_graph': False}

    def clear_history(self):
        logging.info("Clearing user history.")
        self._history = {'durations': [],
                         'outcomes': [],
                         'early': []}

    def set_history(self, new_history):
        logging.info("Setting user history.")
        self._history = new_history
        self._save_data()

    def select_new_sound_file(self):
        filetypes = (('wav files', '*.wav'),
                     ('mp3 files', '*.mp3'),
                     ('all files', '*.*'))
        sound_file = fd.askopenfilename(title='Select alarm sound to play...',
                                        filetypes=filetypes,
                                        initialdir='.')

        if sound_file is None or len(sound_file) == 0:
            logging.warning("No alarm sound selected, alarm will not sound!")
            sound_file = None
        else:
            logging.info("Selected sound file:  %s" % (self._settings['sound_filename'],))

        self._settings['sound_filename'] = sound_file
        self._save_data()
        return sound_file

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
            self._clear_data()
            self.select_new_sound_file()
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
