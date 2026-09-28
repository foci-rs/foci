---
title: Configuration
description: Klipper printer.cfg configuration for an Ouroboros board.
---

This page covers the minimum `printer.cfg` needed to get an Ouroboros board
recognized by Klipper, ready for `FOCI_SELFTEST` and `FOCI_SETUP` on both
steppers. Ouroboros is a single STM32H723 MCU driving two stepper channels,
so it needs one `[mcu]` section and one `[stepper_x]`/`[foci stepper_x]`
pair per channel, not two separate MCUs.

Tuned gains, encoder alignment, and everything else that `FOCI_AUTOTUNE`
and `FOCI_SETUP` persist come from `SAVE_CONFIG` afterward. None of that
belongs in this initial config.

## MCU

```ini
[mcu ouroboros]
serial: /dev/serial/by-id/usb-foci_FOCI_Ouroboros_<serial>-if00
```

Use the serial path you noted down in
[Installation](/getting-started/installation/).

## Stepper X and Y

Each axis needs a standard Klipper `[stepper_x]`/`[stepper_y]` section (FOCI
reads `microsteps`, `rotation_distance`, and `full_steps_per_rotation`
straight from it) plus a `[foci stepper_x]`/`[foci stepper_y]` section that
turns on the TMC4671 driver for that channel. The `foci` section name must
match the linked stepper section's name exactly; that's the only thing that
links the two.

Channel 0 is `STEP0`/`DIR0`/`ENA0`, channel 1 is `STEP1`/`DIR1`/`ENA1`. Swap
which physical stepper you wire to which channel if X and Y come out
reversed, rather than trying to swap the pin names.

```ini
[stepper_x]
step_pin: ouroboros:STEP0
dir_pin: ouroboros:DIR0
enable_pin: !ouroboros:ENA0
microsteps: 16
full_steps_per_rotation: 200
rotation_distance: 40
# A real endstop is still required by Klipper here. ^PA0 is the
# endstop on your main MCU; alternatively, wire the switch to
# Ouroboros' own STOP0 connector and use ouroboros:STOP0 instead. See
# Bring-up for FOCI's sensorless virtual_endstop option.
endstop_pin: ^PA0

[foci stepper_x]
run_current: 1.0
encoder_ppr: 1000

[stepper_y]
step_pin: ouroboros:STEP1
dir_pin: ouroboros:DIR1
enable_pin: !ouroboros:ENA1
microsteps: 16
full_steps_per_rotation: 200
rotation_distance: 40
# Same choice as X: ^PA1 (main MCU) or ouroboros:STOP1 (Ouroboros'
# own connector).
endstop_pin: ^PA1

[foci stepper_y]
run_current: 1.0
encoder_ppr: 1000
```

:::note[Keeping your existing physical endstops]
Changing `endstop_pin` is only necessary if you want to move a switch onto
Ouroboros' own endstop connector. If a switch is already wired to a board
you're keeping, such as a toolhead board, leave it there and leave that
axis's `endstop_pin` as it is.
:::

### Required fields

`run_current` and `encoder_ppr` are the only two fields `[foci <stepper>]`
requires.

- **`run_current`** is in amps. Start at 50-80% of your motor's rated
  phase current from its datasheet, then raise it later if `FOCI_AUTOTUNE`
  or your motion tests call for more headroom.
- **`encoder_ppr`** is your encoder's pulses-per-revolution rating, read
  off the encoder's or motor's datasheet or nameplate. It has nothing to
  do with `microsteps` or `full_steps_per_rotation`. The common
  LDO-42STH48-2504B-EN1000 ships with a 1000 PPR encoder, hence
  `encoder_ppr: 1000` in the example above.

## MCU and MOSFET temperature

Ouroboros exposes three analog channels as regular ADC pins: `MCU_TEMP`
(the STM32H723's internal die temperature) and `TH0`/`TH1` (one MOSFET
thermistor per channel). These work with Klipper's stock
`[temperature_sensor]` support directly:

```ini
[temperature_sensor ouroboros_mcu]
sensor_type: Generic 3950
sensor_pin: ouroboros:MCU_TEMP
min_temp: 0
max_temp: 120

[temperature_sensor ouroboros_tmc1_mosfet]
sensor_type: Generic 3950
sensor_pin: ouroboros:TH0
min_temp: 0
max_temp: 100

[temperature_sensor ouroboros_tmc2_mosfet]
sensor_type: Generic 3950
sensor_pin: ouroboros:TH1
min_temp: 0
max_temp: 100
```

Restart Klipper, then continue with
[Bring-up](/getting-started/bring-up/).
