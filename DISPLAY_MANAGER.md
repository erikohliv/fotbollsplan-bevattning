# Display Manager Documentation

## Overview

The Display Manager implements control for two I2C LCD displays used in the Fotbollsplan irrigation system:

- **Display 1 (D1)**: 20x4 LCD without buttons - Auto-rotating status display
- **Display 2 (D2)**: 2x8 LCD with 4 buttons - Interactive manual control

## Hardware Requirements

### Display 1
- 20 columns × 4 rows LCD with I2C interface (HD44780-based)
- Default I2C address: `0x27` (configurable)
- No buttons required
- Displays system status with auto-rotation

### Display 2
- 8 columns × 2 rows LCD with I2C interface (HD44780-based)
- Default I2C address: `0x3F` (configurable)
- 4 buttons connected to PLC (read via Modbus):
  - LEFT: DI11 (Meny Vänster/Upp)
  - RIGHT: DI12 (Meny Höger/Ner)
  - OK: DI13 (Meny OK/Välj)
  - BACK: DI14 (Meny Tillbaka)
- Buttons read from Modbus register MW64 (bitmask)
- Used for manual control and settings

### Required Hardware
- Raspberry Pi (or compatible) with I2C enabled
- Two I2C LCD displays (20x4 and 2x8)
- Four push buttons connected to UNIPI PLC inputs (DI11-DI14)
- UNIPI PLC with Modbus TCP interface

## Installation

### 1. Enable I2C on Raspberry Pi

```bash
sudo raspi-config
# Navigate to: Interface Options -> I2C -> Enable
sudo reboot
```

### 2. Install Dependencies

```bash
# Install system packages
sudo apt-get update
sudo apt-get install -y python3-pip i2c-tools python3-smbus

# Install Python packages
pip install -r display_requirements.txt
```

**Note:** GPIO support (RPi.GPIO) is no longer required as buttons are read from PLC via Modbus.

### 3. Verify I2C Devices

```bash
# List I2C devices
i2cdetect -y 1

# You should see your displays at addresses 0x27 and 0x3F (or similar)
```

## Configuration

### Display I2C Addresses

Find your display addresses using `i2cdetect -y 1`. Common addresses:
- `0x27`, `0x3F` - PCF8574-based I2C adapters
- `0x20`, `0x21` - MCP23008/23017-based adapters

### Menu Button Configuration

Menu buttons are connected to UNIPI PLC inputs (DI11-DI14) and read via Modbus register MW64:
```python
# Button mapping in PLC (read from MW64 bitmask):
# bit0: LEFT (DI11)  - Meny Vänster/Upp
# bit1: RIGHT (DI12) - Meny Höger/Ner
# bit2: OK (DI13)    - Meny OK/Välj (long press >2s to confirm)
# bit3: BACK (DI14)  - Meny Tillbaka
```

No configuration needed - buttons are automatically read from PLC.

## Usage

### Running the Display Manager

```bash
# Basic usage with default settings
python3 display_manager.py

# Custom I2C addresses
python3 display_manager.py --d1-addr 0x27 --d2-addr 0x3F

# Custom Modbus connection
python3 display_manager.py --modbus-host 192.168.1.100 --modbus-port 502

# Enable auto-watering scheduler
python3 display_manager.py --enable-scheduler --schedule-hour 1 --schedule-minute 0

# Adjust Display 1 rotation interval
python3 display_manager.py --d1-interval 5.0

# Simulation mode (no hardware required)
python3 display_manager.py --simulate
```

### Running as a Service

Create a systemd service file `/etc/systemd/system/display-manager.service`:

```ini
[Unit]
Description=Fotbollsplan Display Manager
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/fotbollsplan-bevattning
ExecStart=/usr/bin/python3 /home/pi/fotbollsplan-bevattning/display_manager.py --enable-scheduler
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable display-manager
sudo systemctl start display-manager
sudo systemctl status display-manager
```

## Display 1 (20x4) - Auto-Rotating Views

Display 1 automatically rotates through 4 different views every 3-5 seconds (configurable).

### View 1: STATUS
```
Auto   Z:2/2   PUMP:ON
Stage:3        HB:*
T:18C M:45% R:2mm
Status: OK
```
Shows:
- Current mode (Auto/Manual)
- Selected zone / Current zone
- Pump status (ON/OFF)
- Stage number
- Heartbeat indicator
- Temperature, Moisture, Rain
- Block status

