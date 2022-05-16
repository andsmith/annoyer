"""
The "stoplight" button panel.
During alarms, it starts flashing.
"""
import tkinter as tk
from panels import Pane, PaneTester
import logging
import numpy as np
from app_states import AnnoyerAppStates
import tkinter.font as tkFont
from enum import IntEnum
from tracking import HistoryTracker


class StopligtStates(IntEnum):
    NORMAL = 0
    ALARMING = 1


class StoplightPane(Pane):
    """
    Class for stoplight button UI.
    """
    LAYOUT = {'x_center': 0.5,
              'spacing_ratio': 1.0 / 2.8,
              'outline_width': 3,
              'colors': {'red': 'red',
                         'yellow': 'yellow',
                         'green': 'green'},
              'background_colors': ['black', 'white'],
              'mouseover_color': "#AAAAAA",
              'mouseover_clicked_color': "white",
              'text': {'red': "I've been\nDISTRACTED!\n\nAnnoy me\nmore often!",
                       'green': "I was fine...\n\nAnnoy me\nless often!",
                       'yellow': "Thanks!\n\nI  was\nlosing focus."},
              'button_text_colors': {'red': 'white',
                                     'yellow': 'black',
                                     'green': 'white'},
              'button_font': None  # init later
              }

    def __init__(self, tk_root, tracker=None, grid_col=1, **kwargs):
        """
        :param tk_root: tk.Tk() object/ frame
        :param grid_col: Which column of the app does this go in?
        :param kwargs:  Additional arguments to Pane
        """
        logging.info("Creating stoplight-button pane.")
        self._shape = (500, 250)
        self._state = StopligtStates.NORMAL
        self._blink_state = 0
        self._blink_delay_sec = 0.5
        super(StoplightPane, self).__init__(tk_root,
                                            tracker=tracker,
                                            grid_col=grid_col,
                                            regions=[None,
                                                     self._shape,
                                                     ('frame',)],
                                            canvas_args={'background': self.LAYOUT['background_colors'][self._state]},
                                            **kwargs)
        self._button_mouseover = None
        self._mouse_buttons = {'right': None,
                               'left': None,
                               'middle': None}
        self._button_clicked = None
        self._button_mouse_is_over = None
        self._objects = {'box': None,
                         'red_circle': None,
                         'green_circle': None,
                         'yellow_circle': None,
                         }
        self._init()
        self._canvas = self._pane_objects['middle']
        self._set_button_coords()
        self._canvas.bind("<Button-1>", self._click)
        self._canvas.bind("<Motion>", self._move)
        self._canvas.bind("<ButtonRelease-1>", self._unclick)

    def _init(self):
        """
        define things that couldn't be defind before tk.Tk() was called
        """
        self.LAYOUT['button_font'] = tkFont.Font(family='Helvetica', size=12, weight='bold')

    def _stop_alarming(self):
        self._state = StopligtStates.NORMAL
        pass

    def _start_alarming(self):
        self._state = StopligtStates.ALARMING
        self._start_flashing()
        pass

    def _start_flashing(self):
        """
        During alarms, blink the background color of buttons between black and ???.
        """
        if self._state == StopligtStates.ALARMING:
            self._blink_state = (self._blink_state + 1) % 2
            self._canvas.configure(bg=self.LAYOUT['background_colors'][self._blink_state])
            self._root.after(int(self._blink_delay_sec * 1000), self._start_flashing)
        else:
            self._blink_state = 0
            self._canvas.configure(bg=self.LAYOUT['background_colors'][self._blink_state])

    def update_period(self):
        pass

    def update_tick(self):
        """
        Main app calls this every tick with its state.
        :param info: dict, must have value of type AnnoyerAppState for key 'state'
        """
        if self._tracker.is_alarmed():
            if self._state == StopligtStates.NORMAL:
                self._start_alarming()
        else:
            if self._state == StopligtStates.ALARMING:
                self._stop_alarming()

    def _set_button_coords(self):
        """
        Determine where the lights go.
        """
        self._spacing_ratio = self.LAYOUT['spacing_ratio']
        total_height = self._shape[0]
        self._circle_radius = total_height / (4.0 * self._spacing_ratio + 6.0)
        spacing = self._circle_radius * self._spacing_ratio

        # max_width = self._circle_radius * (2 + 2.0 * self._spacing_ratio)

        x_center = self.LAYOUT['x_center']
        self._red_center = np.array((x_center * self._shape[1], spacing + self._circle_radius))
        self._yellow_center = np.array((x_center * self._shape[1], 2.0 * spacing + 3.0 * self._circle_radius))
        self._green_center = np.array((x_center * self._shape[1], 3.0 * spacing + 5.0 * self._circle_radius))

    def refresh(self):
        """
        Redraw everything.
        """
        self._canvas.delete('all')

        def draw_button(x, y, name):
            theta = np.linspace(0.0, np.pi * 2.0, 100)
            xp = x + np.cos(theta) * self._circle_radius
            yp = y + np.sin(theta) * self._circle_radius

            coord_list = np.hstack([xp.reshape(-1, 1), yp.reshape(-1, 1)]).reshape(-1).tolist()
            txt = self.LAYOUT['text'][name]
            color = self.LAYOUT['colors'][name]
            if name == self._button_mouse_is_over and name == self._button_clicked:
                border_color = self.LAYOUT['mouseover_clicked_color']
                width = self.LAYOUT['outline_width']
            elif name == self._button_mouse_is_over:
                border_color = self.LAYOUT['mouseover_color']
                width = self.LAYOUT['outline_width']
            else:
                width = 0
                border_color = None
            button_text_color = self.LAYOUT['button_text_colors'][name]
            button = self._canvas.create_polygon(coord_list, fill=color, outline=border_color,
                                                 width=width)
            font = self.LAYOUT['button_font']
            text = self._canvas.create_text(x, y, text=txt, fill=button_text_color, anchor='center', justify=tk.CENTER,
                                            font=font)

            return button, text

        draw_button(self._red_center[0], self._red_center[1], 'red')
        draw_button(self._yellow_center[0], self._yellow_center[1], 'yellow')
        draw_button(self._green_center[0], self._green_center[1], 'green')

        # mouseover ?

    def _event_near_button(self, event):
        """
        Was the mouse close to one of the three buttons?
        :param event:  tkinter mouse event
        """

        centers = {'red': self._red_center,
                   'green': self._green_center,
                   'yellow': self._yellow_center}
        for center in centers:
            if np.linalg.norm(np.array([event.x, event.y]) - centers[center]) <= self._circle_radius:
                return center
        return None

    def _click(self, event):
        """
        The user clicked on a button
        :param event:  tkinter mouse event
        """
        button = self._event_near_button(event)
        if button is not None:
            self._button_clicked = button
            self.refresh()

    def _unclick(self, event):
        """
        The user let go of a mouse button
        :param event:  tkinter mouse event
        """
        button = self._event_near_button(event)
        if self._button_clicked is not None and self._button_clicked == button:
            if self._callback is not None:
                self._callback(button)
        self._button_clicked = None
        self.refresh()

    def _move(self, event):
        """
        The user moved the mouse
        """
        button = self._event_near_button(event)
        if button is not None:
            if self._button_mouse_is_over is None:
                self._button_mouse_is_over = button
                self.refresh()
            self._button_mouse_is_over = button  # awkward
        else:
            if self._button_mouse_is_over is not None:
                self._button_mouse_is_over = None
                self.refresh()
            self._button_mouse_is_over = None  # awkward again

    def _resize(self, event):

        self._shape = (event.height, event.width)
        self._set_button_coords()
        self.refresh()


def click(button):
    logging.info("Button: %s" % (button,))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    PaneTester(StoplightPane, callback=click, grid_col=0)
