---
title: G-Code Reference
description: FOCI G-code commands.
---

`STEPPER=<name>` (`stepper_x`, `stepper_y`) selects which stepper a
command applies to.

## Core

#### FOCI_SELFTEST

`FOCI_SELFTEST STEPPER=<name>`

Runs the self-test for this stepper: ADC calibration, both motor
coils, phase wiring, encoder, and encoder direction. See
[Bring-up](/getting-started/bring-up/).

#### FOCI_SETUP

`FOCI_SETUP STEPPER=<name> [PROFILE=<conservative|balanced|stiff>]`

Identifies motor resistance and inductance and applies current gains.
`PROFILE` defaults to `balanced`. See
[Bring-up](/getting-started/bring-up/).

#### FOCI_AUTOTUNE

`FOCI_AUTOTUNE STEPPER=<name> [PROFILE=<conservative|balanced|stiff>] [MODE=<unloaded|nominal|high_inertia>] [ACTION=<name>]`

Tunes the outer position/velocity loop. Requires `FOCI_SETUP` to have
already run. `PROFILE` defaults to `balanced`, `MODE` to `nominal`.
`ACTION` runs one phase of the tune on its own, for diagnostic use:
`velocity_p_tune` (finds the velocity P gain), `velocity_i_tune`
(replays the velocity integral step against the retained plan, same power
cycle only), `velocity_tune_check` (reversal and standstill checks on the
tuned velocity loop), and `position_p_tune` (position P, after a velocity
tune). Omit it for the normal production path, which runs all of them in
sequence. See
[Tuning](/getting-started/tuning/).

#### DUMP_FOCI

`DUMP_FOCI STEPPER=<name> [TUNING=<0|1>]`

Dumps TMC4671 register state and homing/stall status for this
stepper. `TUNING=1` appends host-computed tuning analysis. Read-only.

#### FOCI_SET_GAINS

`FOCI_SET_GAINS STEPPER=<name> VELOCITY_P=<gain> VELOCITY_I=<gain> POSITION_P=<gain> POSITION_I=<gain>`

Sets outer-loop gains live, for bring-up testing. Not persisted to
`printer.cfg`. Values are floating-point gains
(`VELOCITY_P`/`POSITION_P` up to 127.996, `VELOCITY_I`/`POSITION_I` up
to 7.999), encoded to the chip's raw Q8.8/Q4.12 format.

#### FOCI_SET_INNER_GAINS

`FOCI_SET_INNER_GAINS STEPPER=<name> FLUX_P=<raw> FLUX_I=<raw> TORQUE_P=<raw> TORQUE_I=<raw>`

Sets inner current-loop gains live, for bring-up testing. Not persisted. Each
value is a raw register value, 0 to 32767.

#### FOCI_SET_FILTERS

`FOCI_SET_FILTERS STEPPER=<name> [VELOCITY_HZ=<hz>] [TORQUE_HZ=<hz>] [POSITION_HZ=<hz>] [FLUX_HZ=<hz>]`

Sets input filter cutoffs live, for the current session only, not
persisted. At least one parameter is required. 0 disables that filter.
`VELOCITY_HZ`/`POSITION_HZ` accept 10-1000, `TORQUE_HZ`/`FLUX_HZ`
accept 10-10000.

#### FOCI_SET_CURRENT

`FOCI_SET_CURRENT STEPPER=<name> RUN_CURRENT=<amps>`

Sets run current live, for bring-up testing. Not persisted. `RUN_CURRENT` is
in amps, above 0 up to 5.0.

#### FOCI_SET_VELOCITY_FEEDFORWARD

`FOCI_SET_VELOCITY_FEEDFORWARD STEPPER=<name> [ENABLE=<0|1>] [GAIN=<gain>]`

Sets velocity feedforward live, for bring-up testing. Not persisted. `ENABLE`
defaults to 1. `GAIN` (0.0 to 8.0) defaults to the stepper's current
setting.

#### FOCI_SET_VOLTAGE_LIMIT

`FOCI_SET_VOLTAGE_LIMIT STEPPER=<name> VOLTAGE_LIMIT=<raw>`