### View 2: BLOCK CONDITIONS
```
  BLOCK CONDITIONS
Moisture: 45%
Rain 24h:  2mm
Reason: OK
```
Shows conditions that may block irrigation.

### View 3: PUMP STATE
```
     PUMP STATE
Status: ON
Current Zone: 2
Stage: 3
```
Detailed pump and zone information.

### View 4: CONNECTIVITY
```
   CONNECTIVITY
Modbus: OK
Heartbeat: 123
Time: 09:56:35
```
Shows communication status and system time.

## Display 2 (2x8) - Interactive Control

Display 2 provides manual control through button navigation.

### View Navigation
- **LEFT button**: Previous view
- **RIGHT button**: Next view

### View 1: OVERVIEW
```
A Z:2
P:ON
```
Shows:
- Mode: A=Auto, M=Manual
- Current zone
- Pump status (P:ON or P:OFF)

### View 2: ZONE SELECTION
```
  Zone
   2
```
Or when confirmed:
```
 Zone OK
   2
```
Select irrigation zone (1-7):
- **UP button**: Increment zone (wraps 7→1)
- **DOWN button**: Decrement zone (wraps 1→7)
- **Hold UP or DOWN for 3 seconds**: Confirm zone selection

After confirmation, the selected zone is written to Modbus (MW63) and will be used when manual start is triggered via the physical Start button.

### Starting Manual Irrigation

1. Navigate to ZONE SELECTION view (use LEFT/RIGHT buttons)
2. Select desired zone using UP/DOWN buttons
3. Hold UP or DOWN for 3 seconds to confirm (display shows "Zone OK")
4. Press the physical **Start** button on the control panel
5. Manual sequence runs **only the selected zone**, using auto mode times (Set_Tid_Center for zones 1-3, Set_Tid_Horn for zones 4-7)

Note: Time selection has been removed. Manual mode now uses the same irrigation times as auto mode.

## Auto-Watering Scheduler

The scheduler triggers automatic watering at a configured time (default: 01:00).

### Features
- Checks block conditions before triggering
- Only triggers once per day
- Respects environmental thresholds (rain, moisture, temperature)
- Logs all trigger attempts

### Auto Mode Transition at 21:00

A separate scheduler can be enabled to passively transition the system to auto mode at 21:00 daily.

### Features
- Transitions to auto mode without triggering watering
- If a sequence is running at 21:00, waits for completion before transitioning
- Ensures system is in auto mode for the next scheduled watering (01:00)
- Only performs mode transition once per day

### Configuration
```bash
# Enable auto mode transition at 21:00
python3 display_manager.py --enable-auto-mode-transition

# Set custom transition time (e.g., 22:30)
python3 display_manager.py --enable-auto-mode-transition --transition-hour 22 --transition-minute 30
```

### Block Reasons
The scheduler checks for these conditions:
- `OK`: All conditions met, watering allowed
- `RAIN_THRESHOLD`: Too much rain forecasted
- `MOISTURE_THRESHOLD`: Soil moisture too high
- `ANTI_COLLISION`: System busy with another operation
- `E_STOP`: Emergency stop active

### Configuration
```bash
# Set custom schedule time (e.g., 3:30 AM)
python3 display_manager.py --enable-scheduler --schedule-hour 3 --schedule-minute 30
```

## Integration with Existing System

The Display Manager integrates with the existing irrigation system via Modbus registers:

### Read Registers
- MW50-53: Status (zone, pump, stage, selected zone)
- MW60: Mode (1=Auto, 0=Manual)
- MW70-73: Heartbeat and block status
- MW30-32: Environmental data (moisture, rain, temperature)

### Write Registers
- MW10: Remote command (50=start auto)
- MW60: Mode override (1=Auto, 0=Manual)
- MW61: Manual start pulse
- MW63: Set selected zone
- MW64: Manual run time (DEPRECATED - manual mode now uses auto times)

## Testing

### Run Test Suite
```bash
python3 test_display_manager.py
```

The test suite includes:
1. Modbus integration tests
2. Display rendering tests
3. Display 1 auto-rotation tests
4. Display 2 button navigation tests
5. Auto-scheduler tests

All tests use mocks and don't require physical hardware.

### Manual Testing

Test without hardware using simulation mode:
```bash
python3 display_manager.py --simulate
```

