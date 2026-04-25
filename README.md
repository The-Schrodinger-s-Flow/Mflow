# Mflow — Automated Microfluidic Fluorescence Microscope

> **DISCLAMER: Build in 6 hours. It is a first concept. It does not work. The optics needs revision.**

> **Built at the EMBO Hack Your Microscopy Workshop · ITQB NOVA, Lisbon**


Mflow is an open, reproducible automated microfluidic staining and imaging platform for **live/dead assays in bacterial cultures**. It was designed and built during the EMBO Hack Your Microscopy Workshop at ITQB NOVA (Oeiras, Lisbon) as a response to the challenge:

> *"In-Situ Live/Dead Staining of Bacterial Cultures — build an automated microfluidic staining and imaging system for live/dead assays."*

The system combines an OpenFlexure-based microscope with dual-channel fluorescence detection, Poseidon syringe pumps, a pre-manufactured microfluidic chip, and a custom Python segmentation pipeline to quantify live vs. dead cells in real time.

---

## Table of Contents

- [Challenge Description](#challenge-description)
- [System Overview](#system-overview)
- [Bill of Materials](#bill-of-materials)
- [Hardware Assembly](#hardware-assembly)
  - [Optics](#optics)
  - [Electronics](#electronics)
  - [Microfluidics](#microfluidics)
  - [3D Printed Parts](#3d-printed-parts)
- [Software Setup](#software-setup)
  - [Microscope Control (Trappy-Scopes)](#microscope-control-trappy-scopes)
  - [Segmentation Pipeline](#segmentation-pipeline)
- [Protocol](#protocol)
- [Repository Structure](#repository-structure)
- [Team](#team)
- [License](#license)

---

## Challenge Description

The goal was to build a fully automated system capable of:

1. Flowing fluorescent viability stains over surface-adhered bacteria using microfluidics
2. Imaging the stained sample simultaneously in two fluorescence channels (green and red)
3. Automatically segmenting the images to count live cells, dead cells, and compute a live/dead ratio

**Organism:** *Bacillus subtilis*

**Stains used:**

| Stain | Target | Emission |
|---|---|---|
| SYTO 9 | All cells (live + dead) | Green (~500 nm) |
| Propidium Iodide (PI) | Dead cells only (compromised membrane) | Red (~618 nm) |

Both stains can be applied simultaneously and imaged in separate channels without cross-talk when using appropriate filters.

---

## System Overview

```
┌─────────────────────────────────────────────┐
│              Raspberry Pi 5                 │
│  ┌──────────────┐  ┌──────────────────────┐ │
│  │  Camera 1    │  │  Camera 2            │ │
│  │  (Green ch.) │  │  (Red ch.)           │ │
│  └──────┬───────┘  └──────────┬───────────┘ │
│         │    Trappy-Scopes    │             │
│         └────────────────┬────┘             │
│                          │                  │
│  ┌───────────────────────▼──────────────┐   │
│  │         Sangaboard (Pi Pico)         │   │
│  │    OpenFlexure XYZ Stage Control     │   │
│  └──────────────────────────────────────┘   │
│                                             │
│  ┌──────────────────────────────────────┐   │
│  │   CNC Control Board (Pi Pico)        │   │
│  │   Poseidon Pump A (PBS)              │   │
│  │   Poseidon Pump B (Stain mix)        │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
                      │
         ┌────────────▼─────────────┐
         │  ibidi µ-Slide (chip)    │
         │  Single channel, T-inlet │
         │  Bacteria + PLL coating  │
         └──────────────────────────┘
                      │
         ┌────────────▼─────────────┐
         │  OpenFlexure Microscope  │
         │  Infinity-corrected obj. │
         │  Blue LED excitation     │
         │  Dichroic + dual filter  │
         │  2 × Raspberry Pi Cam v2 │
         └──────────────────────────┘
```

---

## Bill of Materials

### Optics & Imaging

| Item | Part Number | Qty | Notes |
|---|---|---|---|
| OpenFlexure Microscope (body) | — | 1 | FDM printed — see `freya_openscad/` for modified parts |
| Infinity-corrected objective | — | 1 | Plan achromat, compatible with OpenFlexure mount |
| Achromatic doublet lens | [Thorlabs AC127-050-A](https://www.thorlabs.com/thorproduct.cfm?partnumber=AC127-050-A) | 2 | f = 50 mm, Ø½" (12.7 mm), ARC: 400–700 nm — one per camera |
| Raspberry Pi Camera Module v2 | — | 2 | One for green channel, one for red channel |
| Blue LED (excitation) | — | 1 | ~470 nm peak |

**Thorlabs MDF05 Filter Set — FITC (SYTO 9 / Green channel)**

| Component | Spec | Role |
|---|---|---|
| MDF05-FITC Excitation Filter | CWL = 479 nm, BW = 30 nm | Bandpass for blue LED excitation |
| MDF05-FITC Dichroic Mirror | R Band: 380–497 nm · T Band: 514.5–900 nm | Primary beam splitter |
| MDF05-FITC Emission Filter | CWL = 537 nm, BW = 40 nm | Green emission bandpass |

**Thorlabs MDF05 Filter Set — Texas Red (Propidium Iodide / Red channel)**

| Component | Spec | Role |
|---|---|---|
| MDF05-TXRED Dichroic Mirror | R Band: 381–460 nm · T Band: 608–900 nm | Separates red emission arm |
| MDF05-TXRED Emission Filter | CWL = 635.5 nm, BW = 58 nm | Red emission bandpass |

### Electronics

| Item | Qty | Notes |
|---|---|---|
| Raspberry Pi 5 | 1 | Main controller — runs Trappy-Scopes, cameras, and stage |
| Raspberry Pi Pico | 1 | Controls pump CNC board and blue LED; flashed with `steppercontrol.mpy` |
| [Sangaboard](https://sangaboard.readthedocs.io/en/latest/) | 1 | OpenFlexure motor driver board (integrated Pi Pico + stepper drivers) |
| [CNC Shield](https://mikroshop.ch/pdf/CNC-Shield-Guide.pdf) | 1 | Drives Poseidon stepper motors |

### Microfluidics

| Item | Qty | Notes |
|---|---|---|
| ibidi µ-Slide (single channel) | 1 | 1 inlet, 1 outlet |
| T-connector | 1 | Splits two pump lines into single chip inlet |
| [Poseidon syringe pump](https://github.com/pachterlab/poseidon) | 2 | Open-source syringe pump driven by CNC board |
| Compatible syringe | 2 | One per pump |
| PTFE or silicone tubing | ~1 m | Connects pumps to chip |

### Reagents

| Reagent | Purpose |
|---|---|
| SYTO 9 | Fluorescent stain — all cells (green channel) |
| Propidium Iodide (PI) | Fluorescent stain — dead cells only (red channel) |
| PBS (Phosphate Buffered Saline) | Washing buffer |
| Poly-L-Lysine (PLL) | Surface coating for bacterial adhesion |

---

## Hardware Assembly

### Optics

The microscope body is based on the **OpenFlexure** design with custom filter cubes and breadboard mount.

1. Assemble the [OpenFlexure v7 microscope body](https://openflexure.org/projects/microscope/build#openflexure-microscope-v7), **without** the standard optics module.
2. Print the custom filter cubes from `freya_openscad/` and mount them in the optical path above the objective.
3. Print and attach the custom breadboard mount plate (also in `freya_openscad/`) to fix the microscope to an optical breadboard.
4. Mount the **infinity-corrected objective** in the OpenFlexure objective port.
5. Install the **blue LED** paired with the **FITC Excitation Filter** (479/30 nm) in the illumination arm.
6. Install the **FITC Dichroic Mirror** (T: 514.5–900 nm) in the primary filter cube to direct excitation toward the sample and split emission into the green path.
7. Install the **Texas Red Dichroic Mirror** (T: 608–900 nm) in the secondary cube to split off the red path, with the **Texas Red Emission Filter** (635.5/58 nm) in the red detection arm and the **FITC Emission Filter** (537/40 nm) in the green detection arm.
8. Mount one **Thorlabs AC127-050-A** achromatic doublet (f = 50 mm, Ø½") in front of each Raspberry Pi Camera v2 to focus fluorescence onto the sensor.

### Electronics

1. Connect the **Sangaboard** to the Raspberry Pi 5 via USB, and wire it to the OpenFlexure stage stepper motors. Refer to the [Sangaboard documentation](https://sangaboard.readthedocs.io/en/latest/) for pin assignments.
2. Flash `steppercontrol.mpy` onto the **Raspberry Pi Pico** and connect it to the **CNC Shield** driving the Poseidon pumps. Pin assignments are specified in the file.
3. Connect the **blue LED** to the Raspberry Pi Pico (same Pico as the pumps). The LED pin is set in `trappyconfig.yaml`.
4. Connect both **Raspberry Pi Camera v2** modules to the Raspberry Pi 5 via ribbon cables.

### Microfluidics

1. Coat the **ibidi µ-Slide** channel with **Poly-L-Lysine (PLL)** for bacterial adhesion:
   - Pipette PLL solution to fill the channel completely.
   - Allow to **dry overnight** at room temperature.
   - Rinse gently with PBS before introducing bacteria.
2. Load the bacterial culture into the chip. Allow sufficient time for adhesion.
3. Connect the **T-connector** to the single inlet of the chip.
4. Attach **Poseidon Pump Channel 1** (PBS) and **Poseidon Pump Channel 2** (SYTO 9 + PI mixture) to the two arms of the T-connector.
5. Connect the chip outlet to a waste reservoir.

### 3D Printed Parts

All custom design files are in `freya_openscad/`, designed for standard FDM printing:

| Parameter | Value |
|---|---|
| Layer height | 0.2 mm |
| Infill | 20–30% |
| Material | PLA or PETG |
| Supports | As required per part |

Open `.scad` files in [OpenSCAD](https://openscad.org/), render, and export to STL for slicing.

---

## Software Setup

### Installation

```bash
git clone https://github.com/The-Schrodinger-s-Flow/Mflow.git
cd Mflow
python install_packages.py
mv trappyconfig.yaml ~/trappyconfig.yaml
```

Then install [Trappy-Scopes](https://github.com/Trappy-Scopes/trappyscopes):

```bash
git clone https://github.com/Trappy-Scopes/trappyscopes.git
cd trappyscopes
python main.py --install
```

---

### Microscope Control (Trappy-Scopes)

The system is controlled via **[Trappy-Scopes](https://github.com/Trappy-Scopes/trappyscopes)**, configured through `trappyconfig.yaml`.

1. Edit `trappyconfig.yaml` to match your hardware. Fill in any fields marked as gaps:

```yaml
cameras:    # Raspberry Pi Camera v2 indices
blue:       # Blue LED GPIO pin (via Pi Pico)
ch1:        # Pump Channel 1 serial port
ch2:        # Pump Channel 2 serial port
stage:      # Sangaboard serial port (comment out if controlling stage via sanga-python-gui instead)
```

2. Run the main acquisition routine:

```bash
python routine.py
```

3. To launch the Sangaboard stage control GUI separately:

```bash
python sanga-python-gui.py
```

---

### Segmentation Pipeline

Located in `Segmentation/`. Takes two fluorescence images as input and outputs live/dead cell statistics.

**Inputs:**

| File | Description |
|---|---|
| `green_channel.png` | SYTO 9 image — all cells (green) |
| `red_channel.png` | Propidium Iodide image — dead cells only (red) |

**Algorithm:** Thresholding followed by **watershed segmentation** to correctly separate touching or overlapping cells. Independent masks are computed for total cells and dead cells.

**Outputs:**

| File / Output | Description |
|---|---|
| `mask_all_cells.png` | Binary mask of all cells (from green channel) |
| `mask_dead_cells.png` | Binary mask of dead cells (from red channel) |
| `overlay_live_dead.png` | Combined live/dead false-colour overlay |
| Console | Total cell count · Dead cell count · Live/dead ratio |

**Usage:**

```bash
cd <experiment-folder>
python Segmentation.py
```

---

## Protocol

### Full Experiment Procedure

| Step | Action |
|---|---|
| **Night before** | Coat ibidi µ-Slide channel with PLL. Allow to dry overnight at RT. |
| **Day of experiment** | Load bacterial suspension into chip. Allow time for adhesion. |
| **System startup** | Power on Raspberry Pi 5. Connect cameras, Sangaboard, and CNC pump board via USB. |
| **Configure** | Edit `trappyconfig.yaml` with correct port addresses and move to `~/`. |
| **Wash** | Run Pump Channel 1 (PBS) to flush away unattached bacteria. |
| **Stain** | Run Pump Channel 2 (SYTO 9 + PI mixture) to deliver fluorescent stains. |
| **Image** | Capture simultaneous dual-channel images (green + red) via `routine.py`. |
| **Analyse** | Run `Segmentation.py` on captured images to obtain live/dead counts and ratio. |

---

## Repository Structure

```
Mflow/
├── freya_openscad/       # OpenSCAD files — custom filter cubes and breadboard mount
├── Segmentation/         # Python segmentation pipeline (live/dead cell counting)
├── routine.py            # Main acquisition and automation routine (Trappy-Scopes)
├── sanga-python-gui.py   # GUI for Sangaboard stage control
├── steppercontrol.mpy    # MicroPython firmware for pump stepper + LED control (Pi Pico)
├── trappyconfig.yaml     # Trappy-Scopes hardware configuration file
├── install_packages.py   # Dependency installer
└── README.md
```

---

## References

- [OpenFlexure Microscope v7 build guide](https://openflexure.org/projects/microscope/build#openflexure-microscope-v7)
- [Sangaboard documentation](https://sangaboard.readthedocs.io/en/latest/)
- [CNC Shield wiring guide](https://mikroshop.ch/pdf/CNC-Shield-Guide.pdf)
- [Poseidon open-source syringe pump](https://github.com/pachterlab/poseidon)
- [Trappy-Scopes microscope control software](https://github.com/Trappy-Scopes/trappyscopes)
- [Thorlabs AC127-050-A — f=50 mm, Ø½" Achromatic Doublet, ARC: 400–700 nm](https://www.thorlabs.com/thorproduct.cfm?partnumber=AC127-050-A)
- [Thorlabs MDF05 Filter Sets (FITC & Texas Red)](https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=12280)

---

## Team

Built during the **EMBO Hack Your Microscopy Workshop** at **ITQB NOVA, Oeiras, Lisbon**.

*Team: The Schrödinger's Flow*

---

## License

This project is open hardware and open source. Hardware designs are shared under **CERN OHL v2**.
Check specific software file for the licencing information.
Reproducibility is a core goal — if something is unclear, please open an issue.
