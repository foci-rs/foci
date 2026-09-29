# FOCI

**F**ield **O**riented **C**ontrol **I**nterface is a Klipper/Kalico-compatible MCU firmware family for STM32 boards that drive TMC4671 FOC servo controller ICs, written in Rust.

This is the workspace orchestrator. It ties together the per-component repos as submodules and wires them with Cargo `[patch]` overrides so a single `cargo build` resolves the whole stack from local sources.

## Components

| Path | Repo | Purpose |
|---|---|---|
| `ankyra/` | [foci-rs/ankyra](https://github.com/foci-rs/ankyra) | Klipper protocol library |
| `shared/foci-usb-stm32/` | [foci-rs/foci-usb-stm32](https://github.com/foci-rs/foci-usb-stm32) | STM32 USB OTG CDC-ACM transport |
| `host/klipper-foci/` | [foci-rs/klipper-foci](https://github.com/foci-rs/klipper-foci) | Python Klipper extras module |
| `shared/foci-tmc4671/` | `foci-rs/foci-tmc4671` | TMC4671 chip driver |
| `shared/foci-klipper/` | `foci-rs/foci-klipper` | Klipper MCU protocol framework |
| `shared/foci-firmware/` | `foci-rs/foci-firmware` | Board-agnostic firmware: handlers, commissioning, trace |
| `boards/ouroboros-fw/` | `foci-rs/ouroboros-fw` | Firmware binary for Ouroboros (STM32H723, two stepper channels) |
| `boards/openffboard-fw/` | `foci-rs/openffboard-fw` | Firmware binary for OpenFFBoard v1.2.4 (STM32F407VG) |
| `host/foci-trace/` | `foci-rs/foci-trace` | Host-side USB trace capture and analysis tooling |

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

FOCI is alpha software. The implementation, commands, features and API can change.

## Disclaimer

This software controls real motion hardware. Improper configuration, electrical faults, or software bugs can cause sudden or uncontrolled motion, property damage, or injury.

The authors provide this software as-is, without warranty of any kind, express or implied. In no event shall the authors be liable for any damages, including but not limited to property damage, data loss, or personal injury, arising from the use or inability to use this software.

You are responsible for ensuring your installation is electrically safe, correctly wired, and compliant with local regulations. Keep clear of moving parts, and never leave an energized machine unattended without an independent way to cut motor power, such as an emergency stop.

## License

MIT OR Apache-2.0.
