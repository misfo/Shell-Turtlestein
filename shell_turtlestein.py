import os.path, pipes, re, subprocess
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


def parse_cmd(cmd_str):
    return re.match(
            r"(?P<pipe>\s*\|\s*)?(?P<shell_cmd>.*?)(?P<redirect>\s*>\s*)?$",
            cmd_str
        ).groupdict()


# Run a command in the given directory, send input to the process. If
# wait is True, wait for the process to finish. Return a pair indicating
# what happened. If the first element of the pair is True, then everything
# was ok and the second element of the pair is the standard output of the
# process. If we weren't waiting or something went wrong, the first element
# of the pair will be False. In the second case an error dialog will also
# be displayed.
def run_cmd(cwd, cmd, wait, input_str=None):
    shell = isinstance(cmd, basestring)
    if wait:
        proc = subprocess.Popen(cmd, cwd=cwd,
                                     shell=shell,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     stdin=(subprocess.PIPE if input_str else None))
        output, error = proc.communicate(input_str)
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
        if not hasattr(self, 'cmd_history'):
            self.cmd_history = []
        cwd = cwd_for_window(self.window)
        on_done = partial(self.on_done, cwd)
        inputview = show_input_panel_with_readline(self.window,
                                                   abbreviate_user(cwd) + " $",
                                                   self.cmd_history,
                                                   on_done, None, None)
        for (setting, value) in settings().get('input_widget').iteritems():
            inputview.settings().set(setting, value)

    def on_done(self, cwd, cmd_str):
        cmd = parse_cmd(cmd_str)
        settings = cmd_settings(cmd['shell_cmd'])

        before, after = settings['surround_cmd']
        shell_cmd = before + cmd['shell_cmd'] + after

        # We can leverage Sublime's (async) build systems unless we're
        # redirecting the output into the view. In that case, we use Popen
        # synchronously.
        if cmd['redirect']:
            view = self.window.active_view()
            if not view:
                sublime.error_message("No active view to redirect output to.")
                return

            for sel in view.sel():
                self.process_selection(view, sel, cwd, shell_cmd, cmd['pipe'])
        else:
            if cmd['pipe']:
                # Since Sublime's build system don't support piping to STDIN
                # directly, pipe the selected text via `echo`.
                view = self.window.active_view()
                selection_text = "".join([view.substr(s) for s in view.sel()])
                shell_cmd = "echo %s | %s" % (pipes.quote(selection_text), shell_cmd)
            exec_args = settings['exec_args']
            exec_args.update({'cmd': shell_cmd, 'shell': True, 'working_dir': cwd})

            self.window.run_command("exec", exec_args)

    def process_selection(self, view, selection, cwd, shell_cmd, pipe):
        input_str = None
        if pipe:
            input_str = view.substr(selection)

        (success, output) = run_cmd(cwd, shell_cmd, True, input_str)
        if success:
            edit = view.begin_edit()
            view.replace(edit, selection, output)
            view.end_edit(edit)


class SubprocessInCwdCommand(sublime_plugin.WindowCommand):
    """
    Launch a subprocess using the window's working directory
    """
    def run(self, cmd=None, wait=False):
        cwd = cwd_for_window(self.window)
        run_cmd(cwd, cmd, wait)
