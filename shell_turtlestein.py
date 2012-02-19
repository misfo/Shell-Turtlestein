import os.path, re, subprocess
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

class ShellPromptCommand(sublime_plugin.WindowCommand):
    """
    Prompt the user for a shell command to run the the window's directory
    """
    def run(self):
        cwd = cwd_for_window(self.window)
        on_done = partial(exec_cmd, self.window, cwd)
        view = self.window.show_input_panel(cwd + " $", "",
                                            on_done, None, None)
        for (setting, value) in settings().get('input_widget').iteritems():
            view.settings().set(setting, value)

class SubprocessInCwdCommand(sublime_plugin.WindowCommand):
    """
    Launch a subprocess using the window's working directory
    """
    def run(self, cmd = None, wait = False):
        cwd = cwd_for_window(self.window)
        shell = isinstance(cmd, basestring)
        if wait:
            proc = subprocess.Popen(cmd, cwd=cwd,
                                         shell=shell,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT)
            output, _ = proc.communicate()
            return_code = proc.poll()
            if return_code:
                sublime.error_message("The following command exited with status "
                                      + "code " + str(return_code) + ":\n" + cmd
                                      + "\n\nOutput:\n" + output)
        else:
            subprocess.Popen(cmd, cwd=cwd, shell=shell)
