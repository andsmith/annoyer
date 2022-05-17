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
    DEFAULT_ALARM_FILE = "alarm_lo.wav"

    def __init__(self, settings=None, delta_t_sec=.01):
        """
        Start app.  Params always override loaded values / defaults.
        :param settings:  dict with user settings for tracker (see tracking.HistoryTracker for details)
        :param delta_t_sec:  For updating UI
        """
        # params
        self._delta_t_sec = delta_t_sec

        # UI
        self._root = tk.Tk()
        self._root.title("Annoyer!")

        self._tracker = HistoryTracker(self.HISTORY_FILE, settings=settings, default_alarm_file=self.DEFAULT_ALARM_FILE)

        # state
        self._state = AnnoyerAppStates.WAITING

        # sound
        self._play_obj = None
        self._wave_obj = None

        # UI objects
        self._stats_pane = None
        self._thermometer_pane = ThermometerPane(self._root, tracker=self._tracker, callback=self._adjust_threshold)
        self._stoplight_pane = StoplightPane(self._root, tracker=self._tracker, callback=self._handle_buttons)
        self._button_frame = self._stoplight_pane.get_pane_object()['bottom']

        # To be called on each tick, for UI
        self._update_functions = [self._thermometer_pane.update_tick,
                                  self._stoplight_pane.update_tick]  # stats panel not updated in real time
        # optional UI objects
        if self._tracker.get_option('show_graph'):
            self._stats_pane = self._make_stats_pane()
            self._root.columnconfigure(2, weight=self.COL_WEIGHTS['graph'])

        # layout
        self._root.columnconfigure(0, weight=self.COL_WEIGHTS['thermometer'])
        self._root.columnconfigure(1, weight=self.COL_WEIGHTS['stoplight'])
        self._root.rowconfigure(0, weight=1)

        # finish
        self._setup_ui()
        self.reset()
        self._clock()  # start ticking...

    def _make_stats_pane(self):
        return StatsPane(self._root, grid_col=2, tracker=self._tracker)

    def _restart_timer(self):
        self.reset()
        self._check_for_alarm()


    def _setup_ui(self):
        """
        Add buttons/labels for main app.
        """
        button_params = dict(ipadx=2, ipady=2, padx=2, pady=1)
        text_params = dict(padx=8, pady=12)
        # clear data
        self._clear_data_button = tk.Button(master=self._button_frame,
                                            text="Restart timer.",
                                            command=self._restart_timer)
        self._clear_data_button.grid(column=0, row=0, **button_params, sticky='w')

        # clear data
        self._clear_data_button = tk.Button(master=self._button_frame,
                                            text="Clear data.",
                                            command=self._clear_data)
        self._clear_data_button.grid(column=1, row=0, **button_params, sticky='w')

        # change sound
        self._change_sound_button = tk.Button(master=self._button_frame,
                                              text="Change / mute\nsound.",
                                              command=self._select_new_sound_file)
        self._change_sound_button.grid(column=0, row=1, **button_params, sticky='w')

        # show / hide graph
        self._show_graph_button = tk.Button(master=self._button_frame,
                                            text="Hide / show\ngraph -->",
                                            command=self._toggle_graph)
        self._show_graph_button.grid(column=1, row=1, **button_params, sticky='w')

        # labels
        self._sound_file_label_text = tk.StringVar()

        self._sound_file_label = tk.Label(master=self._button_frame, textvariable=self._sound_file_label_text,
                                            **text_params)
        self._sound_file_label.grid(column=0, row=2, columnspan=2 )
        self._update_ui()

        self._button_frame.columnconfigure(0, weight=1)
        self._button_frame.columnconfigure(1, weight=1)
        self._button_frame.columnconfigure(2, weight=1)
        self._button_frame.rowconfigure(0, weight=2)
        self._button_frame.rowconfigure(1, weight=1)

    def _update_ui(self):
        """
        Text, etc., that needs updating.
        """
        sound_file = self._tracker.get_option('sound_filename')
        button_text = "Alarm sound:  (none/silent)" if sound_file is None else \
            "Alarm sound:  %s" % (os.path.split(sound_file)[1])
        self._sound_file_label_text.set(button_text)
        print(button_text, self._sound_file_label_text.get())

    def _select_new_sound_file(self):
        self._tracker.select_new_sound_file()

        if self._play_obj is not None and self._play_obj.is_playing():
            self._play_obj.stop()
            self._play_obj = None
        self._update_ui()

    def _clear_data(self):
        self._tracker.clear_history()
        if self._stats_pane is not None:
            self._stats_pane.refresh()

    def _toggle_graph(self):
        """
        Show/hide graph part of app
        """
        if self._tracker.get_option('show_graph'):
            self._tracker.set_option('show_graph', False)
            self._stats_pane.deactivate()
            self._stats_pane = None
        else:
            self._tracker.set_option('show_graph', True)
            self._stats_pane = self._make_stats_pane()
            self._root.columnconfigure(2, weight=self.COL_WEIGHTS['graph'])

    def _clock(self):
        """
        Tick forever.
        """
        self._tick()
        self._root.after(int(self._delta_t_sec * 1000), self._clock)  # schedule next tick.

    def _become_alarmed(self):
        self._play_sound()
        self._state = AnnoyerAppStates.ALARMING

    def _play_sound(self):
        if self._tracker.get_option('sound_filename') is not None:
            self._wave_obj = self._wave_obj if self._wave_obj is not None else sa.WaveObject.from_wave_file(
                self._tracker.get_option('sound_filename'))

            if self._play_obj is not None:
                if not self._play_obj.is_playing():
                    logging.info("Replaying alarm on loop... ")
                    self._play_obj = self._wave_obj.play()
            else:

                logging.info("Starting alarm sound...")
                self._play_obj = self._wave_obj.play()

    def _stop_sound(self):
        if self._play_obj is not None:
            self._play_obj.stop()
            self._play_obj = None

    def _become_unalarmed(self):
        self._stop_sound()
        self._state = AnnoyerAppStates.WAITING

    def reset(self):
        """
        Stop counting down to distraction, reset timer, etc.
        """
        self._become_unalarmed()  # in case
        self._tracker.restart_period()
        self._tick()  # force re-draw

    def _tick(self):
        """
        Called by timer to update app:
            Update all panes.
            Check if it's time for the alarm.
        """
        self._tracker.update_tick()
        for update_func in self._update_functions:
            update_func()
        self._check_for_alarm()

    def _check_for_alarm(self):
        """
        See if it's time, and change state appropriately, etc.
        If we're in an alarm state, and ran out of sound, start it again
        """
        if self._state == AnnoyerAppStates.WAITING:
            if self._tracker.is_alarmed():
                self._become_alarmed()
        elif self._state == AnnoyerAppStates.ALARMING:
            if not self._tracker.is_alarmed():
                self._become_unalarmed()
            else:
                self._play_sound()
                # make sure it's still playing

    def _adjust_threshold(self, thresh):
        """
        Set new threshold
        :param thresh:  float, should be in [0, 1)
        """
        # logging.info("Annoyer - Adjusting threshold:  %s" % (thresh,))
        suppress_save = self._thermometer_pane.is_sliding()
        self._tracker.set_option('p_threshold', thresh, no_save=suppress_save)
        self._check_for_alarm()

    def _handle_buttons(self, button):
        """
        User pressed one of the three "stoplight" buttons.
        :param button:  string, in {'red', 'green', 'yellow'}
        """

        # Silence any alarms
        alarm_was_on = self._state == AnnoyerAppStates.ALARMING
        if alarm_was_on:
            self._become_unalarmed()

        old_target_duration = self._tracker.predict_alarm_wait_time()
        self._adapt_params(button, alarm_was_on=alarm_was_on, no_save=True)  # will save in tracker.update_result()
        self._tracker.update_result(outcome_color=button,
                                    old_target_duration=old_target_duration,
                                    is_early=not alarm_was_on)
        if self._stats_pane is not None:
            self._stats_pane.refresh()

        self.reset()

    def _adapt_params(self, button, alarm_was_on, no_save=False):
        """
        Adapt rate to button presses.  For new, heuristic, later, Bayesian.

        :param button:  string, in {'red', 'green', 'yellow'}
        :param alarm_was_on:  Was the alarm running (True), or did the user press early (False)?
        :param no_save: Don't save after setting new period
        """
        period_sec = self._tracker.get_option('period_sec')
        if alarm_was_on:
            if button == 'red':
                period_sec /= 1.5  # placeholder for bayesian stats...
            elif button == 'green':
                period_sec *= 1.5
            elif button == 'yellow':
                pass
        else:
            if button == 'red':
                period_sec /= 1.5
            elif button == 'green':
                period_sec *= 1.5
            elif button == 'yellow':
                pass
        self._tracker.set_option('period_sec', period_sec, no_save=no_save)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = AnnoyerApp()
    tk.mainloop()
