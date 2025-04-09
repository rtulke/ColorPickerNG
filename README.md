# Color Picker Next Gen

A cross-platform tool for capturing and analyzing colors on the screen with support for multiple color models and color palettes that works with standard Python libraries.

I developed this ColorPicker to solve a specific challenge - working on a restricted Windows system where I had limited permissions. Unable to install additional software or use pip to add Python modules, I needed to create a tool that would function using only standard libraries.

Despite these constraints, the result is a versatile ColorPicker that works seamlessly across Windows, macOS, and Linux - all without requiring external dependencies that would have been cumbersome to install manually due to their complex dependency chains.

![ColorPickerNG](https://raw.githubusercontent.com/rtulke/ColorPickerNG/main/demo/colorpickerng.png)

## Features

- **Cross-platform compatibility** - Works on Windows, macOS, and Linux
- **Real-time color capture** - Captures colors under the mouse cursor in real-time
- **Multiple color models** - Shows color values in various formats:
  - Web formats: HEX/HTML, RGB
  - HSx models: HSL, HSV, HSI
  - Print: CMYK
  - Advanced models: CIE LAB, CIELCh, CIE XYZ, YCbCr
- **Color history** - Keeps track of captured colors for easy reference
- **Palette management** - Save and load color palettes
- **Freeze function** - Pause color picking to examine a specific color
- **Stay on top** - Option to keep the tool in the foreground
- **Keyboard shortcuts** - Quick access to common functions
- **Clipboard integration** - Easily copy color values to clipboard

## Requirements

### Windows
- No special requirements

### macOS
- Access to Accessibility features (System Preferences → Security → Privacy → Accessibility)
- Terminal or Python interpreter should be added to the allowed applications

### Linux
- `xdotool` - For mouse tracking
- `imagemagick` - For screenshots and image processing (provides `import` and `convert` commands)

You can install these requirements on:
- Ubuntu/Debian: `sudo apt-get install xdotool imagemagick`
- Fedora: `sudo dnf install xdotool ImageMagick`

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/rtulke/ColorPickerNG.git
   ```

2. Make sure you have Python 3 installed.

3. Install required Python packages:
   ```
   pip install tkinter
   ```

4. Run the application:
   ```
   python color_picker.py
   ```

## Usage

- **Move your mouse** to see the color under the cursor
- **Spacebar** to freeze/unfreeze color capturing
- **Ctrl+C** to copy the current color value to clipboard
- **Right-click** on a color in history to see available actions
- **File > Save palette** to store your current color history
- **File > Load palette** to restore previously saved colors
- **ESC** to exit the application

## Debug Mode

You can run the application in debug mode for troubleshooting:

```
python color_picker.py --debug
```

This will print detailed information about operations and enable additional testing options in the Help menu.

## Technical Details

### Color Conversion
The tool implements various color model conversions:
- RGB to HSL/HSV/HSI (Hue, Saturation, Lightness/Value/Intensity)
- RGB to CMYK (Cyan, Magenta, Yellow, Key)
- RGB to CIE LAB/LCh (device-independent color models)
- RGB to YCbCr (used in video processing)
- RGB to CIE XYZ (standardized color model)

### Platform-Specific Implementation
The application uses different methods to capture screen colors depending on the operating system:

- **Windows:** Uses Windows API (GDI) to get pixel color
- **macOS:** Uses a combination of AppleScript and screen capture
- **Linux:** Uses xdotool and ImageMagick for cursor position and screen capture

## Contributing

Contributions to improve the Color Picker are welcome. Please feel free to submit a Pull Request.

## License

This project is licensed under the GNU General Public License v3.0 - see the LICENSE file for details.
