# Adds some GNU readline-like features to an input widget

import sublime_plugin
from functools import partial

active_input_row = -1

def callback_with_history(callback, cmd_history, input_text):
    if callback:
        cmd = input_text.split("\n")[active_input_row]
        if cmd in cmd_history:
            cmd_history.remove(cmd)
        cmd_history.append(cmd)
        return callback(cmd)

def show_input_panel_with_readline(window, caption, cmd_history,
                                   on_done, on_change, on_cancel):
    global active_input_row
    active_input_row = -1
    view = window.show_input_panel(caption, u"\n".join(cmd_history) + u"\n",
                                   partial(callback_with_history, on_done, cmd_history),
                                   on_change, on_cancel)
    view.settings().set('readline_input_widget', True)
    view.show(view.size())
    return view

class ReadlineHistoryChange(sublime_plugin.TextCommand):
    def run_(self, args):
        # Override default run_ so that an edit isn't created.
        if 'event' in args:
            del args['event']
        return self.run(**args)

    def run(self, movement, movement_args):
        self.view.run_command(movement, movement_args)
        self.view.run_command("move_to", {"to": "eol", "extend": False})
        global active_input_row
        active_input_row, _ = self.view.rowcol(self.view.sel()[0].b)

class LeftDeleteOnLine(sublime_plugin.TextCommand):
    def run(self, edit):
        if self.view.rowcol(self.view.sel()[0].b)[1]:
            # Don't left delete if the cursor is at the beginning of the line
            self.view.run_command('left_delete')