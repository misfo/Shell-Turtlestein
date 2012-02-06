Shell Turtlestein
=================

A quick and simple way to run arbitrary shell commands in Sublime Text 2.

Mr. Turtlestein acts as a more flexible alternative to Sublime's build systems.
Commands run in your project's directory:

![input image]()

And display their output just like Sublime's build systems:

![output image]()

Snippets are available for frequently used commands.  All snippets with the
scope name `source.shell` (`source.dosbatch` for Windows users) can be used in
the prompt shown above.  I have
[some examples](https://github.com/misfo/Sublime-Packages/tree/master/User/Snippets/Shell)
you can take a look at to get an idea for this.


Default keybindings
-------------------
* Ctrl + Shift + C (Cmd + Shift + C): prompt for a shell command
* Ctrl + Alt + Shift + C (Cmd + Alt + Shift + C): launch a terminal in the
  window's directory


Optional Configuration
----------------------
In your own `Packages/User/Shell Turtlestein.sublime-commands` file you can
override the following settings:

  * `cmd_config`: An array of configurations to use for commands that are
  	executed.  The first configuration to match the command being run will be
  	used.  The keys that each configuration should have are:
  	* `cmd_regex`: A regex that must match the command for this configuration
  	  for this configuration to be used.
  	* `exec_args`: The arguments that will be passed to `ExecCommand`.  The same
  	  [options that are available to build systems](http://sublimetext.info/docs/en/reference/build_systems.html)
  	  are available here, but `file_regex`, `line_regex`, `encoding`, `env`, and
  	  `path` are the only options that make sense to use with this plugin.
  * `terminal_cmd`: An array of arguments representing the command to run when
    launching a terminal.  If you're sharing your setup between multiple
    machines [like me](https://github.com/misfo/Sublime-Packages), make sure to
    put this setting in an OS-specific settings file
    (e.g. `Packages/User/Shell Turtlestein (OSX).sublime-settings` for OS X)
    so that it won't be used on other OSes.


PAQ
---
Q: Who the balls is Shell Turtlestein?
A: He was a pet turtle that died in some episode of Modern Family.  That's about
   as high-brow as my references get.  R.I.P. Shell :(

Q: What does "PAQ" stand for?
A: Possibly asked questions