---
title: Troubleshooting
description: Common issues and how to resolve them.
---

## Buzzing while holding position

Two causes have been identified. This applies whether the buzz is
continuous or only shows up for a few seconds right after a move ends:

- **Gain too high.** The outer position and velocity loop gains fight
  the axis into oscillating around the target instead of settling.
  Lower `pid_position_p`/`pid_position_i` and
  `pid_velocity_p`/`pid_velocity_i` (see Manual tuning below).
- **Current-loop filters disabled.** Set `torque_filter_hz`/
  `flux_filter_hz` (see Manual tuning below).

## Whine during movement

A brief tone at some settings during
[Tuning](/getting-started/tuning/)'s position-fine-tuning phase is a
known artifact of that phase's own test moves, not motor damage. It
stops on its own when `FOCI_AUTOTUNE` finishes and doesn't occur during
normal printing.

`FOCI_AUTOTUNE` gives you a good, safe result, though it can still land
on a `pid_position_p` high enough to cause the buzzing-while-holding
symptom above during regular use. If you'd prefer a different
tracking-versus-quietness tradeoff, edit `pid_position_p` yourself at
any time (see Manual tuning below): lower values settle less precisely
but hold quieter.

## Rough or loud motion while printing

An axis that never completed [Tuning](/getting-started/tuning/) runs on
gains from a single quick measurement taken during `FOCI_SETUP`, not
the fuller search `FOCI_AUTOTUNE` does. Run `FOCI_AUTOTUNE` before
judging motion quality.

## Manual tuning

`FOCI_AUTOTUNE` computes gains automatically, but every
`[foci <stepper>]` PID field is a normal config value you can set
directly. This project ran on hand-tuned values for a long time before
autotune existed.

### PID gains

Only the `pid_position_p` "too high" row below has been confirmed on
real hardware in this project. The rest is general closed-loop PID
behavior, true of any such system, given as a starting point for where
to look.

| Field | Too high | Too low |
|---|---|---|
| `pid_torque_p` | High-pitched whine, vibration marks on prints | Overshoots on fast moves |
| `pid_torque_i` | Buzzing while stationary, instability | Slowly loses position under static load |
| `pid_flux_p` | Audible noise, wastes current holding position | Reduced top speed or torque |
| `pid_flux_i` | Overshoots and oscillates, wastes current correcting it | Slow to correct, wastes current on rapid moves |
| `pid_position_p` | Overshoots and oscillates on stops, buzzing while holding | Large position error, rounded corners, undersized prints |
| `pid_position_i` | Overshoot on corners with a "hook back" correction, best left at 0 | Drift accumulates over a print, offset layers |
| `pid_velocity_p` | Speed oscillates at target, ringing-like print artifacts | Lags behind target speed, rounded corners |
| `pid_velocity_i` | Speed oscillations | Slightly slower than commanded under load |

Adjust one field at a time, restart Klipper, then test. Change gains
roughly 10-20% per step rather than large jumps, and re-test after each
change. Large jumps make it hard to tell which change actually fixed,
or caused, the symptom.

### Current-loop filters

These set the cutoff for each loop's input filter, and default to
disabled. A higher cutoff passes more of the raw signal through with
less smoothing, so unfiltered noise can come through as buzz or squeal.
A lower cutoff smooths more but adds delay to that loop's response,
which can show up as sluggishness.

| Field | Range | Starting point |
|---|---|---|
| `torque_filter_hz` | 10-10000 Hz | 1000-5000 Hz |
| `flux_filter_hz` | 10-10000 Hz | 1000-5000 Hz |
| `velocity_filter_hz` | 10-1000 Hz | 100-500 Hz |
| `position_filter_hz` | 10-1000 Hz | 100-500 Hz |

`torque_filter_hz` and `flux_filter_hz` are the two to try first.

### Velocity feedforward

`velocity_feedforward` (on/off, default off) and
`velocity_feedforward_gain` (0.0 to 8.0, default 1.0, only used once
`velocity_feedforward` is on) correct a structural lag in the position
loop. With it off, the axis trails the commanded position during
steady motion. Too low a gain, including off, leaves that lag in place.
Too high a gain overshoots ahead of the target instead, most noticeable
at acceleration and direction changes.
