"""
App panel to show statistics / graph of progress
"""

import numpy as np
import time
from panels import Pane, PaneTester
import tkinter as tk
import logging
from app_states import AnnoyerAppStates
import json
import os
from tracking import HistoryTracker
from tempfile import mktemp
import sys


class StatsPane(Pane):
    """
    Class for stats / graph.
    """

    def __init__(self, tk_root, tracker=None, grid_col=2, **kwargs):
        """
        :param tk_root: tk.Tk() object / frame
        :param grid_col: which column of the main app does this pane go into
        :param tracker:  tracking.Tracker() object from main app
        :param kwargs:  additional arguments to Pane
        """
        logging.info("Creating stats pane.")
        self._resize_trigger = 0.95  # shrinking graph for more data
        self._resize_factor = 1.333
        self._shape = (600, 400)
        self._n_bar_spaces = 10
        self._max_bar_width = 6
        super(StatsPane, self).__init__(tk_root,
                                        tracker=tracker,
                                        grid_col=grid_col,
                                        regions=[None,
                                                 self._shape,
                                                 None],
                                        **kwargs)
        self._canvas = self._pane_objects['middle']
        self.refresh()

    LAYOUT = {
        'border_color': 'black',
        'border_width': 3,
        'bar_width': 4,
        'bar_color': 'black',
        'margins': {'top': 0.00,
                    'right': 0.95,
                    'bottom': 0.75,
                    'left': 0.2},
        'legend_pos': (0.15, 0.80),
        'legend_row_spacing': 27,
        'legend_col_spacing': 120,
        'legend_indent': 12,
        'grid_color': 'gray',
        'grid_width': 1,
        'outcome_colors': {'red': 'red',
                           'green': 'green',
                           'yellow': 'yellow',
                           'unknown': None},
        'dot_size': 8,
        'square_size': 7,
        'triangle_base_and_height': (14, 14)}

    def _resize(self, event):
        self._shape = (event.height, event.width)
        self.refresh()

    def update(self, info):
        # graph not updated in real-time  (Ideas..?)
        pass

    def _calc_margins(self):
        """
        Determine extent of graph area
        """
        bw = self.LAYOUT['border_width']

        def _repair(x, dim_ind):
            if x < bw:
                return bw
            elif x >= self._shape[dim_ind] - bw:
                return self._shape[dim_ind] - bw
            return x

        return dict(left=_repair(self.LAYOUT['margins']['left'] * self._shape[1], 1),
                    right=_repair(self.LAYOUT['margins']['right'] * self._shape[1], 1),
                    top=_repair(self.LAYOUT['margins']['top'] * self._shape[0], 0),
                    bottom=_repair(self.LAYOUT['margins']['bottom'] * self._shape[0], 0))

    def _calc_bars(self, y_max, durations):
        """
        Determine x & y coordinates of bars of bar graph.
        """
        if durations.size == 0:
            return np.array([]), np.array([])

        n_bars = len(durations)
        n_bar_spaces = np.max([10, n_bars])
        margins = self._calc_margins()
        x_locs_px = np.linspace(margins['left'], margins['right'], n_bar_spaces + 2)[1:-1]

        y_locs_px = (1.0 - np.array(durations) / y_max) * (margins['bottom'] - margins['top']) + margins['top']
        return x_locs_px, y_locs_px

    def update_period(self, duration_sec, outcome_color, is_early=False):
        """
        This is called by the main app when the user ends an undistracted time-period by pushing a button.
        """
        self._tracker.update_result(duration_sec, outcome_color, is_early=is_early)
        self.refresh()

    def refresh(self):
        """
        redraw everything
        """
        history = self._tracker.get_history()

        bw = self.LAYOUT['border_width']
        margins = self._calc_margins()

        durations = np.array(history['durations']) if history is not None else np.array([])

        y_max = 2. ** (np.ceil(np.log(np.max(durations)) / np.log(2.0))) if durations.size > 0 else 32.0
        y_max = np.max([y_max, 64.0])
        self._canvas.delete('all')
        # draw grid

        ten_pow = np.max([1, np.floor(np.log10(y_max))])

        if y_max / 10. ** ten_pow < 5.0:
            y_grid_scale = 10 ** ten_pow / 4.0
        else:
            y_grid_scale = 10 ** ten_pow
        y_grid_scale = int(y_grid_scale)

        n_grid_lines = int(y_max / y_grid_scale)

        y_grid_locs = np.arange(y_grid_scale, y_max, y_grid_scale)
        if y_grid_locs.size > n_grid_lines:  # coincidence
            y_grid_locs = y_grid_locs[:-1]

        y_grid_locs_px = margins['bottom'] - (y_grid_locs / y_max) * (margins['bottom'] - margins['top'])
        x_grid_locs_left_px = margins['left'] * np.ones(n_grid_lines)
        x_grid_locs_right_px = margins['right'] * np.ones(n_grid_lines)

        def draw_grid(x_left, x_right, y, y_value):
            """
            Draw grid lines on graph, add tick labels.

            :param x_left: x-coordinate of left-side (pixels)
            :param x_right: x-coordinate of right-side (pixels)
            :param y: y-coordinate of grid_line (pixels
            :param y_value: value of y-coordinate (in time units) for writing label
            """
            bar = self._canvas.create_line(x_left, y, x_right, y,
                                           fill=self.LAYOUT['grid_color'],
                                           width=self.LAYOUT['grid_width'])
            tic_label = "%.1f sec. " % (y_value,)
            note = self._canvas.create_text(x_left, y, text=tic_label,
                                            fill=self.LAYOUT['grid_color'],
                                            anchor='e')
            return bar, note

        for i in range(y_grid_locs.size):
            draw_grid(x_grid_locs_left_px[i],
                      x_grid_locs_right_px[i],
                      y_grid_locs_px[i],
                      y_value=y_grid_locs[i])

        # draw border
        self._canvas.create_rectangle(margins['left'], margins['bottom'],
                                      margins['right'], margins['top'],
                                      outline=self.LAYOUT['border_color'],
                                      width=self.LAYOUT['border_width'])

        # draw bars
        px, py = self._calc_bars(y_max, durations=durations)

        def _draw_bar(px, py, color, hide_bar=False, shape='round'):
            """
            Draw a bar for the bar graph, and put a marker on top to indicate which button ended it, and whether or not
            the alarm was sounding.
            :param px: bar is at this x-location
            :param py: bar has this height
            :param color: and this color
            :param hide_bar:  Don't plot the bar itself, just the marker (useful for legend)
            :param shape: one of 'dot' 'square' or 'triangle'
            """

            y0 = int(margins['bottom'])
            p_x = int(px)
            p_y = int(py)
            line = None
            if not hide_bar:
                line = self._canvas.create_line(p_x, y0,
                                                p_x, p_y,
                                                fill=self.LAYOUT['bar_color'],
                                                width=self.LAYOUT['bar_width'])
            fill_color = self.LAYOUT['outcome_colors'][color] if self.LAYOUT['outcome_colors'][color] is not None else \
                self._canvas['background']
            if shape == 'square':
                square_size = self.LAYOUT['square_size']
                marker = self._canvas.create_rectangle(p_x - square_size, p_y - square_size,
                                                       p_x + square_size, p_y + square_size,
                                                       fill=fill_color,
                                                       outline='black',
                                                       width=1)

            elif shape == 'dot':
                dot_size = self.LAYOUT['dot_size']
                marker = self._canvas.create_oval(p_x - dot_size, p_y - dot_size,
                                                  p_x + dot_size, p_y + dot_size,
                                                  fill=fill_color,
                                                  outline='black',
                                                  width=1)
            elif shape == 'triangle':
                triangle_base, triangle_height = self.LAYOUT['triangle_base_and_height']
                coords = [px - triangle_base / 2, py + triangle_height / 2,
                          px + triangle_base / 2, py + triangle_height / 2,
                          px, py - triangle_height / 2]
                marker = self._canvas.create_polygon(*coords,
                                                     fill=fill_color,
                                                     outline='black',
                                                     width=1)
            else:
                raise Exception("Unknown marker shape:  %s" % (shape,))

            return line, marker

        # draw legend
        legend_left = self.LAYOUT['legend_pos'] * np.array(self._shape[::-1])
        row_0_y = legend_left[1]
        row_x = legend_left[0]
        self._canvas.create_text(row_x, row_0_y, text="Legend:")
        rows_y = np.arange(1., 4.) * self.LAYOUT['legend_row_spacing'] + row_0_y
        cols_x = np.arange(0., 4.) * self.LAYOUT['legend_col_spacing'] + row_x

        # shape
        indent = self.LAYOUT['legend_indent']

        def _add_legend_item(px, py, color, text, shape):
            _draw_bar(px, py, color, hide_bar=True, shape=shape)
            self._canvas.create_text(px + indent, py, text=text, fill='black', anchor='w')

        _add_legend_item(cols_x[1], rows_y[0], 'unknown', text="- after alarm", shape='dot')
        _add_legend_item(cols_x[1], rows_y[1], 'unknown', text='- before alarm', shape='square')
        _add_legend_item(cols_x[1], rows_y[2], 'unknown', text='- planned alarm time', shape='triangle')
        _add_legend_item(cols_x[0], rows_y[0], 'red', text='- alarm late', shape='dot')
        _add_legend_item(cols_x[0], rows_y[1], 'yellow', text="- alarm good", shape='dot')
        _add_legend_item(cols_x[0], rows_y[2], 'green', text="- alarm early", shape='dot')

        for i, duration in enumerate(durations):
            shape = 'square' if history['early'][i] else 'dot'
            _draw_bar(px[i], py[i], history['outcomes'][i], shape=shape)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    PaneTester(StatsPane, callback=lambda x: None, grid_col=0)
