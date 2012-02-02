import re, subprocess
import sublime, sublime_plugin
from functools import partial

def cwd_for_window(window):
    folders = window.folders()
    if len(folders) == 1:
        return folders[0]
    else:
        sublime.status_message("There must be one folder open in the window")
        return None

def settings():
    return sublime.load_settings('Shell Turtlestein.sublime-settings')

def exec_args(cmd):
    try:
        return (c['exec_args'] for c
                in settings().get('cmd_config')
                if re.search(c['cmd_regex'], cmd)).next()
    except StopIteration:
        return None

def exec_cmd(window, cwd, cmd):
    config = exec_args(cmd) or {}
    print "config", config
    config.update({'cmd': cmd, 'shell': True, 'working_dir': cwd})
    window.run_command("exec", config)

class ShellInputCommand(sublime_plugin.WindowCommand):
    def run(self):
        cwd = cwd_for_window(self.window)
        if cwd:
            on_done = partial(exec_cmd, self.window, cwd)
            view = self.window.show_input_panel(cwd + " $", "",
                                                on_done, None, None)
            view.set_syntax_file(settings().get('input_syntax_file'))
            view.settings().set('gutter', False)

class LaunchShellCommand(sublime_plugin.WindowCommand):
    def run(self):
        cwd = cwd_for_window(self.window)
        if cwd:
            subprocess.Popen(settings().get('terminal_cmd'), cwd=cwd)
