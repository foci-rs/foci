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
