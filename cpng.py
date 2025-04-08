#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Color Picker Tool

Description: A tool for capturing and analyzing colors on the screen
             with support for multiple color models and color palettes.

Author: Robert Tulke
E-Mail: rt@debian.sh
Version: 2.1
License: GPLv3
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import math
import webbrowser
import time
import platform
import os
import sys
import tempfile
import subprocess
import re
from io import BytesIO
import base64

# Global Debug-Settings
DEBUG = False

def debug_print(message):
    """Outputs debug messages when DEBUG is activated."""
    if DEBUG:
        print(f"DEBUG: {message}")

def get_platform_specific_cursor_color():
    """Platform-specific implementation for capturing the color under the mouse pointer."""
    system = platform.system()
    
    try:
        if system == 'Windows':
            return get_color_windows()
        elif system == 'Darwin':  # macOS
            return get_color_macos()
        elif system == 'Linux':
            return get_color_linux()
        else:
            debug_print(f"Unknown Operating System: {system}")
            return get_color_fallback()
    except Exception as e:
        debug_print(f"Error in color detection for {system}: {str(e)}")
        return get_color_fallback()

def get_color_windows():
    """Determines the color under the mouse pointer in Windows."""
    try:
        import ctypes
        from ctypes import windll, Structure, c_long
        
        class POINT(Structure):
            _fields_ = [("x", c_long), ("y", c_long)]
            
        hdc = windll.user32.GetDC(0)
        pt = POINT()
        windll.user32.GetCursorPos(ctypes.byref(pt))
        pixel = windll.gdi32.GetPixel(hdc, pt.x, pt.y)
        windll.user32.ReleaseDC(0, hdc)
        r = pixel & 0xFF
        g = (pixel >> 8) & 0xFF
        b = (pixel >> 16) & 0xFF
        return r, g, b
    except Exception as e:
        debug_print(f"Windows-specific color detection failed: {e}")
        raise

