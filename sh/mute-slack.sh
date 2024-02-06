#!/bin/bash
# kate: hl bash

set -e
set -u

# While we're called, the user is pressing ctrl-alt-m and the modifiers will confuse slack.
# Wait a bit until our human has released the keys.
# We could of course also pass --clearmodifiers to the `xdotool key` command below,
# but that confuses Slack even more, so let's rather not.
sleep 0.1

# Find an ongoing Slack call. The window name is 'Slack | <call title or channel> | 12:34'.
# If this fails, it'll exit nonzero and 'set -e' will fail this script.
SLACK_CALL_WINDOW="$(xdotool search --name 'Slack.*:[0-9][0-9]')"

# The Slack call window must be active, otherwise Slack will just ignore the input.
# Since the whole point of this is to be able to mute/unmute Slack _while working
# in other windows_, we'll need to switch to Slack, send the m key and switch back
# to whatever we were doing before.
ACTIVE_WINDOW="$(xdotool getactivewindow)"

xdotool windowactivate "$SLACK_CALL_WINDOW"
xdotool key --window "$SLACK_CALL_WINDOW" m

xdotool windowactivate "$ACTIVE_WINDOW"
