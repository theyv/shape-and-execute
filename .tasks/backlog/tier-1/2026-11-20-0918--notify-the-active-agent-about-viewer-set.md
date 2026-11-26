# Intent: Notify the active agent about viewer setting changes

## Problem

An agent can keep using stale task settings after the owner changes them in the viewer. This has happened more than once. In one case the owner raised the review limit to five and the agent reset it to three, then asked again for approval.

## Goal

[human] On the agent’s next turn, surface viewer changes for its active task before it makes a decision using those settings. Show which setting changed, its previous and current values, and that the owner changed it. Example: the owner raised the review limit from 3 to 5.

Use the latest owner settings for subsequent work. An agent should only replace them when the owner asks for another change.