def get_color_macos():
    """Determines the color under the mouse pointer on macOS."""
    try:
        # Temporary screenshot file
        tempfile_path = os.path.join(tempfile.gettempdir(), 'colorpicker_temp.png')
        
        # Correctly determining the mouse position with AppleScript
        mouse_pos_cmd = """
        osascript -e 'tell application "System Events"
            set mousePosition to current location of mouse
            return mousePosition
        end tell'
        """
        try:
            result = subprocess.run(mouse_pos_cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                # AppleScript gibt "x, y" zurück
                coords = result.stdout.strip().split(', ')
                if len(coords) == 2:
                    x, y = int(coords[0]), int(coords[1])
                    debug_print(f"mouse position: {x}, {y}")
                else:
                    debug_print(f"Unexpected format of the mouse position: {result.stdout}")
                    x, y = 800, 600  # Fallback
            else:
                debug_print(f"Could not determine mouse position - error: {result.stderr}")
                x, y = 800, 600  # Fallback to center screen
        except Exception as e:
            debug_print(f"Error determining the mouse position: {e}")
            x, y = 800, 600  # Fallback
        
        # Take a screenshot with screencapture (3x3 pixels at the mouse position)
        # -x  suppresses sound, -R defines region (x,y,width,height)
        capture_cmd = ['screencapture', '-x', '-R', f"{x-1},{y-1},3,3", '-t', 'png', tempfile_path]
        result = subprocess.run(capture_cmd, capture_output=True)
        
        if result.returncode != 0 or not os.path.exists(tempfile_path) or os.path.getsize(tempfile_path) == 0:
            debug_print(f"Screenshot failed - error: {result.stderr}")
            return get_color_fallback()
        
        # Option 1: Use 'sips' for color analysis
        sips_cmd = ['sips', '-g', 'pixelColor', tempfile_path]
        try:
            result = subprocess.run(sips_cmd, capture_output=True, text=True)
            pixel_info = result.stdout
            
            # Search for RGB values in the output text
            rgb_match = re.search(r'pixelcolor.*?(\d+).*?(\d+).*?(\d+)', pixel_info, re.DOTALL | re.IGNORECASE)
            if rgb_match:
                r, g, b = map(int, rgb_match.groups())
                debug_print(f"RGB aus sips: {r}, {g}, {b}")
                os.remove(tempfile_path)  # Aufräumen
                return r, g, b
        except Exception as e:
            debug_print(f"Error in sips analysis: {e}")
        
        # Alternative 2: Use Python image processing if available
        try:
            from PIL import Image
            img = Image.open(tempfile_path)
            # Center pixel of the 3x3 screenshot
            r, g, b = img.getpixel((1, 1))[:3]
            debug_print(f"RGB aus PIL: {r}, {g}, {b}")
            img.close()
            os.remove(tempfile_path)  # clean up
            return r, g, b
        except ImportError:
            debug_print("PIL not installed")
        except Exception as e:
            debug_print(f"Error in PIL analysis: {e}")
        
        # cleaning
        try:
            if os.path.exists(tempfile_path):
                os.remove(tempfile_path)
        except Exception as e:
            debug_print(f"Could not delete temporary file: {e}")
        
        debug_print("All macOS color extraction methods failed")
        return get_color_fallback()
    except Exception as e:
        debug_print(f"macOS-specific color detection failed: {e}")
        return get_color_fallback()

def get_color_linux():
    """Determines the color under the mouse pointer on Linux."""
    try:
        # Tests with xdotool and import
        debug_print("Try Linux color capture with xdotool and imagemagick")
        
        # Get mouse position
        try:
            mouse_pos = subprocess.check_output(['xdotool', 'getmouselocation']).decode()
            x_match = re.search(r'x:(\d+)', mouse_pos)
            y_match = re.search(r'y:(\d+)', mouse_pos)
            
            if x_match and y_match:
                x = int(x_match.group(1))
                y = int(y_match.group(1))
                debug_print(f"mouse position: {x}, {y}")
            else:
                debug_print("Could not determine mouse position - using fallback")
                return get_color_fallback()
        except Exception as e:
            debug_print(f"Error determining the mouse position: {e}")
            return get_color_fallback()
        
        # Temporary screenshot file
        temp_file = os.path.join(tempfile.gettempdir(), 'colorpicker_temp.png')
        
        # Take a screenshot with ImageMagick 'import'
        try:
            subprocess.call(['import', '-window', 'root', '-crop', f'1x1+{x}+{y}', '+repage', temp_file])
            
            # Extract color information using 'convert'
            color_info = subprocess.check_output(
                ['convert', temp_file, '-format', '%[pixel:p{0,0}]', 'info:-']).decode()
            
            # Remove temporary file
            try:
                os.remove(temp_file)
            except Exception:
                pass
            
            # Extract RGB from the 'convert' output
            rgb_match = re.search(r'rgb\((\d+),(\d+),(\d+)\)', color_info, re.IGNORECASE)
            if rgb_match:
                r, g, b = map(int, rgb_match.groups())
                debug_print(f"RGB from ImageMagick: {r}, {g}, {b}")
                return r, g, b
        except Exception as e:
            debug_print(f"Error in ImageMagick: {e}")
        
        # Experiments with x11 screenshot
        try:
            debug_print("Try alternative Linux method with x11")
            # Use Python-Xlib if available
            from Xlib import display, X
            
            d = display.Display()
            root = d.screen().root
            rgb = root.get_image(x, y, 1, 1, X.ZPixmap, 0xffffffff)
            
            # Extract RGB values
            data = rgb.data
            if isinstance(data, bytes) and len(data) >= 4:
                b = data[0]
                g = data[1]
                r = data[2]
                return r, g, b
        except ImportError:
            debug_print("Python-Xlib not installed")
        except Exception as e:
            debug_print(f"Error in X11 method: {e}")
        
        return get_color_fallback()
    except Exception as e:
        debug_print(f"Linux-specific color detection failed: {e}")
        raise

def get_color_fallback():
    """Fallback method when all other methods fail."""
    debug_print("Use fallback color value (black)")
    # Fallback color is black
    return 0, 0, 0

# color conversion capabilities
def rgb_to_hsl(r, g, b):
    r_, g_, b_ = r/255.0, g/255.0, b/255.0
    cmax = max(r_, g_, b_)
    cmin = min(r_, g_, b_)
    delta = cmax - cmin
    l = (cmax + cmin) / 2
    if delta == 0:
        h = s = 0
    else:
        s = delta / (2 - cmax - cmin) if l > 0.5 else delta / (cmax + cmin)
        if cmax == r_:
            h = ((g_ - b_) / delta) % 6
        elif cmax == g_:
            h = ((b_ - r_) / delta) + 2
        else:
            h = ((r_ - g_) / delta) + 4
        h = h * 60
    return f'HSL({round(h)}°, {round(s*100)}%, {round(l*100)}%)'

def rgb_to_hsv(r, g, b):
    r_, g_, b_ = r/255.0, g/255.0, b/255.0
    cmax = max(r_, g_, b_)
    cmin = min(r_, g_, b_)
    delta = cmax - cmin
    if delta == 0:
        h = 0
    elif cmax == r_:
        h = ((g_ - b_) / delta) % 6
    elif cmax == g_:
        h = ((b_ - r_) / delta) + 2
    else:
        h = ((r_ - g_) / delta) + 4
    h = h * 60
    s = 0 if cmax == 0 else delta/cmax
    v = cmax
    return f'HSV({round(h)}°, {round(s*100)}%, {round(v*100)}%)'

def rgb_to_hsi(r, g, b):
    r_, g_, b_ = r/255.0, g/255.0, b/255.0
    I = (r_ + g_ + b_) / 3
    min_val = min(r_, g_, b_)
    S = 0 if I == 0 else 1 - (min_val / I)
    num = 0.5 * ((r_ - g_) + (r_ - b_))
    den = math.sqrt((r_ - g_)**2 + (r_ - b_)*(g_ - b_))
    if den == 0:
        h_rad = 0
    else:
        # Avoiding rounding errors when dividing
        div_result = max(-1, min(1, num/den))
        theta = math.acos(div_result)
        h_rad = theta if b_ <= g_ else (2 * math.pi - theta)
    h = math.degrees(h_rad)
    return f'HSI({round(h)}°, {round(S*100)}%, {round(I*100)}%)'

def rgb_to_cmyk(r, g, b):
    r_, g_, b_ = r/255.0, g/255.0, b/255.0
    k = 1 - max(r_, g_, b_)
    if k == 1:
        c = m = y = 0
    else:
        c = (1 - r_ - k) / (1 - k)
        m = (1 - g_ - k) / (1 - k)
        y = (1 - b_ - k) / (1 - k)
    return f'CMYK({round(c*100)}%, {round(m*100)}%, {round(y*100)}%, {round(k*100)}%)'

def rgb_to_lab(r, g, b):
    r_, g_, b_ = r/255.0, g/255.0, b/255.0
    def to_linear(c):
        return ((c + 0.055) / 1.055)**2.4 if c > 0.04045 else c/12.92
    r_lin = to_linear(r_)
    g_lin = to_linear(g_)
    b_lin = to_linear(b_)
    X = r_lin * 0.4124 + g_lin * 0.3576 + b_lin * 0.1805
    Y = r_lin * 0.2126 + g_lin * 0.7152 + b_lin * 0.0722
    Z = r_lin * 0.0193 + g_lin * 0.1192 + b_lin * 0.9505
    X *= 100; Y *= 100; Z *= 100
    Xn, Yn, Zn = 95.047, 100.0, 108.883
    def f(t):
        return t**(1/3) if t > 0.008856 else (7.787 * t + 16/116)
    L = 116 * f(Y/Yn) - 16
    a_val = 500 * (f(X/Xn) - f(Y/Yn))
    b_val = 200 * (f(Y/Yn) - f(Z/Zn))
    return f'CIE LAB({round(L)}, {round(a_val)}, {round(b_val)})'

def rgb_to_cielch(r, g, b):
    r_, g_, b_ = r/255.0, g/255.0, b/255.0
    def to_linear(c):
        return ((c + 0.055) / 1.055)**2.4 if c > 0.04045 else c/12.92
    r_lin = to_linear(r_)
    g_lin = to_linear(g_)
    b_lin = to_linear(b_)
    X = r_lin * 0.4124 + g_lin * 0.3576 + b_lin * 0.1805
    Y = r_lin * 0.2126 + g_lin * 0.7152 + b_lin * 0.0722
    Z = r_lin * 0.0193 + g_lin * 0.1192 + b_lin * 0.9505
    X *= 100; Y *= 100; Z *= 100
    Xn, Yn, Zn = 95.047, 100.0, 108.883
    def f(t):
        return t**(1/3) if t > 0.008856 else (7.787 * t + 16/116)
    L = 116 * f(Y/Yn) - 16
    a_val = 500 * (f(X/Xn) - f(Y/Yn))
    b_val = 200 * (f(Y/Yn) - f(Z/Zn))
    C = math.sqrt(a_val**2 + b_val**2)
    h_rad = math.atan2(b_val, a_val)
    h_deg = math.degrees(h_rad)
    if h_deg < 0:
        h_deg += 360
    return f'CIELCh({round(L)}, {round(C)}, {round(h_deg)}°)'

def rgb_to_ycbcr(r, g, b):
    Y = 16 + (65.738 * r + 129.057 * g + 25.064 * b) / 256
    Cb = 128 + (-37.945 * r - 74.494 * g + 112.439 * b) / 256
    Cr = 128 + (112.439 * r - 94.154 * g - 18.285 * b) / 256
    return f'YCbCr({round(Y)}, {round(Cb)}, {round(Cr)})'

def rgb_to_xyz(r, g, b):
    r_, g_, b_ = r/255.0, g/255.0, b/255.0
    def to_linear(c):
        return ((c + 0.055) / 1.055)**2.4 if c > 0.04045 else c/12.92
    r_lin = to_linear(r_)
    g_lin = to_linear(g_)
    b_lin = to_linear(b_)
    X = r_lin * 0.4124564 + g_lin * 0.3575761 + b_lin * 0.1804375
    Y = r_lin * 0.2126729 + g_lin * 0.7151522 + b_lin * 0.0721750
    Z = r_lin * 0.0193339 + g_lin * 0.1191920 + b_lin * 0.9503041
    X *= 100; Y *= 100; Z *= 100
    return f'CIE XYZ({round(X)}, {round(Y)}, {round(Z)})'

# Function for calculating all color models from RGB
def get_color_values(r, g, b):
    """Calculates all color models from RGB values."""
    return {
        "HEX/HTML": f'#{r:02X}{g:02X}{b:02X}',
        "RGB": f'RGB({r}, {g}, {b})',
        "HSL": rgb_to_hsl(r, g, b),
        "HSV": rgb_to_hsv(r, g, b),
        "HSI": rgb_to_hsi(r, g, b),
        "CMYK": rgb_to_cmyk(r, g, b),
        "CIE LAB": rgb_to_lab(r, g, b),
        "CIELCh": rgb_to_cielch(r, g, b),
        "YCbCr": rgb_to_ycbcr(r, g, b),
        "CIE XYZ": rgb_to_xyz(r, g, b)
    }

def get_color_at_cursor():
    """Determines the color at the mouse pointer and calculates all color models."""
    r, g, b = get_platform_specific_cursor_color()
    return get_color_values(r, g, b)

# auxiliary functions
def copy_to_clipboard(text, root):
    """Copies the given text to the clipboard."""
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update()

def show_about(root):
    """Displays an 'About' window."""
    about_win = tk.Toplevel(root)
    about_win.title("About Color Picker")
    about_win.geometry("300x200")
    about_win.transient(root)
    about_win.resizable(False, False)
    
    version_label = tk.Label(about_win, text="Color Picker Version 2.0", font=("Helvetica", 12, "bold"))
    version_label.pack(pady=5)
    
    author_label = tk.Label(about_win, text="Author: Robert Tulke", font=("Helvetica", 10))
    author_label.pack(pady=2)
    
    def open_email(event):
        webbrowser.open("mailto:rt@debian.sh")
    
    def open_url(event):
        webbrowser.open("https://github.com/rtulke/ColorPickerNG/")
    
    email_label = tk.Label(about_win, text="rt@debian.sh", fg="blue", cursor="hand2")
    email_label.pack(pady=2)
    email_label.bind("<Button-1>", open_email)
    
    url_label = tk.Label(about_win, text="https://github.com/rtulke/ColorPickerNG/", fg="blue", cursor="hand2")
    url_label.pack(pady=2)
    url_label.bind("<Button-1>", open_url)
    
    features_label = tk.Label(about_win, text="New features: Freeze, palette storage, grouped color models", 
                           wraplength=280, justify=tk.LEFT)
    features_label.pack(pady=5)
    
    close_button = tk.Button(about_win, text="Close", command=about_win.destroy)
    close_button.pack(pady=5)

def show_tooltip(widget, text):
    """Create a tooltip for a widget."""
    tooltip = tk.Toplevel(widget)
    tooltip.wm_overrideredirect(True)
    tooltip.wm_geometry("+0+0")
    tooltip.withdraw()
    
    label = tk.Label(tooltip, text=text, justify=tk.LEFT,
                  background="#FFFFDD", relief=tk.SOLID, borderwidth=1,
                  padx=5, pady=2, wraplength=300)
    label.pack()
    
    def enter(event):
        x, y, _, _ = widget.bbox("insert")
        x += widget.winfo_rootx() + 25
        y += widget.winfo_rooty() + 25
        tooltip.wm_geometry(f"+{x}+{y}")
        tooltip.deiconify()
    
    def leave(event):
        tooltip.withdraw()
    
    widget.bind("<Enter>", enter)
    widget.bind("<Leave>", leave)
    
    return tooltip

def save_palette(history_entries, root):
    """Saves the current history as a color palette."""
    if not history_entries:
        messagebox.showinfo("Information", "No colors available in history to save.")
        return
    
    file_path = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON color palette", "*.json"), ("All files", "*.*")],
        title="Save color palette"
    )
    
    if file_path:
        try:
            # Extract relevant data from the history
            palette_data = []
            for entry in history_entries:
                color_hex = entry["hex"]
                color_values = entry["values"]
                palette_data.append({
                    "hex": color_hex,
                    "values": color_values
                })
            
            # Speichere als JSON
            with open(file_path, 'w') as f:
                json.dump(palette_data, f, indent=2)
            
            messagebox.showinfo("success", f"Color palette was saved as: {file_path}")
        except Exception as e:
            debug_print(f"Error saving palette: {str(e)}")
            messagebox.showerror("Error", f"Error saving palette: {str(e)}")

