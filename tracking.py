"""
Track user settings / performance history.
"""
import logging
import numpy as np
import os
import json
from tkinter import filedialog as fd
import sys
import time
from scipy.stats import expon
import datetime


class Settings(object):
    SETTINGS_FILE = "settings.json"

    def __init__(self, filename=None):
        self._filename = filename if filename is not None else Settings.SETTINGS_FILE

        self._load()

    def _load(self):
        if os.path.exists(self._filename):
            logging.info("Reading settings file:  %s " % (self._filename,))
            with open(self._filename, "r") as infile:
                self._settings = json.load(infile)
        else:
            logging.info("Settings file not found, creating with defaults.")
            self._settings = {'sound_filename': "alarm_lo.wav",
                              'show_graph': True,
                              'p_threshold': .66666,
                              'period_sec': 60.0}
            self._save()

        logging.info("\tsettings:\n\t\t\t%s" % (
            "\n\t\t\t".join(["%s: %s" % (key, self._settings[key]) for key in self._settings])))

    def _save(self):
        logging.info("Writing settings file:  %s " % (self._filename,))
        with open(self._filename, "w") as outfile:
            json.dump(self._settings, outfile)

    def get_option(self, name):
        return self._settings[name]

    def set_option(self, name, value, save=True, update_app=True):
        logging.info("Changing option:  %s  ->  %s" % (name, value))
        self._settings[name] = value
        if save:
            self._save()
        if update_app:
            self.update_tick()  # if settings change may trigger app change

    def update_tick(self):
        """
        re-estimate probabilities...
        """
        pass

    def select_new_sound_file(self):

        filetypes = (('wav files', '*.wav'),
                     ('mp3 files', '*.mp3'),
                     ('all files', '*.*'))

        sound_file = fd.askopenfilename(title='Select alarm sound (CANCEL for silent)',
                                        filetypes=filetypes,
                                        initialdir='.')

        if sound_file is None or len(sound_file) == 0:
            logging.warning("No alarm sound selected, alarm will not sound!")
            sound_file = None
        else:
            logging.info("Selected sound file:  %s" % (self._settings['sound_filename'],))

        self._settings['sound_filename'] = sound_file

        self._save()
        return sound_file

    def get_sound_filename(self):
        return self._settings['sound_filename']

    def _set_alarm_sound(self, audio_file):
        self._settings['sound_filename'] = audio_file


class HistoryTracker(object):
    """
    Class to save/load & store results.
    """
    HISTORY_FILE = "history.json"

    def __init__(self, settings, filename=None):
        """
        :param filename:  load/save to here
        """
        self._filename = filename if filename is not None else HistoryTracker.HISTORY_FILE
        self._options = settings
        self._start_time = time.time()
        if not os.path.exists(self._filename):
            logging.warning("No filename given for tracker, creating temp file:  %s" % (self._filename,))

        # data
        self._history, self._settings = None, None

        # load / create defaults
        self._load_history()  # or make empty

    def _load_history(self):
        """
        Read all history/settings in file, or start with blank history.
        """
        if os.path.exists(self._filename):
            logging.info("Reading user history file:  %s " % (self._filename,))
            with open(self._filename, "r") as infile:
                self._history = json.load(infile)
        else:
            logging.info("User history file not found, creating:  %s " % (self._filename,))
            self.clear_history()

        logging.info("User data:")
        logging.info("\thistory contains %i entries." % (len(self._history['durations']),))

    def is_alarmed(self):
        return self.get_current_prob() > self._options.get_option('p_threshold')

    def get_filename(self):
        return self._filename

    def clear_history(self):
        logging.info("Clearing user history.")
        self._history = {'durations': [],  # how long until user pushed a button
                         'target_durations': [],  # how long until the alarm went off
                         'outcomes': [],  # which button user pushed
                         'early': []}  # pushed before alarm?

    def set_history(self, new_history):
        logging.info("Setting user history.")
        self._history = new_history  # are oxymoron variables anti-pep?
        self._save_data()

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

    def get_elapsed_seconds(self):
        now = time.time()
        sec_elapsed = now - self._start_time
        return sec_elapsed

    def get_current_prob(self):
        period_sec = self._options.get_option('period_sec')
        lambda_par = 1.0 / period_sec
        current_prob = 1.0 - np.exp(-lambda_par * self.get_elapsed_seconds())
        return current_prob

    def predict_alarm_wait_time(self):
        """
        Inverse Exponential CDF(prob) = t such that p(success in time T)=prob
        """
        duration = expon.ppf(self._options.get_option('p_threshold'), loc=0,
                             scale=self._options.get_option('period_sec'))
        return duration

    def restart_period(self):
        self._start_time = time.time()

    def update_result(self, outcome_color, old_target_duration, is_early=False):
        """
        Called every time the user ends an undistracted period with a (stoplight) button push.
        :param
        """
        duration_sec = time.time() - self._start_time

        self._history['durations'].append(duration_sec)
        self._history['outcomes'].append(outcome_color)
        self._history['early'].append(is_early)
        self._history['target_durations'].append(old_target_duration)
        self._save_data()
