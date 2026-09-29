# FOCI

**F**ield **O**riented **C**ontrol **I**nterface — a Klipper/Kalico-compatible MCU firmware family for STM32 boards driving TMC4671 FOC servo controller ICs in Rust.

This is the workspace orchestrator. It ties together the per-component repos as submodules and wires them with Cargo `[patch]` overrides so a single `cargo build` resolves the whole stack from local sources.

## Components

| Path | Repo | Purpose |
|---|---|---|
| `ankyra/` | [foci-rs/ankyra](https://github.com/foci-rs/ankyra) | Klipper protocol library (clean rewrite). Independent workspace. |
| `shared/foci-tmc4671/` | [foci-rs/foci-tmc4671](https://github.com/foci-rs/foci-tmc4671) | TMC4671 chip driver |
| `shared/foci-klipper/` | [foci-rs/foci-klipper](https://github.com/foci-rs/foci-klipper) | Klipper MCU protocol framework |
| `shared/foci-usb-stm32/` | [foci-rs/foci-usb-stm32](https://github.com/foci-rs/foci-usb-stm32) | STM32 USB OTG CDC-ACM transport (GPL-3.0-or-later) |
| `shared/foci-firmware/` | [foci-rs/foci-firmware](https://github.com/foci-rs/foci-firmware) | Board-agnostic firmware: handlers, commissioning, trace |
| `boards/openffboard-fw/` | [foci-rs/openffboard-fw](https://github.com/foci-rs/openffboard-fw) | Firmware binary for OpenFFBoard v1.2.4 (STM32F407VG) |
| `host/klipper-foci/` | [foci-rs/klipper-foci](https://github.com/foci-rs/klipper-foci) | Python Klipper extras module (GPL-3.0) |

## Build

```bash
git clone --recurse-submodules git@github.com:foci-rs/foci.git
cd foci

# Host-side workspace (default-members: foci-tmc4671 + foci-klipper + foci-usb-stm32 + foci-firmware)
cargo build --release
cargo test
cargo clippy -- -D warnings

# Embedded board binary
cargo build -p openffboard-fw --target thumbv7em-none-eabi --release

# Ankyra (its own workspace)
cargo check --manifest-path ankyra/Cargo.toml
```

## Status

Pre-1.0; APIs may change without notice. Used in production firmware on the OpenFFBoard test rig but not yet versioned for external consumers.

## Disclaimer

This software controls real motion hardware. Improper configuration, electrical faults, or software bugs can cause sudden or uncontrolled motion, property damage, or injury.

Use entirely at your own risk. The authors provide this software as-is, without warranty of any kind, express or implied. In no event shall the authors be liable for any damages, including but not limited to property damage, data loss, or personal injury, arising from the use or inability to use this software.

You are responsible for ensuring your installation is electrically safe, correctly wired, and compliant with local regulations. Keep clear of moving parts, and never leave an energized machine unattended without an independent way to cut motor power, such as an emergency stop.

## License

MIT OR Apache-2.0 at the orchestrator level. Individual component repos carry their own license — see the table above. Notably, `foci-usb-stm32` is GPL-3.0-or-later and `klipper-foci` is GPL-3.0; consuming the full firmware binary inherits those terms.
