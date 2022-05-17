"""
Base class for the three main panels/panes of the UI.
"""
from copy import deepcopy
from abc import abstractmethod
import logging
import tkinter as tk
from tracking import HistoryTracker


class Pane(object):
    """
    Abstract class for UI pane.
    """

    DIMS = {'v_pad': 2,
            'title_v_weight': 1,
            'middle_v_weight': 18,
            'bottom_v_weight': 4}

    TEXT_GRID_PARAMS = dict(ipadx=5, ipady=4, padx=8, pady=6)
    CANVAS_GRID_PARAMS = dict(ipadx=5, ipady=4, padx=8, pady=6)

    TEXT_LABEL_PARAMS = dict()  # dict(borderwidth=1, relief="solid")
    CANVAS_PARAMS = dict()  # dict(borderwidth=1, relief="solid")

    def __init__(self, tk_root, tracker=None, grid_col=0, callback=None,
                 regions=(None, None, None), canvas_args=None, frame_args=None):
        """
        :param tk_root:  tk.Tk() object
        :param tracker:  HistoryTracker() object or None
        :param grid_col:  Which column of app?
        :param callback: if the pane needs to notify the main app for something, use this function.
        :param regions:  3-tuple (text for top, (h, w) of middle canvas, text for bottom), or NONE for one/two of those.
            or ('frame', ) for an (empty) frame
            :param canvas_args:  arguments to initialize the tkinter Canvas object
        :param frame_args:  more arguments to Frame(**frame_args)
        """
        self._tracker = tracker if tracker is not None else HistoryTracker()

        self._canvas_args = canvas_args if canvas_args is not None else {}
        self._callback = callback
        self._regions = {'top': regions[0], 'middle': regions[1], 'bottom': regions[2]}
        self._root = tk_root
        self._grid_col = grid_col
        logging.info("init with col: %i" % (grid_col,))
        self._frame_kwargs = frame_args if frame_args is not None else {}
        self._init_frame()

    def _init_frame(self):
        """
        Initialize all the common parts.  Decide how many "regions" it will have (3 - top, middle, bottom) or missing
            the top and/or bottom
        """
        self._frame = tk.Frame(self._root, **self._frame_kwargs)
        self._frame.grid(column=self._grid_col, row=0, sticky="nsew")
        self._pane_objects = {}

        region_num = 0

        if self._regions['top'] is not None:
            if self._regions['top'] == ('frame',):
                self._pane_objects['top'] = tk.Frame(master=self._frame)
            else:
                self._pane_objects['top'] = tk.Label(master=self._frame, text=self._regions['top'],
                                                     **self.TEXT_LABEL_PARAMS)
            self._pane_objects['top'].grid(column=0, row=region_num, **self.TEXT_GRID_PARAMS)
            region_num += 1
            self._frame.rowconfigure(0, pad=self.DIMS['v_pad'], weight=self.DIMS['title_v_weight'])

        if self._regions['middle'] is not None:
            middle_shape = self._regions['middle']
            middle_rowspan = 3 - int(self._regions['top'] is not None) - int(self._regions['bottom'] is not None)
            canvas_params = deepcopy(self._canvas_args)
            canvas_params.update(Pane.CANVAS_PARAMS)
            self._pane_objects['middle'] = tk.Canvas(master=self._frame, width=middle_shape[1], height=middle_shape[0],
                                                     **canvas_params)
            self._pane_objects['middle'].grid(column=0, row=region_num, rowspan=middle_rowspan,
                                              **self.CANVAS_GRID_PARAMS)
            self._pane_objects['middle'].bind("<Configure>", self._resize)
            self._frame.rowconfigure(0, pad=self.DIMS['v_pad'], weight=self.DIMS['middle_v_weight'])

            region_num += 1
        if self._regions['bottom'] is not None:

            bottom_row = 2

            if self._regions['bottom'] == ('frame',):
                self._pane_objects['bottom'] = tk.Frame(master=self._frame)
            else:
                self._pane_objects['bottom'] = tk.Label(master=self._frame, text=self._regions['bottom'],
                                                        **self.TEXT_LABEL_PARAMS, justify=tk.LEFT)
            self._pane_objects['bottom'].grid(column=0, row=bottom_row, **self.TEXT_GRID_PARAMS)
            self._frame.rowconfigure(2, pad=self.DIMS['v_pad'], weight=self.DIMS['bottom_v_weight'])
        self._frame.columnconfigure(0, weight=1)

    def deactivate(self):
        """
        Turn off this pane.
        """
        self._frame.grid_forget()

    def get_pane_object(self):
        return self._pane_objects

    '''
    @abstractmethod
    def _resize(self, event):  # for resize
        pass

    @abstractmethod
    def update_tick(self):  # to get new data
        """
        Main app calls this every tick with its state.
        """
        pass

    @abstractmethod
    def update_period(self):  # to get new data
        """
        Main app calls this at the end of a time period
        """
        pass


    @abstractmethod
    def refresh(self):
        pass
    '''


class PaneTester(object):
    """
    Run each of the subclasses by itself.  (i.e. not part of the main app)
    """

    def __init__(self, pane_type, **kwargs):
        """
        :param pane_type:  object inheriting from Pane
        :param kwargs:  arguments to initialize pane_type()
        """
        self._type = pane_type
        self._root = tk.Tk()
        self._root.title("Pane tester (debugging)")
        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(0, weight=1)
        settings = {'sound_file': 'doesnt_exist.wav'}

        self._tracker = HistoryTracker(settings=settings)

        self._pane = pane_type(self._root, tracker=self._tracker, **kwargs)
        self._root.mainloop()
