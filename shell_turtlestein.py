import os.path, pipes, re, subprocess, tempfile
import sublime, sublime_plugin
from functools import partial


def cwd_for_window(window):
    """
    Return the working directory in which the window's commands should run.

    In the common case when the user has one folder open, return that.
    Otherwise, return one of the following (in order of preference):
        1) One of the open folders, preferring a folder containing the active
           file.
        2) The directory containing the active file.
        3) The user's home directory.

    If `prefer_active_view_dir` is set to True, 2 will be preferred over 1.
    """
    active_view = window.active_view()
    active_file = active_view.file_name() if active_view else None
    if settings().get('prefer_active_view_dir') == True:
        return active_view_dir(active_file) or open_folder(window, active_file) or home_dir()
    else:
        return open_folder(window, active_file) or active_view_dir(active_file) or home_dir()

def open_folder(window, active_file_name):
    folders = window.folders()
    if len(folders) == 1:
        return folders[0]

    if not active_file_name:
        return folders[0] if len(folders) else None

    for folder in folders:
        if active_file_name.startswith(folder):
            return folder

def active_view_dir(active_file_name):
    if active_file_name:
        return os.path.dirname(active_file_name)

def home_dir():
    return os.path.expanduser("~")


def abbreviate_user(path):
    """
    Return a path with the ~ dir abbreviated (i.e. the inverse of expanduser)
    """
    home = home_dir()
    if path.startswith(home):
        return "~" + path[len(home):]
    else:
        return path


def settings():
    return sublime.load_settings('Shell Turtlestein.sublime-settings')


def cmd_settings(cmd):
    """
    Return the default settings with settings for the command merged in
    """
    d = {}
    for setting in ['exec_args', 'surround_cmd']:
        d[setting] = settings().get(setting)
    try:
        settings_for_cmd = next((c for c
                            in settings().get('cmd_settings')
                            if re.search(c['cmd_regex'], cmd)))
        d.update(settings_for_cmd)
    except StopIteration:
        pass
    return d


def parse_cmd(cmd_str):
    return re.match(
            r"\s*(?P<input>\|)?\s*(?P<shell_cmd>.*?)\s*(?P<output>[|>])?\s*$",
            cmd_str
        ).groupdict()


def run_cmd(cwd, cmd, wait, input_str=None):
    shell = isinstance(cmd, str)
    if wait:
        proc = subprocess.Popen(cmd, cwd=cwd,
                                     shell=shell,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     stdin=(subprocess.PIPE if input_str else None))
        encoded_input = None if input_str == None else input_str.encode('utf8')
        output, error = proc.communicate(encoded_input)
        return_code = proc.poll()
        if return_code:
            show_in_output_panel("`%s` exited with a status code of %s\n\n%s"
                                 % (cmd, return_code, error))
            return (False, None)
        else:
            return (True, output.decode('utf8'))
    else:
        subprocess.Popen(cmd, cwd=cwd, shell=shell)
        return (False, None)

def show_in_output_panel(message):
    window = sublime.active_window()
    panel_name = 'shell_turtlestein'
    panel = window.get_output_panel(panel_name)
    edit = panel.begin_edit()
    panel.insert(edit, 0, message)
    panel.end_edit(edit)
    window.run_command('show_panel', {'panel': 'output.' + panel_name})

class ShellPromptCommand(sublime_plugin.WindowCommand):
    """
    Prompt the user for a shell command to run in the window's directory
    """
    def run(self, **args):
        if not hasattr(self, 'cmd_history'):
            self.cmd_history = []
        cwd = cwd_for_window(self.window)
        args.setdefault("run_previous", False)

        if len(self.cmd_history) > 0 and args["run_previous"]:
            self.on_done(cwd, self.cmd_history[-1])
        else:
            on_done = partial(self.on_done, cwd)
            inputview = show_input_panel_with_readline(self.window,
                                                       abbreviate_user(cwd) + " $",
                                                       self.cmd_history,
                                                       on_done, None, None)
            for (setting, value) in list(settings().get('input_widget').items()):
                inputview.settings().set(setting, value)


    def on_done(self, cwd, cmd_str):
        cmd = parse_cmd(cmd_str)
        if not cmd['input'] and cmd['output'] == '|':
            sublime.error_message(
                "Piping output to the view requires piping input from the view as well."
                + " Please use a preceding |.")
            return

        active_view = self.window.active_view()
        if cmd['input'] or cmd['output'] == '|':
            if not active_view:
                sublime.error_message(
                    "A view has to be active to pipe text from and/or to a view.")
                return

        settings = cmd_settings(cmd['shell_cmd'])

        before, after = settings['surround_cmd']
        shell_cmd = before + cmd['shell_cmd'] + after

        if cmd['input']:
            input_regions = [sel for sel in active_view.sel() if sel.size() > 0]
            if len(input_regions) == 0:
                input_regions = [sublime.Region(0, active_view.size())]
        else:
            input_regions = None


        # We can leverage Sublime's (async) build systems unless we're
        # redirecting the output into a view. In that case, we use Popen
        # synchronously.
        if cmd['output']:
            for region in (input_regions or [None]):
                self.process_region(active_view, region, cwd, shell_cmd, cmd['output'])
        else:
            if input_regions:
                # Since Sublime's build system doesn't support piping to STDIN
                # directly, use a tempfile.
                text = "".join([active_view.substr(r) for r in input_regions])
                temp = tempfile.NamedTemporaryFile(delete=False)
                temp.write(text.encode('utf8'))
                shell_cmd = "%s < %s" % (shell_cmd, pipes.quote(temp.name))
            exec_args = settings['exec_args']
            exec_args.update({'cmd': shell_cmd, 'shell': True, 'working_dir': cwd})

            self.window.run_command("exec", exec_args)

    def process_region(self, active_view, selection, cwd, shell_cmd, outpt):
        input_str = None
        if selection:
            input_str = active_view.substr(selection)

        (success, output) = run_cmd(cwd, shell_cmd, True, input_str)
        if success:
            if outpt == '|':
                active_view.run_command("replace_with_text", {'region_start': selection.a,
                                                              'region_end': selection.b,
                                                              'text': output})
            elif outpt == '>':
                self.window.run_command("new_file")
                new_view = self.window.active_view()
                new_view.set_name(shell_cmd.strip())
                new_view.run_command("replace_with_text", {'text': output})


class ReplaceWithTextCommand(sublime_plugin.TextCommand):
    """
    Replace the text in the specified region with the specified text
    """
    def run(self, edit, region_start=None, region_end=None, text=None):
        if region_start and region_end:
            self.view.replace(edit, sublime.Region(region_start, region_end), text)
        else:
            self.view.insert(edit, 0, text)

class SubprocessInCwdCommand(sublime_plugin.WindowCommand):
    """
    Launch a subprocess using the window's working directory
    """
    def run(self, cmd=None, wait=False):
        cwd = cwd_for_window(self.window)
        run_cmd(cwd, cmd, wait)


###########################################################################
# readline-related stuff...
#
# This was in a separate file, but that caused issues starting with Sublime
# Text 3
###########################################################################

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
    view = window.show_input_panel(caption, "\n".join(cmd_history) + "\n",
                                   partial(callback_with_history, on_done, cmd_history),
                                   on_change, on_cancel)
    view.settings().set('readline_input_widget', True)
    view.show(view.size())
    return view

class ReadlineHistoryChange(sublime_plugin.TextCommand):
    def run_(self, someIntNotUsed, args):
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