This mode:
- Uses mock I2C communication
- Logs all display operations
- Allows testing logic without hardware

## Troubleshooting

### I2C Connection Issues

```bash
# Check if I2C is enabled
ls /dev/i2c-*

# Scan for I2C devices
i2cdetect -y 1

# Check I2C speed (should be 100kHz for most LCDs)
sudo nano /boot/config.txt
# Add or modify: dtparam=i2c_baudrate=100000
```

### Display Not Showing Text

1. Check I2C address: `i2cdetect -y 1`
2. Verify contrast adjustment on LCD (adjust potentiometer)
3. Check 5V power supply to LCD
4. Verify I2C wiring: SDA, SCL, VCC, GND

### Button Input Issues

Buttons are now read from PLC via Modbus (MW64). To test:

```bash
# Test Modbus connection
python3 -c "from pymodbus.client import ModbusTcpClient; c = ModbusTcpClient('127.0.0.1'); print(c.connect())"

# Read button status from MW64
python3 -c "from pymodbus.client import ModbusTcpClient; c = ModbusTcpClient('127.0.0.1'); c.connect(); r = c.read_holding_registers(64, 1); print(f'MW64 = {r.registers[0]}')"
```

Check button wiring to PLC inputs DI11-DI14.

### Modbus Connection Issues

```bash
# Test Modbus connection
python3 -c "from pymodbus.client import ModbusTcpClient; c = ModbusTcpClient('127.0.0.1'); print(c.connect())"
```

## Code Structure

### Classes

#### `LCD_I2C`
Generic I2C LCD driver for HD44780-based displays.
- Handles low-level I2C communication
- Supports 4-bit mode operation
- Methods: `write_line()`, `clear()`, `set_cursor()`

#### `ModbusReader`
Helper for reading/writing Modbus registers.
- Manages TCP connection
- Handles errors gracefully
- Returns None on failure

#### `Display1Manager`
Manages the 20x4 auto-rotating display.
- 4 rotating views
- Configurable update interval
- Background thread for auto-rotation

#### `Display2Manager`
Manages the 2x8 interactive display.
- 2 views (overview, zone selection)
- Modbus-based button reading from PLC (DI11-DI14 via MW64)
- Immediate display updates on button press

#### `AutoScheduler`
Handles scheduled auto-watering.
- Time-based triggering
- Condition checking
- Once-per-day execution

## Performance Considerations

### Update Intervals
- Display 1: 3-5 seconds between view rotations (default: 4s)
- Display 2: 100ms button polling
- Scheduler: 30-second check interval

### Modbus Efficiency
- Each display update requires 2-4 Modbus reads
- Connection timeout: 2 seconds
- Failed reads don't block operation

### Threading
- Display 1 runs in background thread
- Display 2 runs in background thread
- Scheduler runs in background thread
- All threads are daemon threads (exit with main program)

## Examples

### Programmatic Usage

```python
from display_manager import Display1Manager, Display2Manager, AutoScheduler

# Initialize Display 1
display1 = Display1Manager(
    i2c_addr=0x27,
    modbus_host="127.0.0.1",
    update_interval=4.0
)
display1.start()

# Initialize Display 2
display2 = Display2Manager(
    i2c_addr=0x3F,
    modbus_host="127.0.0.1"
)
display2.start()

# Initialize scheduler
scheduler = AutoScheduler(
    modbus_host="127.0.0.1",
    schedule_hour=1,
    schedule_minute=0
)
scheduler.start()

# Run until interrupted
try:
    import time
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    display1.stop()
    display2.stop()
    scheduler.stop()
```

### Button Reading

Buttons are automatically read from PLC via Modbus (MW64). No custom configuration needed.

```python
from display_manager import Display2Manager

# Display manager automatically reads buttons from MW64
display2 = Display2Manager(
    i2c_addr=0x3F,
    modbus_host="127.0.0.1",
    modbus_port=502
)
display2.start()
```

Button mapping (from forbindningstabell.csv):
- LEFT (DI11): Navigate/decrease zone
- RIGHT (DI12): Navigate/increase zone  
- OK (DI13): Confirm (hold >2s)
- BACK (DI14): Cancel/back to overview

## License

Part of the Fotbollsplan Bevattning system.

## Support

For issues or questions, please refer to the main project README or open an issue on GitHub.
