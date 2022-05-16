"""
App to get your attention, for the easily distracted.
"""
import tkinter as tk
import os
import logging
from threading import Event
from panel_thermometer import ThermometerPane
from panel_buttons import StoplightPane
from panel_stats import StatsPane
import time
import datetime
from scipy.stats import expon
from app_states import AnnoyerAppStates
import numpy as np
import simpleaudio as sa

from tracking import HistoryTracker


class AnnoyerApp(object):
    """
    Main app
    """
    COL_WEIGHTS = {"thermometer": 1,
                   "stoplight": 1,
                   "graph": 2, }
    HISTORY_FILE = "history.json"

    def __init__(self, show_graph_pane=True, init_thresh=0.6666, init_period_sec=10 * 60.0, delta_t_sec=.1):
        """
        Start app
        :param show_graph_pane:  Start showing graph if True
        :param init_thresh:  Initial probability to set off alarm
        :param init_period_sec:  Initial base rate of distraction
        :param delta_t_sec:  For updating UI
        """
        self._delta_t_sec = delta_t_sec
        self._root = tk.Tk()
        self._start_time, self._alarm_time = None, None
        self._state = AnnoyerAppStates.WAITING
        self._play_obj = None
        self._root.title("Annoyer!")
        self._thresh = init_thresh
        self._ui_wait = Event()
        self._show_graph_pane = show_graph_pane

        self._tracker = HistoryTracker(self.HISTORY_FILE)
        self._sound_file = self._tracker.get_sound_filename()
        if not os.path.exists(self._sound_file):
            raise Exception("Sound file not found:  %s" % (self._sound_file,))
        logging.info("App got sound file:  %s" % (self._sound_file,))
        self._wave_obj = sa.WaveObject.from_wave_file(self._sound_file)
        self._stats_pane = None
        self._thermometer_pane = ThermometerPane(self._root, thresh_prob=self._thresh, callback=self._adjust_threshold)
        self._stoplight_pane = StoplightPane(self._root, callback=self._handle_buttons)
        self._button_frame = self._stoplight_pane.get_pane_object()['bottom']
        self._setup_buttons()
        self._root.columnconfigure(0, weight=self.COL_WEIGHTS['thermometer'])
        self._root.columnconfigure(1, weight=self.COL_WEIGHTS['stoplight'])
        self._period_sec = init_period_sec

        self._update_functions = [self._thermometer_pane.update,
                                  self._stoplight_pane.update]  # stats panel not updated in real time

        self._root.columnconfigure(0, weight=self.COL_WEIGHTS['thermometer'])
        self._root.columnconfigure(1, weight=self.COL_WEIGHTS['stoplight'])
        if self._show_graph_pane:
            self._stats_pane = StatsPane(self._root)
            self._stats_pane.update_result(self._tracker.get_history())
            self._root.columnconfigure(2, weight=self.COL_WEIGHTS['graph'])

        self._root.rowconfigure(0, weight=1)
        self.reset()
        self._clock()

    def _setup_buttons(self):
        """
        Add buttons for main app.
        """
        self._show_graph_button = tk.Button(master=self._button_frame,
                                            text="Hide / show graph -->",
                                            command=self._toggle_graph)
        self._show_graph_button.grid(column=0, row=0, ipadx=5, ipady=4, padx=8, pady=6)
        self._button_frame.columnconfigure(0, weight=1)
        self._button_frame.rowconfigure(0, weight=1)

    def _toggle_graph(self):
        """
        Show/hide graph part of app
        """
        if self._show_graph_pane:
            self._show_graph_pane = False
            self._stats_pane.deactivate()
            del self._stats_pane
        else:
            self._show_graph_pane = True
            self._stats_pane = StatsPane(self._root)
            self._stats_pane.update_result(self._tracker.get_history())
            self._root.columnconfigure(2, weight=self.COL_WEIGHTS['graph'])

    def _clock(self):
        """
        Tick forever.
        """
        self._tick()
        self._root.after(int(self._delta_t_sec * 1000), self._clock)  # schedule next tick.

    def _sound_alarm(self):
        self._play_obj = self._wave_obj.play()
        self._state = AnnoyerAppStates.ALARMING

    def _stop_alarm(self):
        self._play_obj.stop()
        self._state = AnnoyerAppStates.WAITING

    def reset(self):
        """
        Stop counting down to distraction, reset timer, etc.
        """
        self._start_time = time.time()
        self._alarm_time = self._start_time + self._period_sec
        self._state = AnnoyerAppStates.WAITING
        self._tick()  # force re-draw

    def _predict_time_remaining(self, total_sec, elapsed_sec):
        """
        Inverse Exponential CDF(prob) = t such that p(success in time T)=prob
        """
        lambda_par = total_sec
        t = expon.ppf(self._thresh, loc=0, scale=lambda_par)
        return np.ceil(t - elapsed_sec)

    def _tick(self):
        """
        Called by timer to update app:
            Update all panes.
            Check if it's time for the alarm.
        """
        now = time.time()
        sec_elapsed = now - self._start_time
        time_remaining = datetime.timedelta(seconds=self._predict_time_remaining(self._period_sec, sec_elapsed))
        if time_remaining < datetime.timedelta(seconds=0.0):
            time_remaining = datetime.timedelta(seconds=0.0)
        time_elapsed = datetime.timedelta(seconds=sec_elapsed)
        period_sec = datetime.timedelta(seconds=self._period_sec)
        update_info = {'elapsed_sec': sec_elapsed,
                       'period_sec': self._period_sec,
                       'period_str': str(period_sec - datetime.timedelta(microseconds=period_sec.microseconds)),
                       'elapsed_time_str': str(
                           time_elapsed - datetime.timedelta(microseconds=time_elapsed.microseconds)),
                       'countdown_str': str(
                           time_remaining - datetime.timedelta(microseconds=time_remaining.microseconds)),
                       'state': self._state}

        for update_func in self._update_functions:
            update_func(update_info)
        self._check_for_alarm()

    def _check_for_alarm(self):
        """
        See if it's time, and change state appropriately, etc.
        If we're in an alarm state, and ran out of sound, start it again
        """
        if self._state == AnnoyerAppStates.WAITING:
            if self._thermometer_pane.get_current_prob() > self._thresh:
                self._sound_alarm()
        elif self._state == AnnoyerAppStates.ALARMING:
            if self._thermometer_pane.get_current_prob() <= self._thresh:
                self._stop_alarm()
            else:
                # make sure it's still playing
                if not self._play_obj.is_playing():
                    logging.info("Replaying alarm on loop... ")
                    self._play_obj = self._wave_obj.play()

    def _adjust_threshold(self, thresh):
        """
        Set new threshold
        :param thresh:  float, should be in [0, 1)
        """
        # logging.info("Annoyer - Adjusting threshold:  %s" % (thresh,))
        self._thresh = thresh
        self._check_for_alarm()

    def _handle_buttons(self, button):
        """
        User pressed one of the three "stoplight" buttons.
        :param button:  string, in {'red', 'green', 'yellow'}
        """
        duration = time.time() - self._start_time

        if self._state == AnnoyerAppStates.ALARMING:
            self._tracker.update_result(duration_sec=duration, outcome_color=button, is_early=False)

            self._stop_alarm()
            self._update_params(button, alarm_was_on=True)

        elif self._state == AnnoyerAppStates.WAITING:
            self._tracker.update_result(duration_sec=duration, outcome_color=button, is_early=True)
            self._update_params(button, alarm_was_on=False)
        if self._stats_pane is not None:
            self._stats_pane.update_result(history=self._tracker.get_history())
        self.reset()

    def _update_params(self, button, alarm_was_on):
        """
        Adapt rate to button presses.  For new, heuristic, later, Bayesian.

        :param button:  string, in {'red', 'green', 'yellow'}
        :param alarm_was_on:  Was the alarm running (True), or did the user press early (False)?
        """
        if alarm_was_on:
            if button == 'red':
                self._period_sec /= 1.5  # placeholder for bayesian stats...
            elif button == 'green':
                self._period_sec *= 1.5
            elif button == 'yellow':
                pass
        else:
            if button == 'red':
                self._period_sec /= 1.5
            elif button == 'green':
                self._period_sec *= 1.5
            elif button == 'yellow':
                pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = AnnoyerApp(show_graph_pane=False, init_period_sec=60.0)
    tk.mainloop()
