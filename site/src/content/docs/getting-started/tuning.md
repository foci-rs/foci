---
title: Tuning
description: Run FOCI_AUTOTUNE to tune each axis for production motion.
---

`FOCI_AUTOTUNE` measures how an axis actually responds to motor commands
and computes the position and speed control settings for your specific
motor and mechanics. Run it once per axis after
[Bring-up](/getting-started/bring-up/), before printing.

:::caution[Before you start]
- Takes roughly 10 to 15 minutes per motor.
- Homes and re-centers the toolhead repeatedly throughout the run,
  automatically. No action needed from you.
- The motor makes a range of sounds during tuning, including brief
  tones at some settings. This is expected.
- The toolhead moves on its own throughout, in both small and larger
  steps.
:::

## Run it

```gcode
FOCI_AUTOTUNE STEPPER=stepper_x
```

Run once for each axis. Requires `FOCI_SETUP` to have already run
(from Bring-up). Does not require the axis to already be homed. This
command homes itself as part of the run.

## What happens

1. **Homing and centering.** Before each of the phases below, the
   printer homes X and Y and moves the toolhead to a safe position near
   the center of the bed. This repeats several times over the run.
2. **Finding a starting point.** The axis makes a series of small,
   quick back-and-forth movements at increasing strength until it
   reliably moves in both directions.
3. **Confirming the result.** The axis repeats the same small movements
   once more to check the result holds.
4. **Testing recovery.** The axis runs at speed, then reverses
   direction abruptly, and tuning checks how cleanly it recovers. This
   runs for both directions.
5. **Fine-tuning position holding.** The axis moves out and back
   several times, at two speeds, at gradually increasing stiffness,
   until it settles on values that hold position smoothly. This phase
   is the one most likely to produce a brief tone at higher settings.
   That's expected, not a fault.

## Results

A successful run reports:

```text
FOCI_AUTOTUNE stepper_x: SUCCEEDED — tuned (velocity_p=755, velocity_i=256, position_p=199).
```

Repeat for the other axis. Any other result falls into one of four
cases:

- **Inconclusive.** Happens occasionally, not a problem. Run
  `FOCI_AUTOTUNE` again for that axis.
- **Rejected.** Run it again once for that axis. Try a different
  `PROFILE` (`conservative`, `balanced`, `stiff`):

  ```gcode
  FOCI_AUTOTUNE STEPPER=<stepper> PROFILE=conservative
  ```

  If it still keeps rejecting, stop retrying. This looks like a
  firmware tuning process issue that might require a firmware fix, not
  something adjustable from `printer.cfg`.

- **Hard failure** (a specific error naming what went wrong, for
  example a resistance or inductance fault):

  ```gcode
  RESTART
  FOCI_AUTOTUNE STEPPER=<stepper>
  ```

- **Safety fault.** The motor is disabled until Klipper restarts:

  ```gcode
  RESTART
  FOCI_AUTOTUNE STEPPER=<stepper>
  ```

## Validate the result

`FOCI_AUTOTUNE` checks how each motor responds on its own. It does not
run print-like paths, so a `SUCCEEDED` result doesn't prove your printer
moves well at the speeds and accelerations you actually print at. Check
that before trusting it.

The new gains are live but not saved yet: `FOCI_AUTOTUNE` stages them
for `SAVE_CONFIG`. Validate first. If the result is bad, `RESTART`
discards the staged gains and you're back to where you started.

:::caution
The toolhead moves at full print speed during these tests. Clear the
bed, keep a hand on emergency stop, either `M112` or your printer's
physical switch, and watch the first move of each step.
:::

### 1. Full-speed moves, both directions

Home, then run full-travel moves on each axis at your print speed, in
both directions. Repeat each move several times, back and forth:

```gcode
G28
G90
G1 X<min> F<speed, mm/min>
G1 X<max> F<speed, mm/min>
G1 Y<min> F<speed, mm/min>
G1 Y<max> F<speed, mm/min>
```

On CoreXY, also run diagonal moves, from `X<min> Y<min>` to
`X<max> Y<max>` and between the other two corners. Pure X and Y moves
drive both motors together, but each diagonal is driven by only one
motor, so a weak axis can hide until you run one.

Step up rather than starting at the target: run everything once at about
half your speed and acceleration, then at your target, then once at
10 to 20% above it. The last pass tells you how much margin you have.

### 2. What to look for

- **Sound.** Smooth motion, and quiet when holding position. A
  buzz at rest, or a tone during moves that wasn't there at half speed,
  means gains that are too high. See
  [Troubleshooting](/troubleshooting/).
- **Endpoints.** The toolhead stops cleanly at each end with no
  bounce, overshoot, or slow creep into position.
- **Errors.** No `Timer too close`, stall, or motor-fault messages in the
  console during any pass. Afterwards, run `DUMP_FOCI STEPPER=<stepper>`,
  which only reads state, and look for stall or fault flags.

If a pass fails, don't save. Lower the affected gains by 10 to 20%, as
described under [Manual tuning](/troubleshooting/#manual-tuning), or run
`FOCI_AUTOTUNE` again with `PROFILE=conservative`.

### 3. Save

Once the moves pass:

```gcode
SAVE_CONFIG
```

This restarts Klipper and loads the saved values. If
buzzing or a loose stop shows up later, after a long print, lower
`pid_position_p` a little rather than re-tuning.

### 4. Other checks

- **Print a ringing tower** with your usual settings. Look for rounded
  corners, ringing, and dimension errors.
- **Re-run input shaper calibration.** Tuning changes axis stiffness,
  which moves the resonance frequencies. Run `SHAPER_CALIBRATE`, or your
  usual routine, again and save the new shaper values.
- **Re-tune after mechanical changes.** Run `FOCI_AUTOTUNE` again after
  changing belts or belt tension, toolhead weight, `run_current`, or the
  motor.