def load_palette(root, add_to_history_func):
    """Loads a previously saved color palette."""
    file_path = filedialog.askopenfilename(
        defaultextension=".json",
        filetypes=[("JSON color palette", "*.json"), ("All files", "*.*")],
        title="Load color palette"
    )
    
    if file_path:
        try:
            # Load JSON data.
            with open(file_path, 'r') as f:
                palette_data = json.load(f)
            
            # Add palette to history
            for color_entry in reversed(palette_data):  # Reverse so that the newest appear at the top
                hex_color = color_entry["hex"]
                values = color_entry["values"]
                
                # Add each entry to the history
                add_to_history_func(values, hex_color)
            
            messagebox.showinfo("success", f"Color palette has been loaded.: {file_path}")
            return palette_data
        except Exception as e:
            debug_print(f"Error loading the palette: {str(e)}")
            messagebox.showerror("Error", f"Error loading the palette: {str(e)}")
            return []

# main color picker class
class ColorPicker:
    def __init__(self, root, debug=False):
        self.debug = debug
        if self.debug:
            debug_print("ColorPicker initialization started")
        
        self.root = root
        self.root.title("Advanced Color Picker")
        self.root.geometry("500x650")  # Larger window
        
        # foreground option
        self.topmost_var = tk.BooleanVar(value=False)
        
        self.frozen_color = {"r": 0, "g": 0, "b": 0}
        self.freeze_var = tk.BooleanVar(value=False)
        
        # History
        self.history = []  # List of dictionaries with colors and their values
        
        # Cache for the last color captured
        self.last_color = {"r": -1, "g": -1, "b": -1}
        self.last_color_values = {}
        
        # Date of last update for FPS limit
        self.last_update_time = 0
        
        # termination handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Load saved settings.
        self.load_settings()
        
        self.create_ui()
        self.setup_keyboard_shortcuts()
        
        if self.debug:
            debug_print("ColorPicker initialized, starting update loop")
        
        # Starting update loop
        self.update_color()
    
    def save_settings(self):
        """Saves the current settings."""
        settings = {
            "topmost": self.topmost_var.get()
            # Further settings can be added here later.
        }
        
        try:
            # Save in the same directory as the program
            settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                        "colorpicker_settings.json")
            with open(settings_file, 'w') as f:
                json.dump(settings, f)
            
            if self.debug:
                debug_print(f"Settings saved in {settings_file}")
        except Exception as e:
            if self.debug:
                debug_print(f"Error saving settings: {str(e)}")

    def load_settings(self):
        """Loads the saved settings."""
        try:
            # Loading from the same directory as the program
            settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                        "colorpicker_settings.json")
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                
                # Apply topmost setting
                if "topmost" in settings:
                    self.topmost_var.set(settings["topmost"])
                    self.root.wm_attributes("-topmost", settings["topmost"])
                
                if self.debug:
                    debug_print(f"Settings loaded from {settings_file}")
        except Exception as e:
            if self.debug:
                debug_print(f"Error loading settings: {str(e)}")
    
    def on_closing(self):
        """This is called when the program is closed."""
        self.save_settings()
        self.root.destroy()
        
    def create_ui(self):
        """Creates the user interface."""
        if self.debug:
            debug_print("Create user interface")
        
        # main frame
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # menu bar
        self.create_menu()
        
        # info label (left-aligned)
        info_label = ttk.Label(main_frame, text="The color under the cursor is captured live.", anchor="w")
        info_label.pack(pady=5, fill=tk.X)
        
        # frame for color display and freeze button
        color_control_frame = ttk.Frame(main_frame)
        color_control_frame.pack(fill=tk.X, pady=5)
        
        # color preview (larger)
        self.color_display = ttk.Label(color_control_frame, text="", width=15, relief="solid")
        self.color_display.pack(side=tk.LEFT, padx=5, fill=tk.BOTH)
        
        # freeze button
        freeze_button = ttk.Button(color_control_frame, text="freeze (space)", 
                                 command=self.toggle_freeze)
        freeze_button.pack(side=tk.LEFT, padx=5)
        
        # foreground checkbox
        topmost_cb = ttk.Checkbutton(color_control_frame, 
                                   text="Stop in the foreground",
                                   variable=self.topmost_var,
                                   command=self.toggle_topmost)
        topmost_cb.pack(side=tk.LEFT, padx=5)
        
        # Show all color values
        self.create_color_values_display(main_frame)
        
        # Frame for pallet area and history
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Scrollable history section
        self.create_history_area(bottom_frame)
        
        if self.debug:
            debug_print("user interface created")
    
    def create_menu(self):
        """Creates the menu bar."""
        menubar = tk.Menu(self.root)
        
        # file menu
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Save pallet", command=self.save_current_palette)
        filemenu.add_command(label="Load pallet", command=self.load_palette)
        filemenu.add_separator()
        filemenu.add_command(label="Cancel (Esc)", command=self.root.quit, accelerator="Esc")
        menubar.add_cascade(label="File", menu=filemenu)
        
        # Edit menu
        editmenu = tk.Menu(menubar, tearoff=0)
        editmenu.add_command(label="Freeze/Unfreeze", command=self.toggle_freeze, accelerator="Space")
        editmenu.add_command(label="Copy current color mode", command=self.copy_current_color, accelerator="Strg+C")
        editmenu.add_separator()
        editmenu.add_checkbutton(label="Stop in the foreground", 
                               variable=self.topmost_var, 
                               command=self.toggle_topmost)
        editmenu.add_separator()                       
        editmenu.add_command(label="Clear history", command=self.clear_history)
        menubar.add_cascade(label="Edit", menu=editmenu)
        
        # Help menu
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About Color Picker", command=lambda: show_about(self.root), accelerator="F1")
        
        # Debug option if debug mode is active
        if self.debug:
            helpmenu.add_separator()
            helpmenu.add_command(label="Test color capture", command=self.test_color_detection)
        
        menubar.add_cascade(label="Help", menu=helpmenu)
        
        self.root.config(menu=menubar)
    
    def create_color_values_display(self, parent):
        """Creates the area for displaying all color values."""
        # Use of a LabelFrame with a frame
        values_frame = ttk.LabelFrame(parent, text="color values")
        values_frame.pack(fill=tk.BOTH, padx=5, pady=5)
        
        # Column-wise arrangement of the color models
        color_models_frame = ttk.Frame(values_frame)
        color_models_frame.pack(fill=tk.BOTH, padx=5, pady=5)
        
        # Grouping of color models
        color_groups = {
            "Web": ["HEX/HTML", "RGB"],
            "HSx-Modelle": ["HSL", "HSV", "HSI"],
            "Druck": ["CMYK"],
            "Erweitert": ["CIE LAB", "CIELCh", "CIE XYZ", "YCbCr"]
        }
        
        # Tooltips for more complex color models
        tooltips = {
            "HSL": "Hue, Saturation, Lightness - Good for intuitive color selection",
            "HSV": "Hue, Saturation, Value - Optimal for color selection dialogs",
            "HSI": "Hue, Saturation, Intensity - Alternative to HSL",
            "CMYK": "Cyan, Magenta, Yellow, Key (Black) - For printing applications",
            "CIE LAB": "L* (brightness), a* (green-red axis), b* (blue-yellow axis) - device-independent color model",
            "CIELCh": "Lightness, Chroma, Hue - A more intuitive version of the LAB model",
            "YCbCr": "Y (luminance), Cb (blue difference), Cr (red difference) - For video applications",
            "CIE XYZ": "Standardized color model, basis for many other models"
        }
        
        # Create UI elements for each group
        group_row = 0
        group_col = 0
        
        for group_name, models in color_groups.items():
            # Group as label
            group_label = ttk.Label(color_models_frame, text=group_name + ":", font=("Helvetica", 10, "bold"))
            group_label.grid(row=group_row, column=group_col, sticky=tk.W, padx=5, pady=(5, 2))
            
            # Color models of this group
            model_row = group_row + 1
            for model in models:
                # Label for the model name
                model_label = ttk.Label(color_models_frame, text=model + ":")
                model_label.grid(row=model_row, column=group_col, sticky=tk.W, padx=5)
                
                # Value label for this model
                value_label = ttk.Label(color_models_frame, text="")
                value_label.grid(row=model_row, column=group_col+1, sticky=tk.W, padx=5)
                
                # Add tooltip if available
                if model in tooltips:
                    show_tooltip(model_label, tooltips[model])
                
                # Save reference to label
                setattr(self, f"{model.lower().replace('/', '_')}_label", value_label)
                
                model_row += 1
            
            # Next group on the right or in a new line
            if group_col < 1:  # Maximum 2 columns
                group_col += 2
            else:
                group_col = 0
                group_row = model_row + 1
        
        # copy info
        #copy_info = ttk.Label(values_frame, text="(Ctrl+C to copy the currently selected color)")
        #copy_info.pack(pady=5)

    def create_history_area(self, parent):
        """Creates the scrollable history area with improved scrolling."""
        history_frame = ttk.LabelFrame(parent, text="History")
        history_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # frame for canvas and scrollbars
        scroll_frame = ttk.Frame(history_frame)
        scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        # Canvas for scrolling (without visible frame)
        self.history_canvas = tk.Canvas(scroll_frame, highlightthickness=0, bd=0)
        
        # Scrollbar with visible configuration
        history_scrollbar = ttk.Scrollbar(scroll_frame, orient="vertical", 
                                     command=self.history_canvas.yview)
        
        # Important: Pack scrollbar FIRST so that it is always visible
        history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Connect canvas with scrollbar
        self.history_canvas.configure(yscrollcommand=history_scrollbar.set)
        
        # Frame within the canvas for the history entries (without visible frame)
        self.history_frame = ttk.Frame(self.history_canvas, padding=0)
        self.history_canvas_window = self.history_canvas.create_window(
            (0, 0), window=self.history_frame, anchor="nw", 
            width=self.history_canvas.winfo_width()  # Important: set width
        )
        
        # Mouse wheel scrolling for ALL relevant widgets
        # Scrolling functions
        def _bind_mousewheel(widget):
            widget.bind("<MouseWheel>", self.on_mousewheel)  # Windows
            widget.bind("<Button-4>", self.on_mousewheel)    # Linux Scroll-up
            widget.bind("<Button-5>", self.on_mousewheel)    # Linux Scroll-down
            
            # For macOS
            if platform.system() == 'Darwin':
                widget.bind("<MouseWheel>", self.on_mousewheel_macos)
            
            # Recursive for all child widgets
            for child in widget.winfo_children():
                _bind_mousewheel(child)
        
        # Enable scrolling for canvas and content
        _bind_mousewheel(self.history_canvas)
        _bind_mousewheel(self.history_frame)
        
        # Recall this method when new entries are added
        self.bind_history_scroll = _bind_mousewheel
        
        # Configure canvas scroll region
        self.history_frame.bind("<Configure>", self.on_history_frame_configure)
        self.history_canvas.bind("<Configure>", self.on_history_canvas_configure)

    def on_history_frame_configure(self, event):
        """Updates the scroll region of the canvas to the actual size of the frame."""
        # Set the scroll region to the actual size of the inner frame
        self.history_canvas.configure(scrollregion=self.history_canvas.bbox("all"))
        
        # Debugging for scroll region
        if self.debug:
            region = self.history_canvas.bbox("all")
            debug_print(f"Scroll region updated: {region}")
    
    def on_history_canvas_configure(self, event):
        """Adjusts the width of the inner frame to fit the canvas."""
        # Make sure that the inner frame is the full width of the canvas.
        canvas_width = event.width
        self.history_canvas.itemconfig(self.history_canvas_window, width=canvas_width)
        
        # Update the scroll region, too
        self.history_canvas.configure(scrollregion=self.history_canvas.bbox("all"))
    
    def on_mousewheel(self, event):
        """Enables scrolling with the mouse wheel (for Windows and Linux)."""
        # Platform-specific processing of the mouse wheel event
        if hasattr(event, 'num') and event.num in (4, 5):  # Linux
            delta = -1 if event.num == 5 else 1
        elif hasattr(event, 'delta'):  # Windows
            delta = event.delta // 120  # Normalization for Windows
        else:
            delta = 0
            
        # Customize scroll direction and strength
        if delta != 0:
            # The same scrolling command as clicking the scrollbar
            self.history_canvas.yview_scroll(-delta, "units")
            # Mark event as “handled” so that other widgets don't get it
            return "break"
    
    def on_mousewheel_macos(self, event):
        """Use the mouse wheel to scroll (for macOS)."""
        # macOS has a different sign for scrolling
        delta = -1 if event.delta > 0 else 1
                
        # The same scrolling command as clicking the scrollbar
        self.history_canvas.yview_scroll(delta, "units")
        # Mark event as “handled” so that other widgets don't get it
        return "break"
    
    def setup_keyboard_shortcuts(self):
        """Sets up keyboard shortcuts."""
        # Press ESC to end
        self.root.bind("<Escape>", lambda e: self.root.quit())
        
        # F1 for about dialog
        self.root.bind("<F1>", lambda e: show_about(self.root))
        
        # Space bar for freeze
        self.root.bind("<space>", lambda e: self.toggle_freeze())
        
        # Ctrl+C to copy
        self.root.bind("<Control-c>", lambda e: self.copy_current_color())
    
    def toggle_freeze(self):
        """Toggles between freezing and unfreezing the color detection."""
        new_value = not self.freeze_var.get()
        self.freeze_var.set(new_value)
        
        # When freezing, save the current color
        if new_value:
            colors = get_color_at_cursor()
            rgb = colors["RGB"]
            import re
            match = re.search(r'RGB\((\d+), (\d+), (\d+)\)', rgb)
            if match:
                r, g, b = map(int, match.groups())
                self.frozen_color["r"], self.frozen_color["g"], self.frozen_color["b"] = r, g, b
                if self.debug:
                    debug_print(f"color frozen: RGB({r}, {g}, {b})")
    
    def toggle_topmost(self):
        """Enables or disables keeping the foreground."""
        is_topmost = self.topmost_var.get()
        self.root.wm_attributes("-topmost", is_topmost)
        if self.debug:
            debug_print(f"foreground mode: {'active' if is_topmost else 'inactive'}")
        self.save_settings()
    
    def copy_current_color(self):
        """Copy the current color value to the clipboard."""
        if self.freeze_var.get():
            r, g, b = self.frozen_color["r"], self.frozen_color["g"], self.frozen_color["b"]
            colors = get_color_values(r, g, b)
        else:
            colors = get_color_at_cursor()
        
        # Use the first color model as default
        model = list(colors.keys())[0]
        value = colors[model]
        
        copy_to_clipboard(value, self.root)
        self.add_to_history(value, colors["HEX/HTML"])
        
        if self.debug:
            debug_print(f"Copied to clipboard: {value}")
    
    def add_to_history(self, value, hex_color):
        """Add a new entry to the history."""
        # Save all values of this color value
        if self.freeze_var.get():
            r, g, b = self.frozen_color["r"], self.frozen_color["g"], self.frozen_color["b"]
            all_values = get_color_values(r, g, b)
        else:
            all_values = self.last_color_values.copy() if self.last_color_values else get_color_at_cursor()
        
        # Add to history list
        self.history.insert(0, {"hex": hex_color, "values": all_values, "selected": value})
        
        # Limit the size of the history
        if len(self.history) > 50:
            self.history.pop()
        
        # UI update
        self.update_history_display()
        
        if self.debug:
            debug_print(f"color added to history: {hex_color}")
    
    def update_history_display(self):
        """Update the history display with a scroll function for all elements."""
        # Delete previous entries
        for widget in self.history_frame.winfo_children():
            widget.destroy()
        
        # Show new entries
        for idx, entry in enumerate(self.history):
            hex_color = entry["hex"]
            selected_value = entry["selected"]
            
            # frameless frame
            row = ttk.Frame(self.history_frame, padding=0)
            row.pack(fill=tk.X, pady=2, padx=2)
            
            # color preview
            color_preview = ttk.Label(row, text="", background=hex_color, width=3)
            color_preview.pack(side=tk.LEFT, padx=2)
            
            # value text
            text_label = ttk.Label(row, text=selected_value)
            text_label.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
            
            # copy button
            copy_btn = ttk.Button(row, text="copy", 
                               command=lambda val=selected_value: copy_to_clipboard(val, self.root))
            copy_btn.pack(side=tk.LEFT, padx=2)
            
            # delete button
            delete_btn = ttk.Button(row, text="delete", 
                                 command=lambda idx=idx: self.delete_history_entry(idx))
            delete_btn.pack(side=tk.LEFT, padx=2)
        
        # Update the scroll region after adding all entries
        self.history_canvas.configure(scrollregion=self.history_canvas.bbox("all"))
        
        # Important: Bind mouse wheel scrolling for ALL new elements
        if hasattr(self, 'bind_history_scroll'):
            self.bind_history_scroll(self.history_frame)
        
        # If there are entries, scroll up.
        if self.history:
            self.history_canvas.yview_moveto(0.0)
    
    def delete_history_entry(self, index):
        """Deletes an entry from the color history."""
        if 0 <= index < len(self.history):
            del self.history[index]
            self.update_history_display()
            if self.debug:
                debug_print(f"history entry {index} deleted")
    
    def clear_history(self):
        """Deletes the entire color history."""
        result = messagebox.askyesno("Delete history", 
                                   "Are you sure you want to delete all color history?")
        if result:
            self.history = []
            self.update_history_display()
            if self.debug:
                debug_print("Entire history deleted")
    
    def save_current_palette(self):
        """Saves the current palette."""
        save_palette(self.history, self.root)
    
    def load_palette(self):
        """Loads a palette and adds it to the history."""
        load_palette(self.root, self.add_to_history)
    
    def update_color_displays(self, colors):
        """Updates all color value displays."""
        # color preview
        self.color_display.configure(background=colors["HEX/HTML"])
        
        # Update all value labels
        for model, value in colors.items():
            label_name = f"{model.lower().replace('/', '_')}_label"
            if hasattr(self, label_name):
                label = getattr(self, label_name)
                label.configure(text=value)
        
        # Set window title with freeze info
        if self.freeze_var.get():
            self.root.title("Advanced Color Picker - Frozen")
        else:
            self.root.title("Advanced Color Picker")
    
    def test_color_detection(self):
        """Tests the color detection functions."""
        if not self.debug:
            return
            
        test_win = tk.Toplevel(self.root)
        test_win.title("color perception test")
        test_win.geometry("400x300")
        
        # Test of direct color capture
        ttk.Label(test_win, text="color perception test:", font=("Arial", 12, "bold")).pack(pady=5)
        
        # Test Windows method
        win_frame = ttk.LabelFrame(test_win, text="Windows method")
        win_frame.pack(fill=tk.X, padx=10, pady=5)
        
        win_result = ttk.Label(win_frame, text="Not tested.")
        win_result.pack(pady=5)
        
        ttk.Button(win_frame, text="test", 
                command=lambda: self.test_method(win_result, "windows")).pack(pady=5)
        
        # test macOS method
        mac_frame = ttk.LabelFrame(test_win, text="macOS method")
        mac_frame.pack(fill=tk.X, padx=10, pady=5)
        
        mac_result = ttk.Label(mac_frame, text="Not tested.")
        mac_result.pack(pady=5)
        
        ttk.Button(mac_frame, text="test", 
                command=lambda: self.test_method(mac_result, "macos")).pack(pady=5)
        
        # Test the Linux method
        linux_frame = ttk.LabelFrame(test_win, text="Linux method")
        linux_frame.pack(fill=tk.X, padx=10, pady=5)
        
        linux_result = ttk.Label(linux_frame, text="Not tested.")
        linux_result.pack(pady=5)
        
        ttk.Button(linux_frame, text="test", 
                 command=lambda: self.test_method(linux_result, "linux")).pack(pady=5)
        
        # Test fallback method
        fallback_frame = ttk.LabelFrame(test_win, text="fallback method")
        fallback_frame.pack(fill=tk.X, padx=10, pady=5)
        
        fallback_result = ttk.Label(fallback_frame, text="Not tested.")
        fallback_result.pack(pady=5)
        
        ttk.Button(fallback_frame, text="test", 
                 command=lambda: self.test_method(fallback_result, "fallback")).pack(pady=5)
    
    def test_method(self, result_label, method):
        """Tests a particular color capture method."""
        try:
            if method == "windows":
                r, g, b = get_color_windows()
            elif method == "macos":
                r, g, b = get_color_macos()
            elif method == "linux":
                r, g, b = get_color_linux()
            else:
                r, g, b = get_color_fallback()
                
            color_hex = f"#{r:02X}{g:02X}{b:02X}"
            result_label.configure(text=f"RGB({r}, {g}, {b}) - {color_hex}", background=color_hex)
            if method != "fallback":
                debug_print(f"{method.capitalize()}-method successful: RGB({r}, {g}, {b})")
            return True
        except Exception as e:
            result_label.configure(text=f"error: {str(e)}")
            debug_print(f"{method.capitalize()}-Method failed: {e}")
            return False
    
    def update_color(self):
        """Updates the color display (with refresh rate limit)."""
        current_time = time.time()
        
        try:
            # Limit the update rate to 20 FPS (50ms)
            if current_time - self.last_update_time >= 0.05:
                self.last_update_time = current_time
                
                if self.freeze_var.get():
                    # Use frozen color
                    r, g, b = self.frozen_color["r"], self.frozen_color["g"], self.frozen_color["b"]
                    colors = get_color_values(r, g, b)
                else:
                    # Get the current color under the cursor
                    r, g, b = get_platform_specific_cursor_color()
                    
                    # Cache: Only if the color has changed
                    if (r != self.last_color["r"] or 
                        g != self.last_color["g"] or 
                        b != self.last_color["b"]):
                        self.last_color["r"], self.last_color["g"], self.last_color["b"] = r, g, b
                        self.last_color_values = get_color_values(r, g, b)
                    
                    colors = self.last_color_values
                
                # Refresh the display
                self.update_color_displays(colors)
        except Exception as e:
            if self.debug:
                debug_print(f"Error during color update: {str(e)}")
        
        # Schedule next update.
        self.root.after(20, self.update_color)

