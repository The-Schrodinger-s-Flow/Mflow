# Mflow — Automated Microfluidic Fluorescence Microscope

> **Built at the EMBO Hackathon Microscopy Workshop · ITQB NOVA, Lisbon**

Mflow is an open, reproducible automated microfluidic staining and imaging platform for **live/dead assays in bacterial cultures**. It was designed and built during the EMBO Hackathon Microscopy Workshop at ITQB NOVA (Oeiras, Lisbon) as a response to the challenge:

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
  - [Microscope Control (python-microscope)](#microscope-control-python-microscope)
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

**Organism:** *Bacillus* sp. ("Vasilis")  
**Stains used:**
| Stain | Target | Emission |
|---|---|---|
| SYTO 9 | All cells (live + dead) | Green (~530 nm) |
| Propidium Iodide (PI) | Dead cells only (compromised membrane) | Red (~617 nm) |

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
│         │  python-microscope  │             │
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
         │  Bacteria + PDL coating  │
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

| Item | Quantity | Notes |
|---|---|---|
| OpenFlexure Microscope (body) | 1 | Printed — see `freya_openscad/` |
| Infinity-corrected objective | 1 | e.g. 10× or 20×, plan achromat |
| 50 mm camera lens | 2 | One per camera, to focus fluorescence on sensor |
| Raspberry Pi Camera Module v2 | 2 | One for green channel, one for red channel |
| Blue LED (excitation) | 1 | ~470 nm peak |
| Dichroic mirror | 1 | Long-pass, splits green and red emission |
| Emission filter — green | 1 | ~530/30 nm bandpass |
| Emission filter — red | 1 | ~617/30 nm bandpass |

### Electronics

| Item | Quantity | Notes |
|---|---|---|
| Raspberry Pi 5 | 1 | Main controller |
| Raspberry Pi Pico | 2 | One for Sangaboard, one for pump CNC board |
| Sangaboard | 1 | OpenFlexure motor driver board |
| CNC control board | 1 | Drives Poseidon stepper motors |

### Microfluidics

| Item | Quantity | Notes |
|---|---|---|
| ibidi µ-Slide (single channel) | 1 | 1 inlet, 1 outlet |
| T-connector | 1 | Splits two pump lines into single inlet |
| Poseidon syringe pump | 2 | Open-source syringe pump |
| Syringe (compatible with Poseidon) | 2 | One per pump |
| Tubing (PTFE or silicone) | ~1 m | To connect pump → chip |

### Reagents

| Reagent | Purpose |
|---|---|
| SYTO 9 | Fluorescent stain — all cells (green) |
| Propidium Iodide (PI) | Fluorescent stain — dead cells (red) |
| PBS (Phosphate Buffered Saline) | Washing buffer |
| Poly-D-Lysine (PDL) | Bacterial adhesion coating |

---

## Hardware Assembly

### Optics

The microscope body is based on the **OpenFlexure** design. The dual-channel detection was added as a custom modification:

1. Print the microscope body from the files in `freya_openscad/` using a standard FDM printer (PLA or PETG recommended).
2. Mount the **infinity-corrected objective** in the OpenFlexure objective mount.
3. Place the **blue LED** in the illumination arm as the excitation source (~470 nm).
4. Install the **dichroic mirror** in the optical path above the objective to split emission into two arms.
5. Place the **green bandpass filter** (~530/30 nm) in the green arm and the **red bandpass filter** (~617/30 nm) in the red arm.
6. Mount one **50 mm camera lens** in front of each Raspberry Pi Camera v2 to relay the image onto the sensor.

### Electronics

1. Flash the **Sangaboard firmware** onto one Raspberry Pi Pico following the [OpenFlexure Sangaboard guide](https://openflexure.org).
2. Connect the Sangaboard to the OpenFlexure stage stepper motors.
3. Flash `steppercontrol.mpy` onto the second Raspberry Pi Pico and connect it to the CNC control board that drives the Poseidon pumps.
4. Connect both Raspberry Pi Camera v2 modules to the Raspberry Pi 5 via ribbon cables.
5. Connect the Sangaboard and the CNC/pump board to the Raspberry Pi 5 via USB.

### Microfluidics

1. Prepare the **ibidi µ-Slide** by coating the inner surface with **poly-D-lysine (PDL)**:
   - Pipette PDL solution into the chip channel.
   - Allow to **dry overnight** at room temperature.
   - Rinse gently with PBS before introducing bacteria.
2. Load your bacterial culture into the chip and allow adhesion for the appropriate time.
3. Connect the T-connector to the single inlet of the chip.
4. Attach **Poseidon Pump A** (loaded with PBS) and **Poseidon Pump B** (loaded with SYTO 9 + PI stain mixture) to the two arms of the T-connector.
5. Connect the chip outlet to a waste reservoir.

### 3D Printed Parts

All custom OpenSCAD design files are in `freya_openscad/`. Parts are designed for standard FDM printing:

- **Layer height:** 0.2 mm
- **Infill:** 20–30%
- **Material:** PLA or PETG
- **Supports:** As required per part (check per-file)

Open the `.scad` files in [OpenSCAD](https://openscad.org/), render, and export to STL for slicing.

---

## Software Setup

### Installation

```bash
git clone https://github.com/The-Schrodinger-s-Flow/Mflow.git
cd Mflow
python install_packages.py
```

### Microscope Control (python-microscope)

The system is controlled via [python-microscope](https://python-microscope.org/), configured through the YAML file in this repository.

1. Edit `trappyconfig.yaml` to match your hardware (device ports, camera indices, LED pin, etc.). The file contains comments — fill in any fields marked as gaps.
2. Run the main acquisition routine:

```bash
python routine.py
```

3. To launch the Sangaboard stage control GUI:

```bash
python sanga-python-gui.py
```

#### Key configuration parameters in `trappyconfig.yaml`

```yaml
# Fill in your device-specific values:
cameras:         # Raspberry Pi Camera v2 indices
led:             # Blue LED GPIO pin (via Pi Pico)
pumps:           # Serial port for CNC pump board
stage:           # Sangaboard serial port
```

> **Note:** The config file is included in the repo. Refer to it and patch in your specific port numbers and device addresses.

---

### Segmentation Pipeline

Located in `Segmentation/`. The script takes two fluorescence images as input and outputs live/dead statistics.

**Inputs:**
- `green_channel.png` — SYTO 9 image (all cells, green)
- `red_channel.png` — Propidium Iodide image (dead cells only, red)

**Algorithm:**
- Thresholding and **watershed segmentation** to separate touching cells
- Separate masks generated for total cells and dead cells

**Outputs:**
- `mask_all_cells.png` — mask of all cells (from green channel)
- `mask_dead_cells.png` — mask of dead cells (from red channel)
- `overlay_live_dead.png` — combined live/dead visualisation
- Console output with:
  - Total cell count
  - Dead cell count
  - Live/dead ratio

**Usage:**

```bash
python Segmentation/segment.py --green green_channel.png --red red_channel.png
```

---

## Protocol

### Full Experiment Procedure

1. **Chip preparation (night before):** Coat the ibidi µ-Slide channel with PDL. Allow to dry overnight.
2. **Bacterial loading:** Introduce bacterial suspension into the chip. Wait for adhesion.
3. **System startup:** Power on Raspberry Pi 5, connect cameras, Sangaboard, and pump board.
4. **Configuration:** Edit `trappyconfig.yaml` for your setup. Launch `routine.py`.
5. **Wash cycle:** Run Pump A (PBS) to wash unattached bacteria.
6. **Staining:** Run Pump B (SYTO 9 + PI mixture) to introduce stains.
7. **Imaging:** Capture simultaneous dual-channel images (green + red).
8. **Analysis:** Run segmentation script on captured images to obtain live/dead counts and ratio.

---

## Repository Structure

```
Mflow/
├── freya_openscad/       # OpenSCAD files for 3D printed microscope components
├── Segmentation/         # Python segmentation pipeline (live/dead cell counting)
├── routine.py            # Main acquisition and automation routine
├── sanga-python-gui.py   # GUI for Sangaboard stage control
├── steppercontrol.mpy    # MicroPython firmware for stepper/pump control (Pi Pico)
├── trappyconfig.yaml     # python-microscope device configuration file
├── install_packages.py   # Dependency installer
└── README.md
```

---

## Team

Built during the **EMBO Hackathon Microscopy Workshop** at **ITQB NOVA, Oeiras, Lisbon**.

*Team: The Schrödinger's Flow*

---

## License

This project is open hardware and open source. Hardware designs are shared under **CERN OHL v2**. Software is shared under the **MIT License**.

Reproducibility is a core goal — if something is unclear, please open an issue.
