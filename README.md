# Mflow — Automated Microfluidic Fluorescence Microscope

> **Built at the EMBO Hackathon Microscopy Workshop · ITQB NOVA, Lisbon**

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
| OpenFlexure Microscope (body) | 1 | See `freya_openscad/` for the modified parts |
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
| Raspberry Pi Pico | 1 | One for pump CNC board  and for controlling the LED|
| Sangaboard | 1 | OpenFlexure motor driver board |
| CNC control board | 1 | Drives Poseidon stepper motors |

### Microfluidics

| Item | Quantity | Notes |
|---|---|---|
| ibidi µ-Slide (single channel) | 1 | 1 inlet, 1 outlet |
| T-connector | 1 | Splits two pump lines into single inlet |
| [Poseidon syringe pump](https://github.com/pachterlab/poseidon) | 2 | Open-source syringe pump |
| Syringe (compatible with Poseidon) | 2 | One per pump |
| Tubing (PTFE or silicone) | ~1 m | To connect pump → chip |

### Reagents

| Reagent | Purpose |
|---|---|
| SYTO 9 | Fluorescent stain — all cells (green) |
| Propidium Iodide (PI) | Fluorescent stain — dead cells (red) |
| PBS (Phosphate Buffered Saline) | Washing buffer |
| Poly-L-Lysine (PLL) | Bacterial adhesion coating |

---

## Hardware Assembly

### Optics

The microscope body is based on the **OpenFlexure** design. The dual-channel detection was added as a custom modification:

1. Assemble the o[penflexure v7 microscope](https://openflexure.org/projects/microscope/build#openflexure-microscope-v7), without the optics part.
2. Print custom filter cubes (check `freya_openscad`). 
3. Mount it to a breadboard with the custom mount plate (check `freya_openscad`). 
4. Mount the **infinity-corrected objective** in the OpenFlexure objective mount.
5. Place the **blue LED** in the illumination arm as the excitation source (~470 nm) within the custom cube arrangement.
6. Install the **dichroic mirror** in the optical path above the objective to split emission into two arms.
7. Place the **green bandpass filter** (~530/30 nm) in the green arm and the **red bandpass filter** (~617/30 nm) in the red arm.

### Electronics

1. Connect the sangaboard to the Raspberry Pi 5 and the OpenFlexure stage stepper motors ports.
3. Flash `steppercontrol.mpy` onto the second Raspberry Pi Pico and connect it to the CNC control board that drives the Poseidon pumps. Pins are specified in the file.
4. Connect both Raspberry Pi Camera v2 modules to the Raspberry Pi 5 via ribbon cables.
5. Also connect the illumination LED to the raspberry pi pico.
### Microfluidics

1. Prepare the **ibidi µ-Slide** by coating the inner surface with **poly-L-lysine (PLL)**:
   - Pipette PLL solution into the chip channel.
   - Allow to **dry overnight** at room temperature.
   - Rinse gently with PBS before introducing bacteria.
2. Load your bacterial culture into the chip and allow adhesion for the appropriate time.
3. Connect the T-connector to the single inlet of the chip.
4. Attach **Poseidon Pump Channel 1** (loaded with PBS) and **Poseidon Pump Channel 2** (loaded with SYTO 9 + PI stain mixture) to the two arms of the T-connector.
5. Connect the chip outlet to a waste reservoir.


## Software Setup

### Installation

1. ```bash
git clone https://github.com/The-Schrodinger-s-Flow/Mflow.git
cd Mflow
python install_packages.py
mv trappyconfig.yaml ~/trappyconfig.yaml
```
2. Install Trappy-Scopes
```git clone https://github.com/Trappy-Scopes/trappyscopes.git
    cd trappyscopes
    python main.py --install
```


### Microscope Control (python-microscope)

The system is controlled via [Trappy-Scopes]([https://python-microscope.org/](https://github.com/Trappy-Scopes/trappyscopes)), configured through the YAML file in this repository.

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
blue:           # Blue LED GPIO pin (via Pi Pico)
ch1:            # Pump 1
ch2:            # Pump 2
stage:         # Sangaboard serial port (if not using the GUI, otherwise comment-out this field)
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
cd <<experiment-folder>>
python Segmentation.py
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
