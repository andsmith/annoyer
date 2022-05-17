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
import time
from scipy.stats import expon
import datetime


class HistoryTracker(object):
    """
    Class to save/load & store results.
    """

    def __init__(self, filename=None, default_alarm_file=None, settings=None):
        """
        :param filename:  load/save to here
        """
        self._start_time = time.time()
        self._default_alarm_file = default_alarm_file
        if filename is None:
            filename = mktemp(suffix="_tracking.json")
            logging.warning("No filename given for tracker, creating temp file:  %s" % (filename,))
        self._filename = filename

        # data
        self._history, self._settings = None, None

        # load / create defaults
        self._read_data(settings)  # or make empty

    def is_alarmed(self):
        return self.get_current_prob() > self.get_option('p_threshold')

    def get_filename(self):
        return self._filename

    def get_option(self, name):
        return self._settings[name]

    def set_option(self, name, value, no_save=False):
        self._settings[name] = value
        if not no_save:
            self._save_data()
        self.update_tick()  # may trigger change

    def _clear_data(self):
        logging.info("Clearing user data.")
        self.clear_history()
        self._settings = {'sound_filename': None,
                          'show_graph': True,
                          'p_threshold': .66666,
                          'period_sec': 60.0}

    def clear_history(self):
        logging.info("Clearing user history.")
        self._history = {'durations': [],  # how long until user pushed a button
                         'target_durations': [],  # how long until the alarm went off
                         'outcomes': [],  # which button user pushed
                         'early': []}  # pushed before alarm?

    def set_history(self, new_history):
        logging.info("Setting user history.")
        self._history = new_history
        self._save_data()

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

        self._save_data()
        return sound_file

    def _read_data(self, settings=None):
        """
        Read all history/settings in file, or start with blank history.
        :param settings:  dict with settings, use these instead of what's in the file, etc.
        """
        settings = {} if settings is None else settings
        if os.path.exists(self._filename):
            logging.info("Reading user file:  %s " % (self._filename,))
            with open(self._filename, "r") as infile:
                data = json.load(infile)
            self._history, self._settings = data['history'], data['settings']
            self._settings.update(settings)
        else:
            logging.info("User file not found, creating:  %s " % (self._filename,))
            self._clear_data()
            self._settings.update(settings)
            sound_file = self._default_alarm_file
            logging.info("\tusing default sound:  %s" % (sound_file,))
            self.set_option('sound_filename', sound_file)

        logging.info("User data:")
        logging.info("\thistory contains %i entries." % (len(self._history['durations']),))
        logging.info("\tsettings:\n\t\t\t%s" % (
            "\n\t\t\t".join(["%s: %s" % (key, self._settings[key]) for key in self._settings])))

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

    def get_elapsed_seconds(self):
        now = time.time()
        sec_elapsed = now - self._start_time
        return sec_elapsed

    def get_current_prob(self):
        period_sec = self.get_option('period_sec')
        lambda_par = 1.0 / period_sec
        current_prob = 1.0 - np.exp(-lambda_par * self.get_elapsed_seconds())
        return current_prob

    def predict_alarm_wait_time(self):
        """
        Inverse Exponential CDF(prob) = t such that p(success in time T)=prob
        """
        duration = expon.ppf(self.get_option('p_threshold'), loc=0, scale=self.get_option('period_sec'))
        return duration

    def restart_period(self):
        self._start_time = time.time()

    def update_tick(self):
        """
        re-estimate probabilities
        """
        pass

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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    filename = sys.argv[-1] if len(sys.argv) > 1 else None
    t = HistoryTracker(filename)
