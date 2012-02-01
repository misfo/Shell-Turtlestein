import os, re, subprocess
import sublime, sublime_plugin
from functools import partial

def cwd_for_window(window):
	folders = window.folders()
	if len(folders) == 1:
		return folders[0]
	else:
		sublime.status_message("There must be one folder open in the window")
		return None

def exec_config(cmd):
	settings = sublime.load_settings('Shell Turtlestein.sublime-settings')
	try:
		return (c for c
			    in settings.get('exec_configs')
			    if re.search(c.pop('cmd_regex'), cmd)).next()
	except StopIteration:
		return None

def exec_cmd(window, cmd, **kwargs):
	config = exec_config(cmd) or {}
	print "config", config
	config.update(kwargs)
	config.update({'cmd': cmd})
	window.run_command("exec", config)

class ShellInputCommand(sublime_plugin.WindowCommand):
	def run(self):
		cwd = cwd_for_window(self.window)
		if cwd:
			on_done = partial(exec_cmd,
							  self.window,
							  working_dir=cwd,
							  shell=True)
			view = self.window.show_input_panel(cwd + " $", "",
												on_done, None, None)
			if os.name == "nt":
				syntax = "Packages/Batch File/Batch File.tmLanguage"
			else:
				syntax = "Packages/ShellScript/Shell-Unix-Generic.tmLanguage"
			view.set_syntax_file(syntax)
			view.settings().set('gutter', False)

class LaunchShellCommand(sublime_plugin.WindowCommand):
	def run(self):
		cwd = cwd_for_window(self.window)
		if cwd:
			if os.name == "nt":
				cmd = ["cmd.exe"]
			else:
				cmd = ["Terminal.app"]
			subprocess.Popen(cmd, cwd=cwd)
