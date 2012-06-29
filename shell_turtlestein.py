import os.path, re, subprocess
import sublime, sublime_plugin
from functools import partial
from sublime_readline import show_input_panel_with_readline


def cwd_for_window(window):
    """
    Return the working directory in which the window's commands should run.

    In the common case when the user has one folder open, return that.
    Otherwise, return one of the following (in order of preference):
        1) One of the open folders, preferring a folder containing the active
           file.
        2) The directory containing the active file.
        3) The user's home directory.
    """
    folders = window.folders()
    if len(folders) == 1:
        return folders[0]
    else:
        active_view = window.active_view()
        active_file_name = active_view.file_name() if active_view else None
        if not active_file_name:
            return folders[0] if len(folders) else os.path.expanduser("~")
        for folder in folders:
            if active_file_name.startswith(folder):
                return folder
        return os.path.dirname(active_file_name)


def abbreviate_user(path):
    """
    Return a path with the ~ dir abbreviated (i.e. the inverse of expanduser)
    """
    home_dir = os.path.expanduser("~")
    if path.startswith(home_dir):
        return "~" + path[len(home_dir):]
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
        settings_for_cmd = (c for c
                            in settings().get('cmd_settings')
                            if re.search(c['cmd_regex'], cmd)).next()
        d.update(settings_for_cmd)
    except StopIteration:
        pass
    return d


def exec_cmd(window, cwd, cmd):
    d = cmd_settings(cmd)

    before, after = d['surround_cmd']
    cmd = before + cmd + after

    exec_args = d['exec_args']
    exec_args.update({'cmd': cmd, 'shell': True, 'working_dir': cwd})

    window.run_command("exec", exec_args)


def prompt_for_cmd(subcmd, window, cwd, on_done):
    if not hasattr(subcmd, 'cmd_history'):
        subcmd.cmd_history = []
    readview = show_input_panel_with_readline(window,
                                              abbreviate_user(cwd) + " $",
                                              subcmd.cmd_history,
                                              on_done, None, None)
    for (setting, value) in settings().get('input_widget').iteritems():
        readview.settings().set(setting, value)


# Run a command in the given directory, send input to the process. If
# wait is True, wait for the process to finish. Return a pair indicating
# what happened. If the first element of the pair is True, then everything
# was ok and the second element of the pair is the standard output of the
# process. If we weren't waiting or something went wrong, the first element
# of the pair will be False. In the second case an error dialog will also
# be displayed.
def run_cmd(cwd, cmd, wait, input=""):
    shell = isinstance(cmd, basestring)
    if wait:
        proc = subprocess.Popen(cmd, cwd=cwd,
                                     shell=shell,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     stdin=subprocess.PIPE)
        output, error = proc.communicate(input)
        return_code = proc.poll()
        if return_code:
            sublime.error_message("The following command exited with status "
                                  + "code " + str(return_code) + ":\n" + cmd
                                  + "\n\nOutput:\n" + output
                                  + "\n\nError:\n" + error)
            return (False, None)
        else:
            return (True, output)
    else:
        subprocess.Popen(cmd, cwd=cwd, shell=shell)
        return (False, None)


class ShellPromptCommand(sublime_plugin.WindowCommand):
    """
    Prompt the user for a shell command to run in the window's directory
    """
    def run(self):
        window = self.window
        cwd = cwd_for_window(window)
        on_done = partial(exec_cmd, window, cwd)
        prompt_for_cmd(self, window, cwd, on_done)


class SubprocessInCwdCommand(sublime_plugin.WindowCommand):
    """
    Launch a subprocess using the window's working directory
    """
    def run(self, cmd=None, wait=False):
        cwd = cwd_for_window(self.window)
        run_cmd(cwd, cmd, wait)


class ShellPromptFilterCommand(sublime_plugin.TextCommand):
    """
    Prompt the user for a shell command to run in the view's directory.
    Pass the first selection as standard input to the command and replace
    the selection with the command's standard output or an error message
    if something went wrong
    """
    def run(self, edit):
        window = self.view.window()
        cwd = cwd_for_window(window)
        on_done = partial(self.on_done, edit, cwd)
        prompt_for_cmd(self, window, cwd, on_done)

    def on_done(self, edit, cwd, cmd):
        view = self.view
        input_region = view.sel()[0]
        input = view.substr(input_region)
        (success, output) = run_cmd(cwd, cmd, True, input)
        if success:
            view.replace(edit, input_region, output)
