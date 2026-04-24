#!/usr/bin/env python3
"""
A simple Python GUI for controlling OpenFlexure's Sangaboard motor controller on its own. 
Maps sangaboard to a tkinter interface
Originally based on the sanga-python-gui I made for Heriot Watt at flim-sanga
https://gitlab.com/freyawhiteford/flim-sanga.
Freya Whiteford, University of Glasgow, 2025

"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, font
import threading
import time
import os
import numpy as np
from sangaboard import Sangaboard

# Setup Thorlabs DLL path before importing SDK
def setup_thorlabs_dlls():
    """Setup DLL paths for Thorlabs SDK"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_dll_path = os.path.join(script_dir, "dlls", "64_lib")
    
    if os.path.exists(local_dll_path):
        print(f"Setting up Thorlabs DLLs from: {local_dll_path}")
        
        # Add to PATH (for older Python versions)
        os.environ['PATH'] = local_dll_path + os.pathsep + os.environ['PATH']
        
        # Add DLL directory (Python 3.8+)
        if hasattr(os, 'add_dll_directory'):
            try:
                os.add_dll_directory(local_dll_path)
                print("Successfully added DLL directory")
                return True
            except Exception as e:
                print(f"Could not add DLL directory: {e}")
        return True
    else:
        print(f"DLL path not found: {local_dll_path}")
        return False

# Setup DLLs before importing camera libraries
dll_setup_success = setup_thorlabs_dlls()

# Camera-related imports (with fallbacks)
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("OpenCV not available - camera features will be disabled")

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("PIL/Pillow not available - camera display will be disabled")

try:
    if dll_setup_success:
        from thorlabs_tsi_sdk.tl_camera import TLCameraSDK
        from thorlabs_tsi_sdk.tl_camera_enums import SENSOR_TYPE
        THORLABS_SDK_AVAILABLE = True
        print("Thorlabs SDK imported successfully")
    else:
        THORLABS_SDK_AVAILABLE = False
        print("Thorlabs SDK not imported - DLL setup failed")
except ImportError as e:
    THORLABS_SDK_AVAILABLE = False
    print(f"Thorlabs TSI SDK not available: {e}")
except Exception as e:
    THORLABS_SDK_AVAILABLE = False
    print(f"Error importing Thorlabs SDK: {e}")


class SangaboardGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Sangaboard Control GUI")
        
        # Auto-scale window size based on screen resolution
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Set window size to 80% of screen size but with minimum dimensions
        window_width = max(1200, int(screen_width * 0.8))
        window_height = max(800, int(screen_height * 0.8))
        
        # Center the window on screen
        pos_x = (screen_width - window_width) // 2
        pos_y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{pos_x}+{pos_y}")
        self.root.minsize(1000, 700)  # Minimum size to prevent UI cutoff
        
        # Enable DPI awareness for better scaling on high-DPI displays
        try:
            self.root.tk.call('tk', 'scaling', self.root.winfo_fpixels('1i')/72.0)
        except:
            pass  # Ignore if scaling command fails
        
        # Configure fonts
        self.setup_fonts()
        
        # Load emblem image
        self.load_emblem_image()
        
        # Sangaboard instance
        self.sangaboard = None
        self.connected = False
        
        # Camera-related variables
        self.camera_sdk = None
        self.camera = None
        self.camera_running = False
        self.camera_thread = None
        self.current_frame = None
        self.current_display_image = None  # Store the RGB image for pixel readout
        self.image_scale_factor = 1.0      # Track scaling for coordinate conversion
        self.focus_measure = 0.0
        self.autofocus_running = False
        self.first_frame_logged = False  # Track if we've logged camera format info
        self.color_format_logged = False  # Track if we've logged color format detection
        self.bayer_logged = False  # Track if we've logged Bayer demosaicing
        self.is_bayer_camera = False  # Track if camera uses Bayer pattern
        self.camera_make = "N/A"
        self.camera_serial = "N/A"
        
        self.create_widgets()
        
    def setup_fonts(self):
        """Configure fonts for the GUI with adaptive sizing"""
        try:
            # Calculate font size based on screen resolution
            screen_width = self.root.winfo_screenwidth()
            base_font_size = max(9, min(12, int(screen_width / 160)))  # Scale font with screen size
            
            # Try to use Open Sans, fall back to system defaults if not available
            self.default_font = font.nametofont("TkDefaultFont")
            self.text_font = font.nametofont("TkTextFont")
            
            # Try to configure Open Sans
            try:
                self.default_font.configure(family="Open Sans", size=base_font_size)
                self.text_font.configure(family="Open Sans", size=base_font_size)
                print(f"Using Open Sans font, size {base_font_size}")
            except tk.TclError:
                # Open Sans not available, try common alternatives
                alternatives = ["Segoe UI", "Arial", "Helvetica"]
                for alt_font in alternatives:
                    try:
                        self.default_font.configure(family=alt_font, size=base_font_size)
                        self.text_font.configure(family=alt_font, size=base_font_size)
                        print(f"Using {alt_font} font, size {base_font_size} (Open Sans not available)")
                        break
                    except tk.TclError:
                        continue
                else:
                    # Use default system font with scaling
                    self.default_font.configure(size=base_font_size)
                    self.text_font.configure(size=base_font_size)
                    print(f"Using system default font, size {base_font_size} (Open Sans and alternatives not available)")
                    
        except Exception as e:
            print(f"Font configuration failed: {e}, using system defaults")
            
    def load_emblem_image(self):
        """Load and resize the emblem image"""
        try:
            # Get the path to the emblem image
            emblem_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "emblem_pink.png")
            
            if os.path.exists(emblem_path):
                # Load the image using tkinter's PhotoImage
                original_image = tk.PhotoImage(file=emblem_path)
                
                # Create a smaller version for the GUI display
                self.emblem_image = original_image.subsample(4, 4)  # Makes it 1/4 the size
                
                # Set the window icon (use original or smaller version)
                try:
                    self.root.iconphoto(True, original_image)
                    print(f"Set window icon from: {emblem_path}")
                except Exception as e:
                    print(f"Failed to set window icon: {e}")
                
                print(f"Loaded emblem image from: {emblem_path}")
                return True
            else:
                print(f"Emblem image not found at: {emblem_path}")
                self.emblem_image = None
                return False
                
        except Exception as e:
            print(f"Failed to load emblem image: {e}")
            self.emblem_image = None
            return False
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Create main control tab
        self.control_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.control_tab, text="Control")
        
        # Create camera tab
        self.camera_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.camera_tab, text="Camera")
        
        # Create about tab
        self.about_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.about_tab, text="About")
        
        # Create widgets for control tab
        self.create_control_widgets()
        
        # Create widgets for camera tab
        self.create_camera_widgets()
        
        # Create widgets for about tab
        self.create_about_widgets()
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
    def create_control_widgets(self):
        """Create widgets for the main control tab"""
        # Connection frame
        conn_frame = ttk.LabelFrame(self.control_tab, text="Connection", padding="5")
        conn_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=0, padx=(0, 5))
        self.port_var = tk.StringVar(value="COM3")  # Default port
        self.port_entry = ttk.Entry(conn_frame, textvariable=self.port_var, width=10)
        self.port_entry.grid(row=0, column=1, padx=(0, 10))
        
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=2, padx=(0, 10))
        
        self.status_label = ttk.Label(conn_frame, text="Disconnected", foreground="red")
        self.status_label.grid(row=0, column=3)
        
        # Add emblem in top-right if image loaded successfully
        if hasattr(self, 'emblem_image') and self.emblem_image:
            emblem_label = ttk.Label(conn_frame, image=self.emblem_image)
            emblem_label.grid(row=0, column=4, padx=(20, 0), sticky=tk.E)
            # Configure column to expand and push emblem to the right
            conn_frame.columnconfigure(4, weight=1)
        
        # Control frame
        control_frame = ttk.LabelFrame(self.control_tab, text="Axis Control", padding="5")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Position display and controls
        pos_frame = ttk.Frame(control_frame)
        pos_frame.grid(row=0, column=0, columnspan=6, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Current position display
        ttk.Label(pos_frame, text="Current Position:").grid(row=0, column=0, padx=(0, 10))
        self.position_var = tk.StringVar(value="X: -, Y: -, Z: -")
        ttk.Label(pos_frame, textvariable=self.position_var).grid(row=0, column=1)
        
        ttk.Button(pos_frame, text="Move to Zero", command=self.move_to_zero).grid(row=0, column=2, padx=(10, 0))
        
        # Position control dropdown
        self.position_menu_var = tk.StringVar(value="Position Actions")
        position_menu = ttk.Combobox(pos_frame, textvariable=self.position_menu_var, 
                                   values=["Position Actions", "Set Position as Zero"], 
                                   state="readonly", width=15)
        position_menu.grid(row=0, column=3, padx=(10, 0))
        position_menu.bind('<<ComboboxSelected>>', self.on_position_action_selected)
        
        # Absolute position controls
        abs_frame = ttk.Frame(control_frame)
        abs_frame.grid(row=1, column=0, columnspan=6, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(abs_frame, text="Absolute Position:").grid(row=0, column=0, padx=(0, 10))
        
        # Create absolute position entries for each axis
        self.abs_position_vars = {}
        for i, axis in enumerate(['X', 'Y', 'Z']):
            ttk.Label(abs_frame, text=f"{axis}:").grid(row=0, column=1+i*2, padx=(10, 5))
            self.abs_position_vars[axis.lower()] = tk.StringVar(value="0")
            abs_entry = ttk.Entry(abs_frame, textvariable=self.abs_position_vars[axis.lower()], width=8)
            abs_entry.grid(row=0, column=2+i*2, padx=(0, 10))
        
        ttk.Button(abs_frame, text="Move to Absolute", command=self.move_to_absolute).grid(row=0, column=7, padx=(10, 0))
        
        # Movement mode selection
        mode_frame = ttk.Frame(control_frame)
        mode_frame.grid(row=2, column=0, columnspan=6, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(mode_frame, text="Movement Mode:").grid(row=0, column=0, padx=(0, 10))
        self.move_mode_var = tk.StringVar(value="normal")
        ttk.Radiobutton(mode_frame, text="Normal Move", variable=self.move_mode_var, 
                       value="normal").grid(row=0, column=1, padx=(0, 10))
        ttk.Radiobutton(mode_frame, text="Move with Pulses", variable=self.move_mode_var, 
                       value="pulses").grid(row=0, column=2, padx=(0, 10))
        
        # Axis movement controls
        axes = ['X', 'Y', 'Z']
        self.displacement_vars = {}
        self.interval_vars = {}
        
        for i, axis in enumerate(axes):
            row = i + 3  # Start from row 3 now due to additional position controls
            
            # Axis label
            ttk.Label(control_frame, text=f"{axis} Axis:").grid(row=row, column=0, padx=(0, 10), sticky=tk.W)
            
            # Displacement entry
            ttk.Label(control_frame, text="Steps:").grid(row=row, column=1, padx=(0, 5))
            self.displacement_vars[axis.lower()] = tk.StringVar(value="0")
            disp_entry = ttk.Entry(control_frame, textvariable=self.displacement_vars[axis.lower()], width=10)
            disp_entry.grid(row=row, column=2, padx=(0, 10))
            
            # Interval entry (only used for pulse mode)
            ttk.Label(control_frame, text="Interval (steps):").grid(row=row, column=3, padx=(0, 5))
            self.interval_vars[axis.lower()] = tk.StringVar(value="1")
            interval_entry = ttk.Entry(control_frame, textvariable=self.interval_vars[axis.lower()], width=10)
            interval_entry.grid(row=row, column=4, padx=(0, 10))
            
            # Movement buttons
            btn_frame = ttk.Frame(control_frame)
            btn_frame.grid(row=row, column=5, padx=(10, 0))
            
            ttk.Button(btn_frame, text="Move", width=6,
                      command=lambda a=axis.lower(): self.move_axis_exact(a)).grid(row=0, column=0)
        
        # Multi-axis movement
        multi_frame = ttk.LabelFrame(self.control_tab, text="Multi-Axis Movement", padding="5")
        multi_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0), pady=(0, 10))
        
        ttk.Label(multi_frame, text="X Steps:").grid(row=0, column=0, padx=(0, 5))
        self.multi_x_var = tk.StringVar(value="0")
        ttk.Entry(multi_frame, textvariable=self.multi_x_var, width=8).grid(row=0, column=1, padx=(0, 10))
        
        ttk.Label(multi_frame, text="Y Steps:").grid(row=1, column=0, padx=(0, 5))
        self.multi_y_var = tk.StringVar(value="0")
        ttk.Entry(multi_frame, textvariable=self.multi_y_var, width=8).grid(row=1, column=1, padx=(0, 10))
        
        ttk.Label(multi_frame, text="Z Steps:").grid(row=2, column=0, padx=(0, 5))
        self.multi_z_var = tk.StringVar(value="0")
        ttk.Entry(multi_frame, textvariable=self.multi_z_var, width=8).grid(row=2, column=1, padx=(0, 10))
        
        ttk.Label(multi_frame, text="Interval (steps):").grid(row=3, column=0, padx=(0, 5))
        self.multi_interval_var = tk.StringVar(value="1")
        ttk.Entry(multi_frame, textvariable=self.multi_interval_var, width=8).grid(row=3, column=1, padx=(0, 10))
        
        ttk.Button(multi_frame, text="Move All Axes", command=self.move_multi_axis).grid(row=4, column=0, columnspan=2, pady=(10, 0))
        
        # Settings frame
        settings_frame = ttk.LabelFrame(self.control_tab, text="Motor Settings", padding="5")
        settings_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(settings_frame, text="Step Time (μs):").grid(row=0, column=0, padx=(0, 5))
        self.step_time_var = tk.StringVar(value="1000")
        self.step_time_entry = ttk.Entry(settings_frame, textvariable=self.step_time_var, width=10)
        self.step_time_entry.grid(row=0, column=1, padx=(0, 10))
        ttk.Button(settings_frame, text="Set", command=self.set_step_time).grid(row=0, column=2, padx=(0, 20))
        
        ttk.Label(settings_frame, text="Ramp Time (μs):").grid(row=0, column=3, padx=(0, 5))
        self.ramp_time_var = tk.StringVar(value="10000")
        self.ramp_time_entry = ttk.Entry(settings_frame, textvariable=self.ramp_time_var, width=10)
        self.ramp_time_entry.grid(row=0, column=4, padx=(0, 10))
        ttk.Button(settings_frame, text="Set", command=self.set_ramp_time).grid(row=0, column=5)
        
        ttk.Button(settings_frame, text="Release Motors", command=self.release_motors).grid(row=1, column=0, pady=(10, 0))
        ttk.Button(settings_frame, text="Get Current Settings", command=self.get_current_settings).grid(row=1, column=1, columnspan=2, pady=(10, 0))
        ttk.Button(settings_frame, text="Self Test", command=self.run_self_test).grid(row=1, column=3, columnspan=2, pady=(10, 0), padx=(10, 0))
        
        # Log frame
        log_frame = ttk.LabelFrame(self.control_tab, text="Log", padding="5")
        log_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Button(log_frame, text="Clear Log", command=self.clear_log).grid(row=1, column=0, pady=(5, 0))
        
        # Configure grid weights for control tab
        self.control_tab.columnconfigure(0, weight=1)
        self.control_tab.columnconfigure(1, weight=1)
        self.control_tab.rowconfigure(3, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
    def create_about_widgets(self):
        """Create widgets for the about tab"""
        # Main frame for about content
        about_frame = ttk.Frame(self.about_tab, padding="20")
        about_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(about_frame, text="Sangaboard Control GUI", font=("Open Sans", 16, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # Add emblem if available
        if hasattr(self, 'emblem_image') and self.emblem_image:
            emblem_about = ttk.Label(about_frame, image=self.emblem_image)
            emblem_about.grid(row=1, column=0, pady=(0, 20))
        
        # About text
        about_text = scrolledtext.ScrolledText(about_frame, height=20, width=70, wrap=tk.WORD)
        about_text.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 20))
        
        # Repository information
        repo_info = """A Python GUI for directly controlling Sangaboard motor controller boards 0.5.x and up without the use of a Raspberry Pi or OpenFlexure Connect.

Connect a Sangaboard via USB to your computer and select its COM port (usually COM3 or COM4 on Windows) to get started.

Originally intended to be used with Sangaboards running the GLOING move-with-pulses fork of firmware to support 3V3 trigger pulse commands on Sangaboard pin AUX1.
Insert the contents of sangaboard-lib-snippet.py into sangaboard.py once pysangaboard is pip installed to enable pulse functionality.


GLOING fork: https://gitlab.com/gloing/sangaboard-firmware

Original OpenFlexure Sangaboard firmware by Filip Ayazi: https://gitlab.com/filipayazi/sangaboard-firmware

pysangaboard library: https://sangaboard.readthedocs.io/en/latest/index.html
'pip install sangaboard'

This GUI's original repo: https://gitlab.com/freyawhiteford/flim-sanga

Shoutout to Schrödinger's flow at EMBO Hack Your Microscope 2026!

https://openflexure.org/

This GUI thrown together by Freya Whiteford, University of Glasgow, April 2026 after September 2025
(with thanks to Dr Richard Bowman for modifying the Sangaboard firmware)

GPLv3 

"""
        
        about_text.insert(tk.END, repo_info)
        about_text.config(state=tk.DISABLED)  # Make it read-only
        
        # Configure grid weights for about tab
        self.about_tab.columnconfigure(0, weight=1)
        self.about_tab.rowconfigure(0, weight=1)
        about_frame.columnconfigure(0, weight=1)
        about_frame.rowconfigure(2, weight=1)
        
    def create_camera_widgets(self):
        """Create widgets for the camera tab"""
        # Check if camera dependencies are available
        camera_available = CV2_AVAILABLE and PIL_AVAILABLE and THORLABS_SDK_AVAILABLE
        
        if not camera_available:
            # Show installation instructions if dependencies missing
            install_frame = ttk.Frame(self.camera_tab, padding="20")
            install_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            
            ttk.Label(install_frame, text="Camera Support - Installation Required", 
                     font=("Open Sans", 14, "bold")).grid(row=0, column=0, pady=(0, 20))
            
            missing_deps = []
            if not CV2_AVAILABLE:
                missing_deps.append("• OpenCV: pip install opencv-python")
            if not PIL_AVAILABLE:
                missing_deps.append("• Pillow: pip install Pillow")
            if not THORLABS_SDK_AVAILABLE:
                missing_deps.append("• Thorlabs TSI SDK: pip install thorlabs-tsi-camera-python")
                if not dll_setup_success:
                    missing_deps.append("• DLL Setup Issue: Check dlls/64_lib folder contains Thorlabs DLLs")
            
            install_text = f"""To enable camera functionality, please install the following dependencies:

{chr(10).join(missing_deps)}

Installation Steps:
1. Install Python packages: pip install opencv-python Pillow thorlabs-tsi-camera-python
2. Ensure Thorlabs DLLs are in: dlls/64_lib/ folder
3. If DLLs are missing, copy them from Thorlabs ThorCam installation
4. Typical DLL location: C:\\Program Files\\Thorlabs\\Scientific Imaging\\...\\Native_64_lib

DLL Setup Status: {'✓ Success' if dll_setup_success else '✗ Failed - Check DLL path'}

After installation, restart the application to enable camera features."""
            
            ttk.Label(install_frame, text=install_text, wraplength=600).grid(row=1, column=0)
            
            self.camera_tab.columnconfigure(0, weight=1)
            self.camera_tab.rowconfigure(0, weight=1)
            return
        
        # Main camera frame
        main_camera_frame = ttk.Frame(self.camera_tab, padding="10")
        main_camera_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Left panel - Camera display
        display_frame = ttk.LabelFrame(main_camera_frame, text="Camera Feed", padding="5")
        display_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Camera display label
        self.camera_display = ttk.Label(display_frame, text="No Camera Connected", 
                                       background="black", foreground="white")
        self.camera_display.grid(row=0, column=0, padx=10, pady=10)
        
        # Camera connection controls
        cam_conn_frame = ttk.Frame(display_frame)
        cam_conn_frame.grid(row=1, column=0, pady=(10, 0))
        
        self.connect_camera_btn = ttk.Button(cam_conn_frame, text="Connect Camera", 
                                           command=self.toggle_camera_connection)
        self.connect_camera_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.camera_status_label = ttk.Label(cam_conn_frame, text="Disconnected", foreground="red")
        self.camera_status_label.grid(row=0, column=1)
        
        # Right panel - Controls with scrollable frame
        controls_outer_frame = ttk.Frame(main_camera_frame)
        controls_outer_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create scrollable area for camera controls
        canvas = tk.Canvas(controls_outer_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(controls_outer_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Add mouse wheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind("<MouseWheel>", on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", on_mousewheel)
        
        # Pack scrollable components
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Create controls frame inside scrollable area
        controls_frame = ttk.LabelFrame(scrollable_frame, text="Camera Controls", padding="5")
        controls_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Camera settings
        settings_subframe = ttk.LabelFrame(controls_frame, text="Camera Settings", padding="5")
        settings_subframe.pack(fill="x", pady=(0, 10))
        
        ttk.Label(settings_subframe, text="Exposure (ms):").grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        self.exposure_var = tk.StringVar(value="10")
        self.exposure_entry = ttk.Entry(settings_subframe, textvariable=self.exposure_var, width=10)
        self.exposure_entry.grid(row=0, column=1, padx=(0, 10))
        ttk.Button(settings_subframe, text="Set", command=self.set_exposure).grid(row=0, column=2)
        
        ttk.Label(settings_subframe, text="Gain:").grid(row=1, column=0, padx=(0, 5), sticky=tk.W, pady=(5, 0))
        self.gain_var = tk.StringVar(value="1")
        self.gain_entry = ttk.Entry(settings_subframe, textvariable=self.gain_var, width=10)
        self.gain_entry.grid(row=1, column=1, padx=(0, 10), pady=(5, 0))
        ttk.Button(settings_subframe, text="Set", command=self.set_gain).grid(row=1, column=2, pady=(5, 0))
        
        # Display mode controls
        ttk.Label(settings_subframe, text="Display Mode:").grid(row=2, column=0, padx=(0, 5), sticky=tk.W, pady=(10, 0))
        self.display_mode_var = tk.StringVar(value="auto")
        display_mode_frame = ttk.Frame(settings_subframe)
        display_mode_frame.grid(row=2, column=1, columnspan=2, sticky=tk.W, pady=(10, 0))
        
        ttk.Radiobutton(display_mode_frame, text="Auto", variable=self.display_mode_var, 
                       value="auto").grid(row=0, column=0, padx=(0, 10))
        ttk.Radiobutton(display_mode_frame, text="Color", variable=self.display_mode_var, 
                       value="color").grid(row=0, column=1, padx=(0, 10))
        ttk.Radiobutton(display_mode_frame, text="Grayscale", variable=self.display_mode_var, 
                       value="grayscale").grid(row=0, column=2)
        
        # Color format controls for troubleshooting
        ttk.Label(settings_subframe, text="Color Format:").grid(row=3, column=0, padx=(0, 5), sticky=tk.W, pady=(10, 0))
        self.color_format_var = tk.StringVar(value="auto")
        color_format_frame = ttk.Frame(settings_subframe)
        color_format_frame.grid(row=3, column=1, columnspan=2, sticky=tk.W, pady=(10, 0))
        
        ttk.Radiobutton(color_format_frame, text="Auto", variable=self.color_format_var, 
                       value="auto", command=self.on_color_format_change).grid(row=0, column=0, padx=(0, 10))
        ttk.Radiobutton(color_format_frame, text="RGB", variable=self.color_format_var, 
                       value="rgb", command=self.on_color_format_change).grid(row=0, column=1, padx=(0, 10))
        ttk.Radiobutton(color_format_frame, text="BGR", variable=self.color_format_var, 
                       value="bgr", command=self.on_color_format_change).grid(row=0, column=2)
        
        # Bayer pattern controls for raw camera data
        ttk.Label(settings_subframe, text="Bayer Pattern:").grid(row=4, column=0, padx=(0, 5), sticky=tk.W, pady=(10, 0))
        self.bayer_pattern_var = tk.StringVar(value="auto")
        bayer_pattern_frame = ttk.Frame(settings_subframe)
        bayer_pattern_frame.grid(row=4, column=1, columnspan=2, sticky=tk.W, pady=(10, 0))
        
        ttk.Radiobutton(bayer_pattern_frame, text="Auto", variable=self.bayer_pattern_var, 
                       value="auto", command=self.on_bayer_pattern_change).grid(row=0, column=0, padx=(0, 5))
        ttk.Radiobutton(bayer_pattern_frame, text="BGGR", variable=self.bayer_pattern_var, 
                       value="0", command=self.on_bayer_pattern_change).grid(row=0, column=1, padx=(0, 5))
        ttk.Radiobutton(bayer_pattern_frame, text="GBRG", variable=self.bayer_pattern_var, 
                       value="1", command=self.on_bayer_pattern_change).grid(row=0, column=2, padx=(0, 5))
        ttk.Radiobutton(bayer_pattern_frame, text="RGGB", variable=self.bayer_pattern_var, 
                       value="2", command=self.on_bayer_pattern_change).grid(row=1, column=0, padx=(0, 5))
        ttk.Radiobutton(bayer_pattern_frame, text="GRBG", variable=self.bayer_pattern_var, 
                       value="3", command=self.on_bayer_pattern_change).grid(row=1, column=1, padx=(0, 5))
        ttk.Radiobutton(bayer_pattern_frame, text="None", variable=self.bayer_pattern_var, 
                       value="none", command=self.on_bayer_pattern_change).grid(row=1, column=2, padx=(0, 5))
        
        # Camera information
        info_subframe = ttk.LabelFrame(controls_frame, text="Camera Information", padding="5")
        info_subframe.pack(fill="x", pady=(0, 10))
        
        ttk.Label(info_subframe, text="Camera Make:").grid(row=0, column=0, padx=(0, 10), sticky=tk.W)
        self.camera_make_var = tk.StringVar(value="N/A")
        ttk.Label(info_subframe, textvariable=self.camera_make_var).grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(info_subframe, text="Serial Number:").grid(row=1, column=0, padx=(0, 10), sticky=tk.W, pady=(5, 0))
        self.camera_serial_var = tk.StringVar(value="N/A")
        ttk.Label(info_subframe, textvariable=self.camera_serial_var).grid(row=1, column=1, sticky=tk.W, pady=(5, 0))
        
        ttk.Label(info_subframe, text="Frame Size:").grid(row=2, column=0, padx=(0, 10), sticky=tk.W, pady=(5, 0))
        self.frame_size_var = tk.StringVar(value="N/A")
        ttk.Label(info_subframe, textvariable=self.frame_size_var).grid(row=2, column=1, sticky=tk.W, pady=(5, 0))
        
        ttk.Label(info_subframe, text="Focus Measure:").grid(row=3, column=0, padx=(0, 10), sticky=tk.W, pady=(5, 0))
        self.focus_measure_var = tk.StringVar(value="0.00")
        ttk.Label(info_subframe, textvariable=self.focus_measure_var).grid(row=3, column=1, sticky=tk.W, pady=(5, 0))
        
        # RGB/Grayscale values at cursor (mouse position)
        rgb_subframe = ttk.LabelFrame(controls_frame, text="Pixel Values (at cursor)", padding="5")
        rgb_subframe.pack(fill="x", pady=(0, 10))
        
        ttk.Label(rgb_subframe, text="Position:").grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        self.cursor_pos_var = tk.StringVar(value="x: -, y: -")
        ttk.Label(rgb_subframe, textvariable=self.cursor_pos_var).grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(rgb_subframe, text="Values:").grid(row=1, column=0, padx=(0, 5), sticky=tk.W, pady=(5, 0))
        self.rgb_values_var = tk.StringVar(value="N/A")
        ttk.Label(rgb_subframe, textvariable=self.rgb_values_var).grid(row=1, column=1, sticky=tk.W, pady=(5, 0))
        
        # Bind mouse motion to camera display for RGB readout
        self.camera_display.bind("<Motion>", self.on_mouse_motion)
        self.camera_display.bind("<Leave>", self.on_mouse_leave)
        
        # Stage movement controls
        stage_subframe = ttk.LabelFrame(controls_frame, text="Stage Movement", padding="5")
        stage_subframe.pack(fill="x", pady=(0, 10))
        
        # Step size controls
        step_frame = ttk.Frame(stage_subframe)
        step_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(step_frame, text="Step Size:").grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        
        ttk.Label(step_frame, text="X:").grid(row=0, column=1, padx=(10, 2), sticky=tk.W)
        self.camera_step_x_var = tk.StringVar(value="10")
        ttk.Entry(step_frame, textvariable=self.camera_step_x_var, width=8).grid(row=0, column=2, padx=(0, 10))
        
        ttk.Label(step_frame, text="Y:").grid(row=0, column=3, padx=(5, 2), sticky=tk.W)
        self.camera_step_y_var = tk.StringVar(value="10")
        ttk.Entry(step_frame, textvariable=self.camera_step_y_var, width=8).grid(row=0, column=4, padx=(0, 10))
        
        ttk.Label(step_frame, text="Z:").grid(row=0, column=5, padx=(5, 2), sticky=tk.W)
        self.camera_step_z_var = tk.StringVar(value="10")
        ttk.Entry(step_frame, textvariable=self.camera_step_z_var, width=8).grid(row=0, column=6, padx=(0, 10))
        
        # Pulse enable checkbox
        self.camera_pulse_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(step_frame, text="Use Pulses", variable=self.camera_pulse_var).grid(row=0, column=7, padx=(10, 0))
        
        # X-axis controls
        x_frame = ttk.LabelFrame(stage_subframe, text="X-Axis", padding="3")
        x_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        ttk.Button(x_frame, text="← -X", command=lambda: self.camera_move_relative('x', -1), 
                  width=8).grid(row=0, column=0, padx=2, pady=2)
        ttk.Button(x_frame, text="+X →", command=lambda: self.camera_move_relative('x', 1), 
                  width=8).grid(row=0, column=1, padx=2, pady=2)
        
        # Y-axis controls  
        y_frame = ttk.LabelFrame(stage_subframe, text="Y-Axis", padding="3")
        y_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        
        ttk.Button(y_frame, text="↑ +Y", command=lambda: self.camera_move_relative('y', 1), 
                  width=8).grid(row=0, column=0, padx=2, pady=2)
        ttk.Button(y_frame, text="↓ -Y", command=lambda: self.camera_move_relative('y', -1), 
                  width=8).grid(row=1, column=0, padx=2, pady=2)
        
        # Z-axis controls
        z_frame = ttk.LabelFrame(stage_subframe, text="Z-Axis", padding="3")
        z_frame.grid(row=1, column=2, sticky=(tk.W, tk.E), padx=(5, 0))
        
        ttk.Button(z_frame, text="↑ +Z", command=lambda: self.camera_move_relative('z', 1), 
                  width=8).grid(row=0, column=0, padx=2, pady=2)
        ttk.Button(z_frame, text="↓ -Z", command=lambda: self.camera_move_relative('z', -1), 
                  width=8).grid(row=1, column=0, padx=2, pady=2)
        
        # Configure grid weights for stage controls
        stage_subframe.columnconfigure(0, weight=1)
        stage_subframe.columnconfigure(1, weight=1)
        stage_subframe.columnconfigure(2, weight=1)
        
        # Configure grid weights
        self.camera_tab.columnconfigure(0, weight=1)
        self.camera_tab.rowconfigure(0, weight=1)
        main_camera_frame.columnconfigure(0, weight=1)
        main_camera_frame.columnconfigure(1, weight=1)
        main_camera_frame.rowconfigure(0, weight=1)
        controls_outer_frame.columnconfigure(0, weight=1)
        controls_outer_frame.rowconfigure(0, weight=1)
        
    def log_message(self, message):
        """Add a message to the log with timestamp"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def clear_log(self):
        """Clear the log text"""
        self.log_text.delete(1.0, tk.END)
        
    def toggle_connection(self):
        """Connect or disconnect from the Sangaboard"""
        if not self.connected:
            try:
                port = self.port_var.get().strip()
                if not port:
                    messagebox.showerror("Error", "Please enter a valid port")
                    return
                    
                self.log_message(f"Connecting to Sangaboard on port {port}...")
                self.sangaboard = Sangaboard(port=port, timeout=3)
                
                # Test the connection
                position = self.sangaboard.position
                self.log_message(f"Connected successfully! Current position: {position}")
                
                self.connected = True
                self.connect_btn.config(text="Disconnect")
                self.status_label.config(text="Connected", foreground="green")
                self.port_entry.config(state="disabled")
                
                # Update current position and settings
                self.update_position()
                self.get_current_settings()
                
            except Exception as e:
                self.log_message(f"Connection failed: {str(e)}")
                messagebox.showerror("Connection Error", f"Failed to connect to Sangaboard:\n{str(e)}")
                if self.sangaboard:
                    try:
                        self.sangaboard.close()
                    except:
                        pass
                    self.sangaboard = None
        else:
            try:
                if self.sangaboard:
                    self.sangaboard.close()
                    self.log_message("Disconnected from Sangaboard")
                
                self.connected = False
                self.connect_btn.config(text="Connect")
                self.status_label.config(text="Disconnected", foreground="red")
                self.port_entry.config(state="normal")
                self.sangaboard = None
                
            except Exception as e:
                self.log_message(f"Error during disconnection: {str(e)}")
                
    def check_connection(self):
        """Check if connected to Sangaboard"""
        if not self.connected or not self.sangaboard:
            messagebox.showerror("Error", "Not connected to Sangaboard")
            return False
        return True
        
    def move_axis_exact(self, axis):
        """Move specified axis by the exact value entered (positive or negative)"""
        if not self.check_connection():
            return
            
        try:
            displacement = int(self.displacement_vars[axis].get())
            if displacement == 0:
                self.log_message(f"No movement - displacement is 0 for {axis.upper()} axis")
                return
                
            mode = self.move_mode_var.get()
            
            direction = "+" if displacement > 0 else ""
            self.log_message(f"Moving {axis.upper()} axis {direction}{displacement} steps in {mode} mode")
            
            # Run in separate thread to prevent GUI freezing
            def move():
                try:
                    if mode == "pulses":
                        interval = int(self.interval_vars[axis].get())
                        self.log_message(f"Using pulse interval: {interval} steps")
                        self.sangaboard.move_rel_with_pulses(displacement, interval, axis=axis)
                    else:
                        self.sangaboard.move_rel(displacement, axis=axis)
                        
                    self.log_message(f"Movement completed for {axis.upper()} axis")
                    # Update position after movement
                    self.root.after(100, self.update_position)
                except Exception as e:
                    self.log_message(f"Error moving {axis.upper()} axis: {str(e)}")
                    
            threading.Thread(target=move, daemon=True).start()
            
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numeric values")
            
    def move_multi_axis(self):
        """Move multiple axes simultaneously"""
        if not self.check_connection():
            return
            
        try:
            x_steps = int(self.multi_x_var.get())
            y_steps = int(self.multi_y_var.get())
            z_steps = int(self.multi_z_var.get())
            
            displacement = [x_steps, y_steps, z_steps]
            
            # Check if any movement is requested
            if all(step == 0 for step in displacement):
                self.log_message("No movement - all displacements are 0")
                return
            
            mode = self.move_mode_var.get()
            self.log_message(f"Moving all axes: X={x_steps}, Y={y_steps}, Z={z_steps} in {mode} mode")
            
            # Run in separate thread to prevent GUI freezing
            def move():
                try:
                    if mode == "pulses":
                        # Note: multi-axis pulse movement isn't directly supported by the library
                        # so we'll use regular movement and log a warning
                        self.log_message("Warning: Multi-axis pulse movement not supported, using normal movement")
                        self.sangaboard.move_rel(displacement)
                    else:
                        self.sangaboard.move_rel(displacement)
                        
                    self.log_message("Multi-axis movement completed")
                    # Update position after movement
                    self.root.after(100, self.update_position)
                except Exception as e:
                    self.log_message(f"Error in multi-axis movement: {str(e)}")
                    
            threading.Thread(target=move, daemon=True).start()
            
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numeric values")
            
    def update_position(self):
        """Update the current position display"""
        if not self.check_connection():
            return
            
        try:
            position = self.sangaboard.position
            self.position_var.set(f"X: {position[0]}, Y: {position[1]}, Z: {position[2]}")
            
        except Exception as e:
            self.log_message(f"Error reading position: {str(e)}")
            
    def zero_position(self):
        """Set current position to zero"""
        if not self.check_connection():
            return
            
        try:
            self.sangaboard.zero_position()
            self.log_message("Position zeroed")
            self.update_position()
            
        except Exception as e:
            self.log_message(f"Error zeroing position: {str(e)}")
            
    def on_position_action_selected(self, event):
        """Handle position action dropdown selection"""
        action = self.position_menu_var.get()
        
        if action == "Set Position as Zero":
            self.zero_position()
            
        # Reset dropdown to default
        self.position_menu_var.set("Position Actions")
        
    def move_to_zero(self):
        """Move all axes to zero position"""
        if not self.check_connection():
            return
            
        try:
            current_position = self.sangaboard.position
            self.log_message(f"Moving to zero from current position: X={current_position[0]}, Y={current_position[1]}, Z={current_position[2]}")
            
            # Run in separate thread to prevent GUI freezing
            def move():
                try:
                    self.sangaboard.move_abs([0, 0, 0])
                    self.log_message("Moved to zero position")
                    # Update position after movement
                    self.root.after(100, self.update_position)
                except Exception as e:
                    self.log_message(f"Error moving to zero: {str(e)}")
                    
            threading.Thread(target=move, daemon=True).start()
            
        except Exception as e:
            self.log_message(f"Error getting current position: {str(e)}")
            
    def move_to_absolute(self):
        """Move to specified absolute position"""
        if not self.check_connection():
            return
            
        try:
            # Get absolute position values
            x_pos = int(self.abs_position_vars['x'].get())
            y_pos = int(self.abs_position_vars['y'].get())
            z_pos = int(self.abs_position_vars['z'].get())
            
            target_position = [x_pos, y_pos, z_pos]
            
            try:
                current_position = self.sangaboard.position
                self.log_message(f"Moving to absolute position: X={x_pos}, Y={y_pos}, Z={z_pos}")
                self.log_message(f"Current position: X={current_position[0]}, Y={current_position[1]}, Z={current_position[2]}")
            except:
                self.log_message(f"Moving to absolute position: X={x_pos}, Y={y_pos}, Z={z_pos}")
            
            # Run in separate thread to prevent GUI freezing
            def move():
                try:
                    self.sangaboard.move_abs(target_position)
                    self.log_message("Absolute movement completed")
                    # Update position after movement
                    self.root.after(100, self.update_position)
                except Exception as e:
                    self.log_message(f"Error in absolute movement: {str(e)}")
                    
            threading.Thread(target=move, daemon=True).start()
            
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numeric values for all axes")
        except Exception as e:
            self.log_message(f"Error preparing absolute movement: {str(e)}")
            
    def set_step_time(self):
        """Set the step time"""
        if not self.check_connection():
            return
            
        try:
            step_time = int(self.step_time_var.get())
            self.sangaboard.step_time = step_time
            self.log_message(f"Step time set to {step_time} μs")
            
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid numeric value")
        except Exception as e:
            self.log_message(f"Error setting step time: {str(e)}")
            
    def set_ramp_time(self):
        """Set the ramp time"""
        if not self.check_connection():
            return
            
        try:
            ramp_time = int(self.ramp_time_var.get())
            # Always use manual command for ramp time
            response = self.sangaboard.query(f"ramp_time {ramp_time}")
            self.log_message(f"Ramp_time set command response: '{response}'")
            self.log_message(f"Ramp time set to {ramp_time} μs")
            
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid numeric value")
        except Exception as e:
            self.log_message(f"Error setting ramp time: {str(e)}")
            
    def get_current_settings(self):
        """Get and display current motor settings"""
        if not self.check_connection():
            return
            
        try:
            # Try to get step time
            try:
                step_time = self.sangaboard.step_time
                self.step_time_var.set(str(step_time))
                self.log_message(f"Step time: {step_time} μs")
            except Exception as e:
                self.log_message(f"Error reading step time: {str(e)}")
                
            # Always use manual query for ramp time
            try:
                response = self.sangaboard.query("ramp_time?")
                self.log_message(f"Ramp_time query response: '{response}'")
                # Try to extract number from response
                import re
                match = re.search(r'(\d+)', response)
                if match:
                    ramp_time = int(match.group(1))
                    self.ramp_time_var.set(str(ramp_time))
                    self.log_message(f"Ramp time: {ramp_time} μs")
                else:
                    self.log_message("Could not extract ramp time value from response")
            except Exception as e:
                self.log_message(f"Error reading ramp time: {str(e)}")
            
        except Exception as e:
            self.log_message(f"General error reading settings: {str(e)}")
            
    def release_motors(self):
        """Release motor coils"""
        if not self.check_connection():
            return
            
        try:
            self.sangaboard.release_motors()
            self.log_message("Motors released")
            
        except Exception as e:
            self.log_message(f"Error releasing motors: {str(e)}")
            
    def run_self_test(self):
        """Run a self-test that moves each motor in turn for 5 steps with pulses"""
        if not self.check_connection():
            return
            
        # Ask for confirmation
        result = messagebox.askyesno("Self Test", 
                                   "This will move each motor (X, Y, Z) for 5 steps forward then back.\n"
                                   "Make sure the motors can move safely.\n\n"
                                   "Continue with self-test?")
        if not result:
            return
            
        self.log_message("Starting self-test...")
        
        # Run in separate thread to prevent GUI freezing
        def test():
            try:
                axes = ['x', 'y', 'z']
                test_steps = 5
                pulse_interval = 1
                
                for axis in axes:
                    # Move forward
                    self.log_message(f"Testing {axis.upper()} axis: +{test_steps} steps with pulses")
                    self.sangaboard.move_rel_with_pulses(test_steps, pulse_interval, axis=axis)
                    
                    # Small delay between movements
                    time.sleep(0.5)
                    
                    # Move back to original position
                    self.log_message(f"Testing {axis.upper()} axis: -{test_steps} steps with pulses")
                    self.sangaboard.move_rel_with_pulses(-test_steps, pulse_interval, axis=axis)
                    
                    # Delay before next axis
                    time.sleep(0.5)
                
                self.log_message("Self-test completed successfully!")
                
                # Update position after test
                self.root.after(100, self.update_position)
                
            except Exception as e:
                self.log_message(f"Self-test failed: {str(e)}")
                
        threading.Thread(target=test, daemon=True).start()
    
    def camera_move_relative(self, axis, direction):
        """Move the stage by a relative amount while camera is running"""
        if not self.check_connection():
            return
            
        try:
            # Get step size for the specific axis
            if axis == 'x':
                step_size = int(self.camera_step_x_var.get())
            elif axis == 'y':
                step_size = int(self.camera_step_y_var.get())
            elif axis == 'z':
                step_size = int(self.camera_step_z_var.get())
            else:
                self.log_message(f"Invalid axis: {axis}")
                return
                
            # Calculate movement amount (direction is +1 or -1)
            movement = step_size * direction
            
            # Get pulse setting
            use_pulses = self.camera_pulse_var.get()
            
            # Log the movement
            axis_name = axis.upper()
            direction_str = "+" if direction > 0 else ""
            pulse_str = " with pulses" if use_pulses else ""
            self.log_message(f"Camera tab: Moving {axis_name}{direction_str}{movement}{pulse_str}")
            
            # Perform movement in a separate thread to avoid blocking camera
            def move():
                try:
                    if use_pulses:
                        # Move with pulses
                        if axis == 'x':
                            self.sangaboard.move_rel([movement, 0, 0], backlash=True)
                        elif axis == 'y':
                            self.sangaboard.move_rel([0, movement, 0], backlash=True)
                        elif axis == 'z':
                            self.sangaboard.move_rel([0, 0, movement], backlash=True)
                    else:
                        # Move without pulses
                        if axis == 'x':
                            self.sangaboard.move_rel([movement, 0, 0])
                        elif axis == 'y':
                            self.sangaboard.move_rel([0, movement, 0])
                        elif axis == 'z':
                            self.sangaboard.move_rel([0, 0, movement])
                    
                    self.log_message(f"Camera tab: {axis_name} movement completed")
                    # Update position after movement
                    self.root.after(100, self.update_position)
                    
                except Exception as e:
                    self.log_message(f"Error in camera tab movement: {str(e)}")
                    
            threading.Thread(target=move, daemon=True).start()
            
        except ValueError:
            messagebox.showerror("Error", f"Please enter a valid numeric value for {axis.upper()} step size")
        except Exception as e:
            self.log_message(f"Error preparing camera tab movement: {str(e)}")
        
    # Camera-related methods
    def toggle_camera_connection(self):
        """Connect or disconnect from the camera"""
        if not THORLABS_SDK_AVAILABLE:
            messagebox.showerror("Error", "Thorlabs SDK not available. Please install required dependencies.")
            return
            
        if not self.camera_running:
            # Ensure clean state before attempting connection
            self.cleanup_camera()
            
            try:
                self.log_message("Initializing camera...")
                self.camera_sdk = TLCameraSDK()
                camera_list = self.camera_sdk.discover_available_cameras()
                
                if len(camera_list) == 0:
                    messagebox.showerror("Error", "No Thorlabs cameras found")
                    # Clean up SDK if no cameras found
                    if self.camera_sdk:
                        self.camera_sdk.dispose()
                        self.camera_sdk = None
                    return
                
                # Use the first available camera
                self.camera = self.camera_sdk.open_camera(camera_list[0])
                
                # Get camera information
                try:
                    # Try different ways to get camera information
                    camera_name = "Unknown"
                    camera_serial = "Unknown"
                    camera_make = "Unknown"
                    
                    # Method 1: Try direct properties
                    if hasattr(self.camera, 'name'):
                        camera_name = str(self.camera.name)
                    elif hasattr(self.camera, 'model'):
                        camera_name = str(self.camera.model)
                    elif hasattr(self.camera, '_camera_name'):
                        camera_name = str(self.camera._camera_name)
                    
                    if hasattr(self.camera, 'serial_number'):
                        camera_serial = str(self.camera.serial_number)
                    elif hasattr(self.camera, '_serial_number'):
                        camera_serial = str(self.camera._serial_number)
                    
                    # Method 2: Try to get from camera list info
                    try:
                        camera_info = camera_list[0]  # The camera we just opened
                        if hasattr(camera_info, 'name'):
                            camera_name = str(camera_info.name)
                        if hasattr(camera_info, 'serial_number'):
                            camera_serial = str(camera_info.serial_number)
                        if hasattr(camera_info, 'model'):
                            camera_name = str(camera_info.model)
                    except:
                        pass
                    
                    # Extract manufacturer from camera name
                    if camera_name != "Unknown":
                        name_lower = camera_name.lower()
                        if "thorlabs" in name_lower:
                            camera_make = "Thorlabs"
                        elif "zelux" in name_lower or "kiralux" in name_lower:
                            camera_make = "Thorlabs"
                        else:
                            # Try to extract first word as manufacturer
                            name_parts = camera_name.split()
                            if name_parts:
                                camera_make = name_parts[0]
                    
                    # Store camera info
                    self.camera_make = camera_make
                    self.camera_serial = camera_serial
                    
                    # Update GUI
                    if hasattr(self, 'camera_make_var'):
                        self.camera_make_var.set(camera_make)
                    if hasattr(self, 'camera_serial_var'):
                        self.camera_serial_var.set(camera_serial)
                    
                    # Log camera information
                    if camera_name != "Unknown":
                        self.log_message(f"Camera: {camera_make} - {camera_name}")
                    else:
                        self.log_message(f"Camera: {camera_make}")
                    self.log_message(f"Serial Number: {camera_serial}")
                    
                except Exception as e:
                    self.log_message(f"Could not retrieve camera information: {str(e)}")
                    self.camera_make = "Unknown"
                    self.camera_serial = "Unknown"
                    if hasattr(self, 'camera_make_var'):
                        self.camera_make_var.set("Unknown")
                    if hasattr(self, 'camera_serial_var'):
                        self.camera_serial_var.set("Unknown")
                
                self.camera.exposure_time_us = 10000  # 10ms default
                self.camera.frames_per_trigger_zero_for_unlimited = 0
                self.camera.arm(2)  # Arm for continuous acquisition
                self.camera.issue_software_trigger()
                
                self.camera_running = True
                self.connect_camera_btn.config(text="Disconnect Camera")
                self.camera_status_label.config(text="Connected", foreground="green")
                
                # Start camera thread
                self.camera_thread = threading.Thread(target=self.camera_capture_loop, daemon=True)
                self.camera_thread.start()
                
                self.log_message("Camera connected successfully")
                
            except Exception as e:
                self.log_message(f"Camera connection failed: {str(e)}")
                messagebox.showerror("Camera Error", f"Failed to connect camera:\n{str(e)}")
                # Ensure thorough cleanup on any failure
                self.cleanup_camera()
                # Reset button state
                self.connect_camera_btn.config(text="Connect Camera")
                self.camera_status_label.config(text="Disconnected", foreground="red")
        else:
            self.disconnect_camera()
            
    def disconnect_camera(self):
        """Disconnect the camera"""
        try:
            self.camera_running = False
            if self.camera_thread:
                self.camera_thread.join(timeout=2)
            
            self.cleanup_camera()
            
            self.connect_camera_btn.config(text="Connect Camera")
            self.camera_status_label.config(text="Disconnected", foreground="red")
            self.camera_display.config(image="", text="Camera Disconnected")
            
            self.log_message("Camera disconnected")
            
        except Exception as e:
            self.log_message(f"Error disconnecting camera: {str(e)}")
    
    def on_color_format_change(self):
        """Handle color format selection change"""
        # Reset the logging flag so the new format is logged
        self.color_format_logged = False
        self.log_message(f"Color format changed to: {self.color_format_var.get()}")
    
    def on_bayer_pattern_change(self):
        """Handle Bayer pattern selection change"""
        # Reset the logging flags so the new pattern is logged
        self.bayer_logged = False
        pattern = self.bayer_pattern_var.get()
        
        if pattern == "auto":
            self.log_message("Bayer pattern set to Auto-detect")
        elif pattern == "none":
            self.is_bayer_camera = False
            self.log_message("Bayer demosaicing disabled")
        else:
            self.is_bayer_camera = True
            self.bayer_pattern = int(pattern)
            pattern_names = {0: "BGGR", 1: "GBRG", 2: "RGGB", 3: "GRBG"}
            self.log_message(f"Bayer pattern manually set to: {pattern_names.get(int(pattern), pattern)}")
            
    def cleanup_camera(self):
        """Clean up camera resources"""
        try:
            # Stop camera thread first
            if hasattr(self, 'camera_running'):
                self.camera_running = False
            
            # Wait for thread to finish
            if hasattr(self, 'camera_thread') and self.camera_thread and self.camera_thread.is_alive():
                self.camera_thread.join(timeout=1)
            
            # Clean up camera
            if hasattr(self, 'camera') and self.camera:
                try:
                    self.camera.disarm()
                except:
                    pass  # Ignore errors if already disarmed
                try:
                    self.camera.dispose()
                except:
                    pass  # Ignore errors if already disposed
                self.camera = None
                
            # Clean up SDK
            if hasattr(self, 'camera_sdk') and self.camera_sdk:
                try:
                    self.camera_sdk.dispose()
                except:
                    pass  # Ignore errors if already disposed
                self.camera_sdk = None
                
            # Reset thread reference
            if hasattr(self, 'camera_thread'):
                self.camera_thread = None
                
            # Reset image data
            self.current_display_image = None
            self.image_scale_factor = 1.0
            self.first_frame_logged = False
            self.color_format_logged = False
            
            # Reset displays
            if hasattr(self, 'camera_make_var'):
                self.camera_make_var.set("N/A")
            if hasattr(self, 'camera_serial_var'):
                self.camera_serial_var.set("N/A")
            if hasattr(self, 'frame_size_var'):
                self.frame_size_var.set("N/A")
            if hasattr(self, 'cursor_pos_var'):
                self.cursor_pos_var.set("x: -, y: -")
            if hasattr(self, 'rgb_values_var'):
                self.rgb_values_var.set("N/A")
                
        except Exception as e:
            self.log_message(f"Error cleaning up camera: {str(e)}")
            
    def camera_capture_loop(self):
        """Main camera capture loop running in separate thread"""
        while self.camera_running:
            try:
                frame = self.camera.get_pending_frame_or_null()
                if frame is not None:
                    # Convert frame to numpy array
                    image_array = np.copy(frame.image_buffer)
                    image_array = image_array.reshape(frame.image_buffer.shape)
                    
                    # Log camera format information on first frame
                    if not getattr(self, 'first_frame_logged', False):
                        self.first_frame_logged = True
                        shape_str = f"{image_array.shape}"
                        dtype_str = str(image_array.dtype)
                        
                        # Get additional camera properties for color format debugging
                        try:
                            cfa_phase = None
                            sensor_type = None
                            bit_depth = None
                            
                            if hasattr(self.camera, 'color_filter_array_phase'):
                                cfa_phase = self.camera.color_filter_array_phase
                                self.log_message(f"Color Filter Array Phase: {cfa_phase}")
                            if hasattr(self.camera, 'sensor_type'):
                                sensor_type = self.camera.sensor_type
                                self.log_message(f"Sensor Type: {sensor_type}")
                            if hasattr(self.camera, 'bit_depth'):
                                bit_depth = self.camera.bit_depth
                                self.log_message(f"Bit Depth: {bit_depth}")
                            
                            # Check if this is a Bayer pattern camera
                            self.is_bayer_camera = (cfa_phase is not None and cfa_phase != 0)
                            if self.is_bayer_camera:
                                self.log_message(f"BAYER CAMERA DETECTED - This requires demosaicing for proper color!")
                                self.bayer_pattern = cfa_phase
                            else:
                                self.is_bayer_camera = False
                                
                        except Exception as debug_e:
                            self.log_message(f"Camera property debug failed: {debug_e}")
                            self.is_bayer_camera = False
                        
                        if len(image_array.shape) == 3:
                            format_info = f"Color camera detected: {shape_str}, {dtype_str}, {image_array.shape[2]} channels"
                            # Sample some pixel values to check color format
                            if image_array.shape[0] > 10 and image_array.shape[1] > 10:
                                sample_pixel = image_array[10, 10]
                                self.log_message(f"Sample pixel (10,10): {sample_pixel}")
                        else:
                            format_info = f"Grayscale camera detected: {shape_str}, {dtype_str}"
                        
                        self.log_message(format_info)
                        
                        # Auto-set display mode based on detected format
                        if hasattr(self, 'display_mode_var'):
                            if len(image_array.shape) == 3 and image_array.shape[2] >= 3:
                                self.display_mode_var.set("color")
                                self.log_message("Auto-set display mode to Color")
                            else:
                                self.display_mode_var.set("grayscale")
                                self.log_message("Auto-set display mode to Grayscale")
                    
                    # Update frame size information
                    frame_height, frame_width = image_array.shape[:2]
                    self.root.after(0, self.update_frame_size, frame_width, frame_height)
                    
                    # Calculate focus measure
                    if CV2_AVAILABLE:
                        self.focus_measure = self.calculate_focus_measure(image_array)
                        self.root.after(0, self.update_focus_display)
                    
                    # Convert for display
                    if PIL_AVAILABLE:
                        display_image, rgb_image, scale_factor = self.convert_frame_for_display(image_array)
                        if display_image:
                            self.current_display_image = rgb_image
                            self.image_scale_factor = scale_factor
                            self.root.after(0, self.update_camera_display, display_image)
                    
                    self.current_frame = image_array
                    
                time.sleep(0.033)  # ~30 FPS
                
            except Exception as e:
                if self.camera_running:  # Only log if we're supposed to be running
                    self.log_message(f"Camera capture error: {str(e)}")
                break
                
    def calculate_focus_measure(self, image):
        """Calculate focus measure using variance of Laplacian"""
        try:
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Calculate Laplacian variance
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            return laplacian.var()
            
        except Exception as e:
            self.log_message(f"Focus calculation error: {str(e)}")
            return 0.0
            
    def convert_frame_for_display(self, image_array):
        """Convert camera frame to format suitable for tkinter display"""
        try:
            # Handle different bit depths more carefully
            if image_array.dtype == np.uint16:
                # For 16-bit images, use percentile-based normalization to avoid extreme stretching
                p_low, p_high = np.percentile(image_array, (1, 99))
                if p_high > p_low:
                    image_normalized = np.clip((image_array - p_low) / (p_high - p_low) * 255, 0, 255).astype(np.uint8)
                else:
                    # Fallback for uniform images
                    image_normalized = (image_array >> 8).astype(np.uint8)  # Simple bit shift
            elif image_array.dtype != np.uint8:
                # For other data types, use simple range normalization
                img_min = image_array.min()
                img_max = image_array.max()
                img_range = img_max - img_min
                
                if img_range == 0:
                    image_normalized = np.full_like(image_array, 128, dtype=np.uint8)
                else:
                    image_normalized = ((image_array - img_min) / img_range * 255).astype(np.uint8)
            else:
                image_normalized = image_array
            
            # Handle Bayer pattern demosaicing for proper color reconstruction
            bayer_setting = self.bayer_pattern_var.get() if hasattr(self, 'bayer_pattern_var') else "auto"
            
            if (bayer_setting != "none" and len(image_normalized.shape) == 2):
                try:
                    # Determine if we should apply Bayer demosaicing
                    should_apply_bayer = False
                    bayer_pattern = 0  # Default pattern
                    
                    if bayer_setting == "auto":
                        # Use camera-detected Bayer pattern
                        should_apply_bayer = hasattr(self, 'is_bayer_camera') and self.is_bayer_camera
                        if should_apply_bayer:
                            bayer_pattern = getattr(self, 'bayer_pattern', 0)
                    else:
                        # Manual Bayer pattern selection
                        should_apply_bayer = True
                        bayer_pattern = int(bayer_setting)
                    
                    if should_apply_bayer:
                        # Map Bayer pattern to OpenCV constants
                        if bayer_pattern == 0:
                            cv_pattern = cv2.COLOR_BayerBG2RGB  # BGGR
                        elif bayer_pattern == 1:
                            cv_pattern = cv2.COLOR_BayerGB2RGB  # GBRG  
                        elif bayer_pattern == 2:
                            cv_pattern = cv2.COLOR_BayerRG2RGB  # RGGB
                        elif bayer_pattern == 3:
                            cv_pattern = cv2.COLOR_BayerGR2RGB  # GRBG
                        else:
                            cv_pattern = cv2.COLOR_BayerBG2RGB  # Default fallback
                        
                        # Apply demosaicing to convert Bayer pattern to RGB
                        image_normalized = cv2.cvtColor(image_normalized, cv_pattern)
                        
                        if not getattr(self, 'bayer_logged', False):
                            pattern_names = {0: "BGGR", 1: "GBRG", 2: "RGGB", 3: "GRBG"}
                            mode = "Auto-detected" if bayer_setting == "auto" else "Manual"
                            pattern_name = pattern_names.get(bayer_pattern, f"Pattern {bayer_pattern}")
                            self.log_message(f"{mode} Bayer demosaicing applied ({pattern_name}) - now proper sRGB!")
                            self.bayer_logged = True
                            
                except Exception as bayer_e:
                    self.log_message(f"Bayer demosaicing failed: {bayer_e}")
                    # Fallback: convert grayscale to RGB
                    image_normalized = cv2.cvtColor(image_normalized, cv2.COLOR_GRAY2RGB)
            
            # Determine if this is truly a color image or grayscale and handle display mode
            is_color_data = len(image_normalized.shape) == 3 and image_normalized.shape[2] >= 3
            display_mode = self.display_mode_var.get() if hasattr(self, 'display_mode_var') else "auto"
            color_format = self.color_format_var.get() if hasattr(self, 'color_format_var') else "auto"
            
            if display_mode == "color" or (display_mode == "auto" and is_color_data):
                # Display as color
                if is_color_data:
                    # Already color data - handle different color formats
                    if image_normalized.shape[2] == 3:
                        # 3-channel image - apply color format conversion based on setting
                        image_rgb = image_normalized.copy()
                        
                        if color_format == "bgr":
                            # Force BGR to RGB conversion
                            image_rgb = cv2.cvtColor(image_rgb, cv2.COLOR_BGR2RGB)
                            if not getattr(self, 'color_format_logged', False):
                                self.log_message("Manual BGR->RGB conversion applied")
                                self.color_format_logged = True
                                
                        elif color_format == "rgb":
                            # Use as RGB directly
                            if not getattr(self, 'color_format_logged', False):
                                self.log_message("Using direct RGB format")
                                self.color_format_logged = True
                                
                        else:  # auto mode
                            # Auto-detect BGR format using statistical analysis
                            try:
                                # Sample a region to check channel characteristics
                                h, w = image_rgb.shape[:2]
                                sample_h, sample_w = min(100, h//2), min(100, w//2)
                                sample_region = image_rgb[sample_h:sample_h+50, sample_w:sample_w+50]
                                
                                if sample_region.size > 0:
                                    # Calculate variance in each channel
                                    r_var = np.var(sample_region[:, :, 0])
                                    g_var = np.var(sample_region[:, :, 1]) 
                                    b_var = np.var(sample_region[:, :, 2])
                                    
                                    # If blue channel has significantly more variance than red,
                                    # this might be BGR format where blue is actually red data
                                    if b_var > r_var * 1.5:
                                        image_rgb = cv2.cvtColor(image_rgb, cv2.COLOR_BGR2RGB)
                                        if not getattr(self, 'color_format_logged', False):
                                            self.log_message("Auto-detected BGR format - converting to RGB")
                                            self.color_format_logged = True
                                    else:
                                        if not getattr(self, 'color_format_logged', False):
                                            self.log_message("Auto-detected RGB format - using directly")
                                            self.color_format_logged = True
                                
                            except Exception as color_debug_e:
                                # If analysis fails, try BGR conversion for Thorlabs cameras
                                image_rgb = cv2.cvtColor(image_rgb, cv2.COLOR_BGR2RGB)
                                if not getattr(self, 'color_format_logged', False):
                                    self.log_message("Auto-detection failed - applying BGR->RGB for Thorlabs camera")
                                    self.color_format_logged = True
                            
                    elif image_normalized.shape[2] == 4:
                        # RGBA format - drop alpha channel and convert BGR to RGB if needed
                        image_rgb = image_normalized[:, :, :3]
                        # Apply BGR to RGB conversion for 4-channel images too
                        image_rgb = cv2.cvtColor(image_rgb, cv2.COLOR_BGR2RGB)
                    else:
                        # Take first 3 channels
                        image_rgb = image_normalized[:, :, :3]
                        
                else:
                    # Grayscale data but user wants color display
                    image_rgb = cv2.cvtColor(image_normalized, cv2.COLOR_GRAY2RGB)
                    
            elif display_mode == "grayscale":
                # Force grayscale display
                if is_color_data:
                    # Convert color to grayscale first
                    gray = cv2.cvtColor(image_normalized, cv2.COLOR_RGB2GRAY)
                    image_rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
                else:
                    # Already grayscale
                    image_rgb = cv2.cvtColor(image_normalized, cv2.COLOR_GRAY2RGB)
                    
            else:
                # Auto mode - preserve original format
                if is_color_data:
                    image_rgb = image_normalized if image_normalized.shape[2] == 3 else image_normalized[:, :, :3]
                else:
                    image_rgb = cv2.cvtColor(image_normalized, cv2.COLOR_GRAY2RGB)
            
            # Store original RGB image before resizing
            original_rgb = image_rgb.copy()
            
            # Resize for display with better interpolation
            height, width = image_rgb.shape[:2]
            max_width, max_height = 400, 300
            scale_factor = 1.0
            
            if width > max_width or height > max_height:
                scale_factor = min(max_width/width, max_height/height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                # Use INTER_AREA for downsampling to reduce aliasing
                image_rgb = cv2.resize(image_rgb, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            # Convert to PIL Image and then to PhotoImage
            pil_image = Image.fromarray(image_rgb)
            photo_image = ImageTk.PhotoImage(pil_image)
            
            # Return photo image, original RGB for pixel readout, and scale factor
            return photo_image, original_rgb, scale_factor
            
        except Exception as e:
            self.log_message(f"Image conversion error: {str(e)}")
            return None, None, 1.0
            
    def update_camera_display(self, photo_image):
        """Update the camera display in the GUI"""
        if photo_image and hasattr(self, 'camera_display'):
            self.camera_display.config(image=photo_image, text="")
            self.camera_display.image = photo_image  # Keep a reference
            
    def update_focus_display(self):
        """Update the focus measure display"""
        self.focus_measure_var.set(f"{self.focus_measure:.2f}")
        
    def set_exposure(self):
        """Set camera exposure time"""
        if not self.camera:
            messagebox.showerror("Error", "No camera connected")
            return
            
        try:
            exposure_ms = float(self.exposure_var.get())
            exposure_us = int(exposure_ms * 1000)  # Convert to microseconds
            self.camera.exposure_time_us = exposure_us
            self.log_message(f"Exposure set to {exposure_ms} ms")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid exposure time")
        except Exception as e:
            self.log_message(f"Error setting exposure: {str(e)}")
            
    def set_gain(self):
        """Set camera gain"""
        if not self.camera:
            messagebox.showerror("Error", "No camera connected")
            return
            
        try:
            gain = float(self.gain_var.get())
            # Note: Gain setting depends on camera model
            # This is a placeholder - actual implementation depends on camera capabilities
            self.log_message(f"Gain setting to {gain} (implementation depends on camera model)")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid gain value")
        except Exception as e:
            self.log_message(f"Error setting gain: {str(e)}")
            
    def update_frame_size(self, width, height):
        """Update the frame size display"""
        self.frame_size_var.set(f"{width} x {height}")
        
    def update_focus_display(self):
        """Update the focus measure display"""
        self.focus_measure_var.set(f"{self.focus_measure:.2f}")
        
    def on_mouse_motion(self, event):
        """Handle mouse motion over camera display for RGB readout"""
        try:
            if self.current_display_image is not None and hasattr(self, 'image_scale_factor'):
                # Convert display coordinates to original image coordinates
                original_x = int(event.x / self.image_scale_factor)
                original_y = int(event.y / self.image_scale_factor)
                
                # Check if coordinates are within image bounds
                height, width = self.current_display_image.shape[:2]
                if 0 <= original_x < width and 0 <= original_y < height:
                    # Get RGB values at this pixel
                    rgb_values = self.current_display_image[original_y, original_x]
                    r, g, b = rgb_values[0], rgb_values[1], rgb_values[2]
                    
                    # Update display
                    self.cursor_pos_var.set(f"x: {original_x}, y: {original_y}")
                    
                    # Check if this is effectively a grayscale image (R=G=B) or true color
                    if r == g == b:
                        # Display as grayscale value
                        self.rgb_values_var.set(f"Gray: {r}")
                    else:
                        # Display as true RGB values
                        self.rgb_values_var.set(f"R: {r}, G: {g}, B: {b}")
                else:
                    self.cursor_pos_var.set("x: -, y: -")
                    self.rgb_values_var.set("N/A")
        except Exception as e:
            # Silently handle errors to avoid spamming the log
            pass
            
    def on_mouse_leave(self, event):
        """Handle mouse leaving camera display"""
        self.cursor_pos_var.set("x: -, y: -")
        self.rgb_values_var.set("N/A")


def main():
    root = tk.Tk()
    app = SangaboardGUI(root)
    
    # Handle window closing
    def on_closing():
        # Cleanup Sangaboard connection
        if app.connected and app.sangaboard:
            try:
                app.sangaboard.close()
            except:
                pass
        
        # Cleanup camera connection
        if app.camera_running:
            try:
                app.disconnect_camera()
            except:
                pass
                
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
