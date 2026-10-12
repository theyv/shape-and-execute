---
title: A dark viewer in the style of Supabase
type: architecture
status: accepted
date: 2026-10-07
source: DL-82, implementation 2026-10-07
applies-to: [skills/shape-and-execute/assets/viewer/app.css, skills/shape-and-execute/assets/viewer/index.html]
---

# A dark viewer in the style of Supabase

## Context
The viewer shows task state, graphs and settings. Its first spec asked for both themes through
`prefers-color-scheme`.

## Decision
[joint] Dark is the default and the designed theme: quiet surfaces, thin borders, one green
accent, small uppercase labels, monospace for IDs and branches, dense tables (Supabase); KPI
tiles on Overview and coloured status pills with text labels (Mixpanel). The light theme is
only a second token set behind a toggle.

## Why
The owner: "Use a dark, clear, well-organized interface that is easy to scan.".

## Rejected options
- Two equal themes chosen by `prefers-color-scheme`.
