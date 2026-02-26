# Operation Black Hawk

A professional flight simulation application built with Python and OpenGL. Experience realistic helicopter flight dynamics with a large-scale world environment and dynamic flight controls.

## Features

- **Realistic Flight Dynamics**: Implements authentic speed, yaw, pitch, roll, and bank mechanics
- **Large-Scale World**: Explore an expansive 100x terrain with procedurally generated ground tiles
- **Dynamic Controls**: Responsive aircraft controls with speed regulation, pitch/yaw rate scaling, and visual control surfaces
- **Advanced Graphics**: Utilizes OpenGL for high-performance 3D rendering with optimized tile-based terrain culling
- **Complex Physics**: Manages flap animations, rudder tracking, and realistic flight model parameters

## Requirements

- Python 3.6+
- PyOpenGL
- PyOpenGL_accelerate (optional, for performance improvement)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/operation-black-hawk.git
cd operation-black-hawk
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the application:

```bash
python Operarion_Black_Hawk.py
```

### Controls

- **A/D** - Yaw left/right
- **W/S** - Pitch up/down
- **Q/E** - Bank left/right
- **+/-** - Increase/decrease airspeed
- **ESC** - Exit application

## Project Structure

```
operation-black-hawk/
├── Operarion_Black_Hawk.py       # Main application entry point
├── requirements.txt              # Project dependencies (PyOpenGL, etc.)
├── README.md                     # This file
├── LICENSE                       # MIT License
├── CONTRIBUTING.md               # Contribution guidelines
└── .gitignore                    # Git ignore rules
```

## Dependencies

All required Python packages are listed in `requirements.txt` and will be installed automatically via pip. This project uses the following external package:

- **PyOpenGL** - Python bindings for OpenGL (automatically downloaded and installed from PyPI)

## Technical Details

### Flight Parameters

- **Speed Range**: 120 - 1200 units/second
- **FOV**: 75 degrees
- **Terrain Size**: 1,200,000 units with 600-unit tile size
- **Draw Distance**: Up to 300,000 units

### Performance Optimization

- Tile-based terrain culling (40-step radius around player)
- Z-fighting prevention with strategic rendering offsets
- Visual control surface animations for pitch, roll, and rudder

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Academic Context

This project was developed as part of CSE 423 course work focusing on advanced graphics programming and flight simulation mechanics.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## Author

Created for CSE 423 - Advanced Topics in Computer Science
