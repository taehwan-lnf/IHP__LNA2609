# Specification

## Purpose

`LNA2609` is a characterisation vehicle, not an amplifier. It exists to measure SiGe HBTs
of the IHP SG13G2 process on wafer, so that compact models can be checked against silicon
in the regime where a low noise amplifier operates.

Because the die is a measurement instrument rather than a circuit, the parts of the RF IP
assessment that describe gain, output power, modulation or a link budget do not apply to
it.

## Die

| Item | Value |
|---|---|
| Top cell | `LNA2609` |
| Die size | 1.712 mm x 1.752 mm |
| Grid | 4 by 4 blocks |
| Outer seal ring | one, around the die |
| Inner seal rings | one per block |
| Pad style | ground-signal-ground, 100 um pitch |
| Metal stack | SG13G2 seven-layer aluminium BEOL |

## De-embedding standards

Four standards are included so that the pad and interconnect parasitics can be removed from
the measured device data.

| Cell | Standard |
|---|---|
| `GSG_open_sealring` | OPEN |
| `GSG_short_sealring` | SHORT |
| `GSG_thru_sealring` | THRU |
| `GSG_load_sealring` | LOAD |

## Devices under test

Twelve devices cover three SG13G2 HBT flavours at four emitter sizes each. The naming of a
device cell follows `GSG_dut_<model>_m1_Nx<stripes>_le<length>_we<width>_sealring`.

| Device | Emitter length | Emitter width | Emitter stripes Nx |
|---|---|---|---|
| `npn13g2`  | 0.9 um | 0.07 um | 22, 32, 39, 48 |
| `npn13g2l` | 2.5 um | 0.07 um | 8, 11, 14, 17 |
| `npn13g2v` | 2.5 um | 0.12 um | 6, 8, 10, 12 |

The three flavours differ in their emitter geometry and therefore in their transit
frequency and breakdown voltage, which is what makes the set useful for checking how the
compact models scale.

## Intended measurement

On-wafer S-parameter and DC measurement, with the four standards used to de-embed the pads
and launches. The measurement procedure, the setup description and the raw data will be
published under `measurements/` once the samples have been received and measured, as the
programme participation agreement requires.