def check_platform_requirements():
    """Checks for platform-specific requirements and issues warnings."""
    system = platform.system()
    
    if system == 'Darwin':  # macOS
        # Checking screen access rights
        try:
            test_result = subprocess.run(
                ['osascript', '-e', 'tell application "System Events" to get the name of every process'],
                capture_output=True
            )
            if test_result.returncode != 0:
                print("\nWARNING: The Color Picker requires access to operating aids under macOS.")
                print("Please go to System Preferences → Security → Privacy → Accessibility.")
                print("and add your terminal app or Python interpreter.")
        except Exception:
            print("\nWARNING: Could not verify macOS authorizations.")
    
    elif system == 'Linux':
        # Checking the necessary Linux packages
        required_tools = {
            'xdotool': 'mouse tracking',
            'import': 'Part of the ImageMagick package for screenshots',
            'convert': 'Part of the ImageMagick package for image processing'
        }
        
        missing_tools = []
        for tool, description in required_tools.items():
            try:
                result = subprocess.run(['which', tool], capture_output=True)
                if result.returncode != 0:
                    missing_tools.append(f"{tool} ({description})")
            except Exception:
                missing_tools.append(f"{tool} (could not be verified)")
        
        if missing_tools:
            print("\nWARNING: The following tools are required but were not found:")
            for tool in missing_tools:
                print(f"  - {tool}")
            print("Please install these tools for full functionality.")
            print("On Ubuntu/Debian: sudo apt-get install xdotool imagemagick")
            print("Under Fedora: sudo dnf install xdotool ImageMagick")
    
    return True  # Always continue, even if warnings are present

def create_picker(debug_mode=False):
    """Main function for creating and launching the color picker."""
    global DEBUG
    DEBUG = debug_mode
    
    if debug_mode:
        debug_print("Start Color Picker in debug mode")
        debug_print(f"operating system: {platform.system()} {platform.version()}")
    
    # Check platform-specific requirements
    check_platform_requirements()
    
    try:
        root = tk.Tk()
        if debug_mode:
            debug_print("Tkinter root created")
        
        app = ColorPicker(root, debug=debug_mode)
        if debug_mode:
            debug_print("Color Picker instance created")
        
        root.mainloop()
    except Exception as e:
        print(f"\nERROR while starting the color picker: {str(e)}")
        if debug_mode:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    # Debug mode can be activated via command line argument
    import argparse
    parser = argparse.ArgumentParser(description="Color Picker Next Gen")
    parser.add_argument('--debug', action='store_true', help='Activates debug mode')
    args = parser.parse_args()
    
    try:
        create_picker(debug_mode=args.debug)
    except Exception as e:
        print(f"An unexpected error has occurred: {str(e)}")
        if args.debug:
            import traceback
            traceback.print_exc()
