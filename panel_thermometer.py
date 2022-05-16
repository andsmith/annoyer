"""
Graphically display the changing probabilities, and let the user select a threshold for the alarm.
"""
from panels import Pane, PaneTester
import tkinter as tk
import logging
import numpy as np


class ThermometerPane(Pane):
    """
    Main panel for showing probability and controling threshold.
    """
    MAX_FRAC = 0.9999  # maximum prob. thresh.

    def __init__(self, tk_root, grid_col=0, thresh_prob=0.667, **kwargs):
        """
        Start the "thermometer pane".
        :param tk_root: tk.Tk() object / frame
        :param grid_col: which of the app's main columns does this pane go into?
        :param thresh_prob: where to draw cutoff
        :param kwargs: args for Pane.__init__()
        """
        logging.info("Creating thermometer pane.")
        self._thresh = thresh_prob
        self._shape = (500, 250)
        self._current_prob = 0.5654654
        self._level_one_y, self._level_zero_y, self._x_left, self._x_right = None, None, None, None
        self._mouse_buttons = {'right': None,
                               'left': None,
                               'middle': None}
        self._elapsed_time_str = ""
        self._period_str = ""
        self._countdown_str = ""
        self._objects = {'lines': None,
                         'red_line': None,
                         'fill': None,
                         'threshold': None,
                         'threshold_txt': None,
                         'instructions_txt': None,
                         'tic_lines': [],
                         'tic_labels': []}

        super(ThermometerPane, self).__init__(tk_root, grid_col, regions=['blank', self._shape, 'blank'], **kwargs)
        self._canvas = self._pane_objects['middle']
        self._title = self._pane_objects['top']
        self._status = self._pane_objects['bottom']
        self._canvas.bind("<Button-1>", self._click)
        self._canvas.bind("<Motion>", self._move)
        self._canvas.bind("<ButtonRelease-1>", self._unclick)

    def _click(self, event):
        """
        User clicked pane.
        :param event:  tkinter mouse event object
        """
        self._mouse_buttons['left'] = event
        self._set_ui_threshold(event)

    def get_current_prob(self):
        """
        :returns:  Current probability user has become distracted.
        """
        return self._current_prob

    def update(self, info):
        """
        Main app calls this during each tick.
        Re-estimate probabilities, and redraw thermometer, etc.
        """
        if info['elapsed_sec'] is not None:
            lambda_par = 1.0 / info['period_sec']
            t = info['elapsed_sec']
            self._elapsed_time_str = info['elapsed_time_str']
            self._period_str = info['period_str']
            self._countdown_str = info['countdown_str']
            self._current_prob = 1.0 - np.exp(-lambda_par * t)  # exp. dist. CDF
            frac = info['elapsed_sec'] / info['period_sec']
            # logging.info("Estimating %.4f probability with %s remaining (%.2f complete)" % (self._current_prob,
            #                                                                                info['countdown_str'],
            #                                                                                frac * 100.0))
            self.refresh()

    def _unclick(self, event):
        """
        User let go of mouse.
        :param event:  tkinter mouse event object
        """
        self._mouse_buttons['left'] = None

    def _move(self, event):
        """
        User moved mouse.
        :param event:  tkinter mouse event object
        """
        if self._mouse_buttons['left'] is not None:
            self._set_ui_threshold(event)

    def _set_ui_threshold(self, event):
        """
        Change the threshold based on UI.
        Notify main app through callback.
        """
        y_click = event.y
        y_high = self._shape[0] * self._level_zero_y
        y_low = self._shape[0] * self._level_one_y

        frac = 1.0 - (y_click - y_low) / (y_high - y_low)
        frac = frac if frac <= self.MAX_FRAC else self.MAX_FRAC
        frac = frac if frac > 0.0 else 0.0

        self._thresh = frac
        self.refresh()
        if self._callback is not None:
            self._callback(self._thresh)

    LAYOUT = {'y_center': 0.84,
              'x_center': 0.50,
              'bulb_rad': 0.05,
              'bulb_angles': (- np.pi / 3.5, np.pi + np.pi / 3.5),
              'bulb_top': 0.025,
              'bulb_color': 'black',
              'fluid_color': 'red',
              'bulb_width': 3,
              'tic_color': 'black',
              'tic_width': 3,
              'threshold_color': 'blue',
              'threshold_width': 3,
              'instructions_pos': (0.5, 0.915),
              'instructions_color': 'black',
              'instructions_text': "(click/drag to adjust\nalarm threshold)"}

    def refresh(self):
        """
        Re-draw all the things.
        """
        self._canvas.delete('all')

        # BODY
        theta = np.linspace(self.LAYOUT['bulb_angles'][0], self.LAYOUT['bulb_angles'][1], 100)[::-1]
        aspect = float(self._shape[1]) / float(self._shape[0])
        xb = np.cos(theta) * self.LAYOUT['bulb_rad'] / aspect + self.LAYOUT['x_center']
        x0 = xb[0]
        x1 = xb[-1]
        yb = np.sin(theta) * self.LAYOUT['bulb_rad'] + self.LAYOUT['y_center']
        y0 = self.LAYOUT['bulb_top']
        y1 = self.LAYOUT['bulb_top']
        x = np.hstack([x0, xb, x1])
        y = np.hstack([y0, yb, y1])
        self._level_zero_y = yb[0] - 0.03
        self._level_one_y = self.LAYOUT['bulb_top']
        self._x_left, self._x_right = x0, x1

        level_prob_y = self._level_zero_y * (1.0 - self._current_prob) + self._level_one_y * self._current_prob

        x_partial = np.hstack([x0, xb, x1])
        y_partial = np.hstack([level_prob_y, yb, level_prob_y
                               ])
        coords = np.hstack([x.reshape(-1, 1) * self._shape[1],
                            y.reshape(-1, 1) * self._shape[0]])
        partial_coords = np.hstack([x_partial.reshape(-1, 1) * self._shape[1],
                                    y_partial.reshape(-1, 1) * self._shape[0]])

        coord_list = coords.reshape(-1).tolist()

        # RED (indicator)
        partial_coord_list = partial_coords.reshape(-1).tolist()
        self._objects['fill'] = self._canvas.create_polygon(*partial_coord_list, fill=self.LAYOUT['fluid_color'],
                                                            width=0)
        # Black outline
        self._objects['lines'] = self._canvas.create_line(*coord_list, fill=self.LAYOUT['bulb_color'],
                                                          width=self.LAYOUT['bulb_width'])

        # Tics
        def _draw_tic(frac):
            x = x0, x1 + (x1 - x0) * 0.67
            tic_y_rel = self._level_zero_y * (1.0 - frac) + self._level_one_y * frac
            coord_list = [x[0] * self._shape[1], tic_y_rel * self._shape[0],
                          x[1] * self._shape[1], tic_y_rel * self._shape[0]]
            self._objects['tic_lines'].append(self._canvas.create_line(*coord_list, fill=self.LAYOUT['tic_color'],
                                                                       width=self.LAYOUT['tic_width']))
            text_x, text_y = coord_list[2], coord_list[1]
            frac_txt = " %.1f %%" % (frac * 100.0,)
            self._objects['tic_labels'].append(
                self._canvas.create_text(text_x, text_y, text=frac_txt, fill=self.LAYOUT['tic_color'], anchor='w'))

        _draw_tic(0.0)
        _draw_tic(1.0)
        _draw_tic(0.5)

        # Alarm,
        x_rel = x0 - (x1 - x0) * 0.67, x1
        y_rel = self._level_zero_y * (1.0 - self._thresh) + self._level_one_y * self._thresh
        coord_list = [x_rel[0] * self._shape[1], y_rel * self._shape[0],
                      x_rel[1] * self._shape[1], y_rel * self._shape[0]]

        self._objects['threshold'] = self._canvas.create_line(*coord_list, fill=self.LAYOUT['threshold_color'],
                                                              width=self.LAYOUT['threshold_width'])

        thresh_txt = "%.2f %% " % (self._thresh * 100.0,)
        text_x, text_y = coord_list[0], coord_list[1]

        self._objects['threshold_label'] = self._canvas.create_text(text_x, text_y, text=thresh_txt,
                                                                    fill=self.LAYOUT['threshold_color'], anchor='e')
        instr_pos = np.array(self.LAYOUT['instructions_pos']) * np.array(self._shape[::-1])

        self._objects['threshold_text'] = self._canvas.create_text(instr_pos[0],
                                                                   instr_pos[1],
                                                                   anchor='n',
                                                                   justify=tk.CENTER,
                                                                   text=self.LAYOUT['instructions_text'],
                                                                   fill=self.LAYOUT['instructions_color'])

        # text
        self._title.configure(text="P(distraction | t=%s) = %.4f\nP exceeds threshold in %s" % (
            self._elapsed_time_str, self._current_prob, self._countdown_str))
        self._status.configure(text="Estimated period between\n distractions:  %s" % (self._period_str,))

    def _resize(self, event):
        self._shape = (event.height, event.width)
        self.refresh()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    PaneTester(ThermometerPane)