Sets the live voltage output limit for authority diagnostics. Not
persisted. `VOLTAGE_LIMIT` is a raw register value, 0 to 32767.

## Diagnostics

:::note
These are debugging tools for isolating a problem, developer-focused,
not something a working printer needs in normal operation.
:::

### Passive

Read-only, no motion or current changes.

#### FOCI_STEP_POSITION

`FOCI_STEP_POSITION STEPPER=<name>`

Reports raw MCU step position alongside Klipper's own tracked position
and the difference between them.

#### FOCI_STEPPER_STATS

`FOCI_STEPPER_STATS STEPPER=<name>`

Reports step queue and execution counters: queued/loaded/executed
steps, timing, discard/stop/reset counts.

#### FOCI_STACK_WATERMARK

`FOCI_STACK_WATERMARK STEPPER=<name>`

Reports unused MCU stack headroom since boot. Refuses while motion is
active.

### Active

Runs a bounded, deliberate excitation of the motor or current loop.

#### FOCI_CURRENT_STEP_TEST

`FOCI_CURRENT_STEP_TEST STEPPER=<name> TARGET=<value> [AXIS=<torque|flux>] [DURATION_MS=<ms>] [VOLTAGE_LIMIT=<raw>]`

Runs a bounded current-loop step on the chosen axis. `TARGET` accepts
-1000 to 1000. `AXIS` defaults to `torque`. `DURATION_MS` defaults to
80, accepts 20-200. `VOLTAGE_LIMIT` defaults to 12000, accepts
1024-29000.

#### FOCI_CURRENT_VECTOR_STEP_TEST

`FOCI_CURRENT_VECTOR_STEP_TEST STEPPER=<name> [TORQUE_TARGET=<value>] [FLUX_TARGET=<value>] [DURATION_MS=<ms>] [VOLTAGE_LIMIT=<raw>]`

Runs a bounded combined torque/flux current-vector step.
`TORQUE_TARGET`/`FLUX_TARGET` default to 0, accept -1000 to 1000.
`DURATION_MS` defaults to 80, accepts 20-200. `VOLTAGE_LIMIT` defaults
to 12000, accepts 1024-29000.

#### FOCI_CURRENT_TORQUE_SAMPLE_TEST

`FOCI_CURRENT_TORQUE_SAMPLE_TEST STEPPER=<name> TARGET=<value> [FLUX_TARGET=<value>] [SAMPLE_DELAY_MS=<ms>] [VOLTAGE_LIMIT=<raw>]`

Runs a bounded torque pulse and samples it early, before the usual
dwell floor. `TARGET` accepts -1000 to 1000. `FLUX_TARGET` defaults to
0. `SAMPLE_DELAY_MS` defaults to 5, accepts 1-200. `VOLTAGE_LIMIT`
defaults to 12000, accepts 1024-29000.

#### FOCI_POSITION_TORQUE_OFFSET_TEST

`FOCI_POSITION_TORQUE_OFFSET_TEST STEPPER=<name> TARGET=<value> [SAMPLE_DELAY_MS=<ms>] [VOLTAGE_LIMIT=<raw>]`

Runs a bounded torque-offset sample while staying in position mode.
`TARGET` accepts -1000 to 1000. `SAMPLE_DELAY_MS` defaults to 2,
accepts 1-200. `VOLTAGE_LIMIT` defaults to 12000, accepts 1024-29000.

#### FOCI_VOLTAGE_STEP_TEST

`FOCI_VOLTAGE_STEP_TEST STEPPER=<name> UQ=<value> [UD=<value>] [SAMPLE_DELAY_MS=<ms>]`

Runs a bounded open-loop voltage-vector pulse and samples it, bypassing
current control. `UQ` accepts -1024 to 1024. `UD` defaults to 0,
accepts -1024 to 1024. `SAMPLE_DELAY_MS` defaults to 2, accepts 1-200.

#### FOCI_RESISTANCE_TEST

`FOCI_RESISTANCE_TEST STEPPER=<name> [DETAIL=<0-255>]`

Triggers the same firmware resistance-identification engine
`FOCI_SETUP` uses, streaming results back without host-side pass/fail
fitting. `DETAIL` defaults to 0.
