#!/usr/bin/env python3
"""
Display Manager for Fotbollsplan Bevattning
Manages two I2C LCD displays:
- Display 1 (D1): 20x4 without buttons - auto-rotating status views
- Display 2 (D2): 2x8 with 4 buttons - interactive manual control

Author: Fotbollsplan Bevattning System
"""

import time
import threading
import logging
from typing import Optional, Callable, Dict, Any
from datetime import datetime
from enum import IntEnum

try:
    import smbus2 as smbus
except ImportError:
    try:
        import smbus
    except ImportError:
        smbus = None

try:
    from pymodbus.client import ModbusTcpClient
except ImportError:
    try:
        from pymodbus.client.sync import ModbusTcpClient
    except ImportError:
        ModbusTcpClient = None

try:
    from pymodbus.exceptions import ModbusIOException, ConnectionException
except ImportError:
    ModbusIOException = ConnectionException = Exception


# Modbus register addresses (from existing system)
MW_REMOTE_CMD = 10
MW_STATUS_ZONE = 50
MW_STATUS_PUMP = 51
MW_STATUS_STEG = 52
MW_SELECTED_ZONE = 53
MW_FLOW_SWITCH = 55         # Flödesvakt status
MW_MODE_OVERRIDE = 60
MW_MANUAL_START = 61
MW_SET_SELECTED = 63
MW_MENU_BUTTONS = 64        # Menu buttons bitmask
MW_MANUAL_TIME = 65         # Manual runtime (minutes)
MW_SPECIAL_MODE = 66        # Special mode: 0=none, 1=Test, 2=Blow
MW_HEARTBEAT = 70
MW_HEARTBEAT_CNT = 71
MW_EVENTMASK = 72
MW_BLOCK_REASON = 73
MW_MARKFUKT = 30
MW_REGEN24 = 31
MW_TEMP = 32
MW_PRESSURE_SWITCH = 33      # Tryckvakt status (digital)
MW_MODE = 100                # Mode switch: 0=Neutral, 1=Lokalt läge, 2=Fjärrläge


logger = logging.getLogger("display_manager")
logger.setLevel(logging.DEBUG)
_console = logging.StreamHandler()
_console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
_console.setLevel(logging.INFO)
logger.addHandler(_console)


class BlockReason(IntEnum):
    """Block reasons from PLC"""
    OK = 0
    RAIN_THRESHOLD = 1
    MOISTURE_THRESHOLD = 2
    ANTI_COLLISION = 3
    E_STOP = 4


class Display1View(IntEnum):
    """Views for Display 1 (20x4)"""
    STATUS = 0
    BLOCK_CONDITIONS = 1
    PUMP_STATE = 2
    CONNECTIVITY = 3
    MODE_STATUS = 4


class Display2View(IntEnum):
    """Views for Display 2 (2x8)"""
    OVERVIEW = 0
    MODE_SELECT = 1      # Select mode: Auto/Manual/Test/Blow
    ZONE_SELECT = 2      # Select zone (for Manual/Test/Blow)
    TIME_SELECT = 3      # Select runtime (for Manual only)
    CONFIRM = 4          # Confirm and start


class LCD_I2C:
    """Generic I2C LCD driver for HD44780-based displays"""
    
    # LCD Commands
    LCD_CLEARDISPLAY = 0x01
    LCD_RETURNHOME = 0x02
    LCD_ENTRYMODESET = 0x04
    LCD_DISPLAYCONTROL = 0x08
    LCD_CURSORSHIFT = 0x10
    LCD_FUNCTIONSET = 0x20
    LCD_SETCGRAMADDR = 0x40
    LCD_SETDDRAMADDR = 0x80
    
    # Flags for display entry mode
    LCD_ENTRYRIGHT = 0x00
    LCD_ENTRYLEFT = 0x02
    LCD_ENTRYSHIFTINCREMENT = 0x01
    LCD_ENTRYSHIFTDECREMENT = 0x00
    
    # Flags for display on/off control
    LCD_DISPLAYON = 0x04
    LCD_DISPLAYOFF = 0x00
    LCD_CURSORON = 0x02
    LCD_CURSOROFF = 0x00
    LCD_BLINKON = 0x01
    LCD_BLINKOFF = 0x00
    
    # Flags for function set
    LCD_8BITMODE = 0x10
    LCD_4BITMODE = 0x00
    LCD_2LINE = 0x08
    LCD_1LINE = 0x00
    LCD_5x10DOTS = 0x04
    LCD_5x8DOTS = 0x00
    
    # Flags for backlight control
    LCD_BACKLIGHT = 0x08
    LCD_NOBACKLIGHT = 0x00
    
    En = 0b00000100  # Enable bit
    Rw = 0b00000010  # Read/Write bit
    Rs = 0b00000001  # Register select bit
    
    def __init__(self, i2c_addr: int, rows: int, cols: int, bus_num: int = 1):
        """
        Initialize LCD display
        
        Args:
            i2c_addr: I2C address of the display (e.g., 0x27 or 0x3F)
            rows: Number of rows (e.g., 2, 4)
            cols: Number of columns (e.g., 8, 16, 20)
            bus_num: I2C bus number (default: 1 for Raspberry Pi)
        """
        self.i2c_addr = i2c_addr
        self.rows = rows
        self.cols = cols
        self.bus_num = bus_num
        self.backlight_state = self.LCD_BACKLIGHT
        self.bus = None
        
        if smbus is None:
            raise RuntimeError("smbus/smbus2 library not available. Install with: pip install smbus2")
        
        self.bus = smbus.SMBus(bus_num)
        self._init_display()
    
    def _write_byte(self, data: int):
        """Write a byte to I2C bus"""
        try:
            self.bus.write_byte(self.i2c_addr, data)
        except Exception as e:
            logger.warning(f"I2C write error: {e}")
    
    def _write_nibble(self, data: int):
        """Write 4-bit nibble"""
        self._write_byte(data | self.backlight_state)
        self._write_byte(data | self.En | self.backlight_state)
        time.sleep(0.0005)
        self._write_byte(data & ~self.En | self.backlight_state)
        time.sleep(0.0001)
    
    def _write_byte_data(self, data: int, mode: int):
        """Write byte in 4-bit mode"""
        high_nibble = mode | (data & 0xF0)
        low_nibble = mode | ((data << 4) & 0xF0)
        self._write_nibble(high_nibble)
        self._write_nibble(low_nibble)
    
    def _init_display(self):
        """Initialize the display in 4-bit mode"""
        time.sleep(0.05)
        
        # Initialize in 4-bit mode
        self._write_nibble(0x30)
        time.sleep(0.005)
        self._write_nibble(0x30)
        time.sleep(0.0001)
        self._write_nibble(0x30)
        time.sleep(0.0001)
        self._write_nibble(0x20)
        time.sleep(0.0001)
        
        # Function set: 4-bit, 2 line, 5x8 dots
        self._write_byte_data(self.LCD_FUNCTIONSET | self.LCD_4BITMODE | self.LCD_2LINE | self.LCD_5x8DOTS, 0)
        
        # Display control: display on, cursor off, blink off
        self._write_byte_data(self.LCD_DISPLAYCONTROL | self.LCD_DISPLAYON | self.LCD_CURSOROFF | self.LCD_BLINKOFF, 0)
        
        # Clear display
        self.clear()
        
        # Entry mode: left to right
        self._write_byte_data(self.LCD_ENTRYMODESET | self.LCD_ENTRYLEFT | self.LCD_ENTRYSHIFTDECREMENT, 0)
        
        time.sleep(0.002)
    
    def clear(self):
        """Clear the display"""
        self._write_byte_data(self.LCD_CLEARDISPLAY, 0)
        time.sleep(0.002)
    
    def set_cursor(self, row: int, col: int):
        """Set cursor position"""
        row_offsets = [0x00, 0x40, 0x14, 0x54]
        if row >= self.rows:
            row = self.rows - 1
        self._write_byte_data(self.LCD_SETDDRAMADDR | (col + row_offsets[row]), 0)
    
    def write_string(self, text: str):
        """Write string at current cursor position"""
        for char in text:
            self._write_byte_data(ord(char), self.Rs)
    
    def write_line(self, row: int, text: str, align: str = 'left'):
        """
        Write text on a specific row
        
        Args:
            row: Row number (0-indexed)
            text: Text to write
            align: Alignment ('left', 'center', 'right')
        """
        # Truncate or pad text to fit
        if len(text) > self.cols:
            text = text[:self.cols]
        elif len(text) < self.cols:
            if align == 'center':
                padding = (self.cols - len(text)) // 2
                text = ' ' * padding + text
            elif align == 'right':
                text = text.rjust(self.cols)
        
        text = text.ljust(self.cols)  # Pad to clear rest of line
        self.set_cursor(row, 0)
        self.write_string(text)
    
    def backlight_on(self):
        """Turn backlight on"""
        self.backlight_state = self.LCD_BACKLIGHT
        self._write_byte(0)
    
    def backlight_off(self):
        """Turn backlight off"""
        self.backlight_state = self.LCD_NOBACKLIGHT
        self._write_byte(0)
    
    def close(self):
        """Close I2C bus connection"""
        if self.bus:
            try:
                self.bus.close()
            except Exception:
                pass


class ModbusReader:
    """Helper class to read Modbus registers with caching"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 502, unit: int = 1, cache_duration: float = 0.5):
        self.host = host
        self.port = port
        self.unit = unit
        self.cache_duration = cache_duration  # Cache duration in seconds
        self._cache = {}  # {(address, count): (data, timestamp)}
        self._client = None
        self._client_connected = False

    def _reset_client(self):
        """Close and reset Modbus client"""
        if self._client:
            try:
                self._client.close()
            except OSError as e:
                # Expected if socket already closed by remote end (e.g., EBADF/ENOTCONN)
                logger.debug(f"Expected OSError closing Modbus client: {e}")
            except Exception as e:
                logger.warning(f"Unexpected error closing Modbus client: {e}")
        self._client = None
        self._client_connected = False

    def _get_client(self):
        """Get or create a persistent Modbus client connection"""
        if ModbusTcpClient is None:
            logger.warning("pymodbus not available")
            return None

        if self._client is None:
            self._client = ModbusTcpClient(self.host, port=self.port, timeout=2)
            self._client_connected = False

        if not self._client_connected:
            try:
                if not self._client.connect():
                    logger.debug("Modbus connection failed")
                    self._reset_client()
                    return None
                self._client_connected = True
            except Exception as e:
                self._handle_modbus_exception(e, "Modbus connection")
                return None

        return self._client

    def _handle_modbus_exception(self, exc: Exception, context: str):
        """Shared Modbus exception handler with reset"""
        if isinstance(exc, (ConnectionException, ModbusIOException)):
            logger.debug(f"{context} {type(exc).__name__}: {exc}")
        else:
            logger.warning(f"Unexpected {context} {type(exc).__name__}: {exc}")
        self._reset_client()
    
    def _validate_result(self, result, address: int, context: str) -> bool:
        """Validate Modbus result and reset connection on errors"""
        if result is None:
            logger.debug(f"{context} error at {address}")
            self._reset_client()
            return False
        if hasattr(result, 'isError') and result.isError():
            logger.debug(f"{context} error at {address}")
            self._reset_client()
            return False
        return True
    
    def _invalidate_cache_for_address(self, address: int):
        """Remove cached entries that overlap the given register address"""
        # k[0] = start address, k[1] = count; remove any cache entry whose range overlaps the target address
        for key in list(self._cache.keys()):
            if key[0] <= address <= key[0] + key[1] - 1:
                del self._cache[key]
    
    def close(self):
        """Public close to release persistent Modbus connection"""
        self._reset_client()
    
    def read_registers(self, address: int, count: int = 1, use_cache: bool = True) -> Optional[list]:
        """Read holding registers from Modbus with optional caching"""
        cache_key = (address, count)
        
        # Check cache if enabled
        if use_cache and cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            age = time.time() - timestamp
            if age < self.cache_duration:
                logger.debug(f"Using cached Modbus data for addr {address} (age: {age:.3f}s)")
                return cached_data
        
        client = self._get_client()
        if client is None:
            return None
        try:
            result = client.read_holding_registers(address, count, unit=self.unit)
            
            if not self._validate_result(result, address, "Modbus read"):
                return None
            
            data = result.registers
            
            # Update cache
            if use_cache:
                self._cache[cache_key] = (data, time.time())
            
            return data
        except Exception as e:
            self._handle_modbus_exception(e, "Modbus read")
            return None
    
    def clear_cache(self):
        """Clear the Modbus cache"""
        self._cache.clear()
    
    def write_register(self, address: int, value: int) -> bool:
        """Write single holding register to Modbus"""
        client = self._get_client()
        if client is None:
            return False
        try:
            result = client.write_register(address, int(value), unit=self.unit)
            
            if not self._validate_result(result, address, "Modbus write"):
                return False
            
            # Invalidate cache for this register
            self._invalidate_cache_for_address(address)
            
            return True
        except Exception as e:
            self._handle_modbus_exception(e, "Modbus write")
            return False


class Display1Manager:
    """
    Manages Display 1: 20x4 LCD with auto-rotating views
    Views cycle automatically every 3-5 seconds
    """
    
    def __init__(self, i2c_addr: int = 0x27, modbus_host: str = "127.0.0.1",
                 modbus_port: int = 502, update_interval: float = 4.0):
        """
        Initialize Display 1 Manager
        
        Args:
            i2c_addr: I2C address of the 20x4 display
            modbus_host: Modbus TCP host
            modbus_port: Modbus TCP port
            update_interval: Seconds between view updates (3-5 recommended)
        """
        self.lcd = LCD_I2C(i2c_addr, rows=4, cols=20)
        self.modbus = ModbusReader(modbus_host, modbus_port)
        self.update_interval = update_interval
        self.current_view = Display1View.STATUS
        self.running = False
        self.thread = None
        self.last_data = {}
    
    def get_system_status(self) -> Dict[str, Any]:
        """Read current system status from Modbus"""
        status = {
            'zone': 0,
            'pump_on': False,
            'steg': 0,
            'selected_zone': 0,
            'mode': 'Manual',
            'switch_mode': 0,
            'switch_mode_text': 'Inget läge valt',
            'heartbeat': 0,
            'heartbeat_cnt': 0,
            'eventmask': 0,
            'block_reason': BlockReason.OK,
            'moisture': 0,
            'rain': 0,
            'temp': 0,
            'modbus_ok': False,
            'timestamp': datetime.now()
        }
        
        # Read status registers
        status_regs = self.modbus.read_registers(MW_STATUS_ZONE, 4)
        if status_regs:
            status['zone'] = status_regs[0]
            status['pump_on'] = status_regs[1] == 1
            status['steg'] = status_regs[2]
            status['selected_zone'] = status_regs[3]
            status['modbus_ok'] = True
        
        # Read mode
        mode_reg = self.modbus.read_registers(MW_MODE_OVERRIDE, 1)
        if mode_reg:
            status['mode'] = 'Auto' if mode_reg[0] == 1 else 'Manual'
        
        # Read switch mode (MW100)
        switch_mode_reg = self.modbus.read_registers(MW_MODE, 1)
        if switch_mode_reg:
            mode_val = switch_mode_reg[0]
            status['switch_mode'] = mode_val
            if mode_val == 1:
                status['switch_mode_text'] = 'Lokalt läge aktivt'
            elif mode_val == 2:
                status['switch_mode_text'] = 'Fjärrläge aktivt'
            else:
                status['switch_mode_text'] = 'Inget läge valt'
        
        # Read heartbeat and event info
        hb_regs = self.modbus.read_registers(MW_HEARTBEAT, 4)
        if hb_regs:
            status['heartbeat'] = hb_regs[0]
            status['heartbeat_cnt'] = hb_regs[1]
            status['eventmask'] = hb_regs[2]
            status['block_reason'] = BlockReason(hb_regs[3])
        
        # Read environmental data
        env_regs = self.modbus.read_registers(MW_MARKFUKT, 3)
        if env_regs:
            status['moisture'] = env_regs[0]
            status['rain'] = env_regs[1]
            status['temp'] = env_regs[2]
        
        return status
    
    def _render_status_view(self, status: Dict[str, Any]):
        """Render main status view (20x4)"""
        # Line 0: Mode, Zone, Pump
        mode_str = status['mode']
        zone_str = f"Z:{status['selected_zone']}/{status['zone']}"
        pump_str = "PUMP:ON " if status['pump_on'] else "PUMP:OFF"
        line0 = f"{mode_str:6} {zone_str:6} {pump_str:7}"
        
        # Line 1: Stage and heartbeat
        steg_str = f"Stage:{status['steg']}"
        hb_indicator = "*" if (status['heartbeat_cnt'] % 2) == 0 else " "
        line1 = f"{steg_str:15} HB:{hb_indicator}"
        
        # Line 2: Environmental conditions
        line2 = f"T:{status['temp']:2}C M:{status['moisture']:2}% R:{status['rain']:2}mm"
        
        # Line 3: Block status
        block = status['block_reason']
        if block == BlockReason.OK:
            line3 = "Status: OK"
        elif block == BlockReason.RAIN_THRESHOLD:
            line3 = "Block: Rain"
        elif block == BlockReason.MOISTURE_THRESHOLD:
            line3 = "Block: Moisture"
        elif block == BlockReason.ANTI_COLLISION:
            line3 = "Block: Anti-Coll"
        elif block == BlockReason.E_STOP:
            line3 = "EMERGENCY STOP!"
        else:
            line3 = f"Block: {block}"
        
        self.lcd.write_line(0, line0)
        self.lcd.write_line(1, line1)
        self.lcd.write_line(2, line2)
        self.lcd.write_line(3, line3)
    
    def _render_block_conditions_view(self, status: Dict[str, Any]):
        """Render block conditions view"""
        self.lcd.write_line(0, "BLOCK CONDITIONS", align='center')
        self.lcd.write_line(1, f"Moisture: {status['moisture']:3}%")
        self.lcd.write_line(2, f"Rain 24h: {status['rain']:3}mm")
        self.lcd.write_line(3, f"Reason: {status['block_reason'].name}")
    
    def _render_pump_state_view(self, status: Dict[str, Any]):
        """Render pump state view"""
        self.lcd.write_line(0, "PUMP STATE", align='center')
        pump_status = "ON " if status['pump_on'] else "OFF"
        self.lcd.write_line(1, f"Status: {pump_status}")
        self.lcd.write_line(2, f"Current Zone: {status['zone']}")
        self.lcd.write_line(3, f"Stage: {status['steg']}")
    
    def _render_connectivity_view(self, status: Dict[str, Any]):
        """Render Modbus/connectivity view"""
        self.lcd.write_line(0, "CONNECTIVITY", align='center')
        modbus_status = "OK " if status['modbus_ok'] else "FAIL"
        self.lcd.write_line(1, f"Modbus: {modbus_status}")
        self.lcd.write_line(2, f"Heartbeat: {status['heartbeat_cnt']}")
        now = status['timestamp'].strftime("%H:%M:%S")
        self.lcd.write_line(3, f"Time: {now}")
    
    def _render_mode_status_view(self, status: Dict[str, Any]):
        """Render mode status view (Lokal/Fjärr-styrning)"""
        self.lcd.write_line(0, "STYRNINGSLÄGE", align='center')
        self.lcd.write_line(1, "", align='center')
        self.lcd.write_line(2, status['switch_mode_text'], align='center')
        self.lcd.write_line(3, "", align='center')
    
    def update_display(self):
        """Update display with current view"""
        try:
            status = self.get_system_status()
            
            if self.current_view == Display1View.STATUS:
                self._render_status_view(status)
            elif self.current_view == Display1View.BLOCK_CONDITIONS:
                self._render_block_conditions_view(status)
            elif self.current_view == Display1View.PUMP_STATE:
                self._render_pump_state_view(status)
            elif self.current_view == Display1View.CONNECTIVITY:
                self._render_connectivity_view(status)
            elif self.current_view == Display1View.MODE_STATUS:
                self._render_mode_status_view(status)
            
            self.last_data = status
        except Exception as e:
            logger.error(f"Error updating Display 1: {e}")
    
    def _rotation_loop(self):
        """Background thread for auto-rotating views"""
        view_count = 5  # Updated to include MODE_STATUS view
        while self.running:
            try:
                self.update_display()
                time.sleep(self.update_interval)
                
                # Rotate to next view
                self.current_view = Display1View((self.current_view + 1) % view_count)
            except Exception as e:
                logger.error(f"Error in Display 1 rotation loop: {e}")
                time.sleep(1)
    
    def start(self):
        """Start auto-rotation"""
        if not self.running:
            logger.info("Starting Display 1 auto-rotation")
            self.running = True
            self.thread = threading.Thread(target=self._rotation_loop, daemon=True)
            self.thread.start()
    
    def stop(self):
        """Stop auto-rotation"""
        if self.running:
            logger.info("Stopping Display 1")
            self.running = False
            if self.thread:
                self.thread.join(timeout=2)
            self.lcd.clear()
            self.lcd.close()
            self.modbus.close()


class Display2Manager:
    """
    Manages Display 2: 2x8 LCD with 4 buttons (Up, Down, Left, Right)
    Interactive manual control interface with complete menu system
    """
    
    # Mode constants
    MODE_AUTO = 0
    MODE_MANUAL = 1
    MODE_TEST = 2
    MODE_BLOW = 3
    
    MODE_NAMES = ["Auto", "Manual", "Test", "Blow"]
    MODE_ABBR = ["A", "M", "T", "B"]
    
    def __init__(self, i2c_addr: int = 0x3F, modbus_host: str = "127.0.0.1",
                 modbus_port: int = 502, button_pins: Dict[str, int] = None):
        """
        Initialize Display 2 Manager
        
        Args:
            i2c_addr: I2C address of the 2x8 display
            modbus_host: Modbus TCP host
            modbus_port: Modbus TCP port
            button_pins: DEPRECATED - Buttons now read from PLC via Modbus (DI11-DI14)
        """
        self.lcd = LCD_I2C(i2c_addr, rows=2, cols=8)
        self.modbus = ModbusReader(modbus_host, modbus_port)
        self.current_view = Display2View.OVERVIEW
        
        # Selection state
        self.selected_mode = 0      # 0=Auto, 1=Manual, 2=Test, 3=Blow
        self.selected_zone = 1      # 1-7
        self.selected_time = 15     # minutes (1-240)
        
        self.running = False
        self.thread = None
        
        # Hold-to-confirm for OK button on CONFIRM view
        self.button_hold_start = None
        self.hold_duration = 2.0  # 2 seconds for OK button long press on CONFIRM view
        self.confirmed = False
        
        # Button state tracking for edge detection
        self.prev_buttons = {'left': False, 'right': False, 'ok': False, 'back': False}
        
        logger.info("Display 2 Manager initialized - buttons read from Modbus MW64 (DI11-DI14)")
    
    def read_buttons(self) -> Dict[str, bool]:
        """
        Read current state of all buttons from Modbus register MW64
        MW64 bitmask: bit0=Left (DI11), bit1=Right (DI12), bit2=OK (DI13), bit3=Back (DI14)
        """
        buttons = {'left': False, 'right': False, 'ok': False, 'back': False}
        
        try:
            # Read menu buttons register from PLC
            reg_value = self.modbus.read_register(MW_MENU_BUTTONS)
            if reg_value is not None:
                # Extract button states from bitmask
                buttons['left'] = bool(reg_value & 0x01)
                buttons['right'] = bool(reg_value & 0x02)
                buttons['ok'] = bool(reg_value & 0x04)
                buttons['back'] = bool(reg_value & 0x08)
        except Exception as e:
            logger.warning(f"Error reading menu buttons from Modbus: {e}")
        
        return buttons
    
    def handle_button_press(self, button: str, is_held: bool = False):
        """Handle button press event with new menu workflow
        
        Workflow:
        OVERVIEW -> MODE_SELECT -> ZONE_SELECT -> TIME_SELECT (if Manual) -> CONFIRM -> Execute
        
        Button mapping:
        - Left (DI11): Decrease value / Previous
        - Right (DI12): Increase value / Next
        - OK (DI13): Confirm and advance (hold >2s on CONFIRM to execute)
        - Back (DI14): Go back / Cancel
        """
        logger.debug(f"Button {'held' if is_held else 'pressed'}: {button}")
        
        if button == 'back':
            # Back button: go to previous view or cancel to overview
            if self.current_view == Display2View.OVERVIEW:
                pass  # Already at overview
            elif self.current_view == Display2View.MODE_SELECT:
                self.current_view = Display2View.OVERVIEW
            elif self.current_view == Display2View.ZONE_SELECT:
                self.current_view = Display2View.MODE_SELECT
            elif self.current_view == Display2View.TIME_SELECT:
                self.current_view = Display2View.ZONE_SELECT
            elif self.current_view == Display2View.CONFIRM:
                # Go back based on mode
                if self.selected_mode == self.MODE_AUTO:  # Auto - go back to mode selection
                    self.current_view = Display2View.MODE_SELECT
                elif self.selected_mode == self.MODE_MANUAL:  # Manual - go back to time
                    self.current_view = Display2View.TIME_SELECT
                else:  # Test/Blow - go back to zone
                    self.current_view = Display2View.ZONE_SELECT
            self.confirmed = False
            
        elif button == 'ok':
            # OK button: confirm and advance
            if self.current_view == Display2View.OVERVIEW:
                # Enter menu system
                self.current_view = Display2View.MODE_SELECT
                self.confirmed = False
                
            elif self.current_view == Display2View.MODE_SELECT:
                # Advance based on mode
                if self.selected_mode == self.MODE_AUTO:  # Auto - skip zone selection, go to confirm
                    self.current_view = Display2View.CONFIRM
                else:  # Manual/Test/Blow - need zone selection
                    self.current_view = Display2View.ZONE_SELECT
                
            elif self.current_view == Display2View.ZONE_SELECT:
                # Advance based on mode
                if self.selected_mode == self.MODE_MANUAL:  # Manual - needs time selection
                    self.current_view = Display2View.TIME_SELECT
                else:  # Auto/Test/Blow - go to confirm
                    self.current_view = Display2View.CONFIRM
                    
            elif self.current_view == Display2View.TIME_SELECT:
                # Advance to confirm
                self.current_view = Display2View.CONFIRM
                
            elif self.current_view == Display2View.CONFIRM:
                if is_held:
                    # Long press on CONFIRM - execute!
                    self._execute_selection()
                    self.current_view = Display2View.OVERVIEW
                    
        elif button == 'left':
            # Decrease value
            if self.current_view == Display2View.MODE_SELECT:
                # Cycle modes: Auto(0) <- Manual(1) <- Test(2) <- Blow(3)
                self.selected_mode = (self.selected_mode - 1) % 4
            elif self.current_view == Display2View.ZONE_SELECT:
                # Decrease zone: 7 <- 1 <- 2 <- ...
                self.selected_zone = ((self.selected_zone - 2) % 7) + 1
            elif self.current_view == Display2View.TIME_SELECT:
                # Decrease time by 1 minute (min 1)
                self.selected_time = max(1, self.selected_time - 1)
                
        elif button == 'right':
            # Increase value
            if self.current_view == Display2View.MODE_SELECT:
                # Cycle modes: Auto(0) -> Manual(1) -> Test(2) -> Blow(3)
                self.selected_mode = (self.selected_mode + 1) % 4
            elif self.current_view == Display2View.ZONE_SELECT:
                # Increase zone: 1 -> 2 -> ... -> 7 -> 1
                self.selected_zone = (self.selected_zone % 7) + 1
            elif self.current_view == Display2View.TIME_SELECT:
                # Increase time by 1 minute (max 240)
                self.selected_time = min(240, self.selected_time + 1)
        
        # Update display immediately
        self.update_display()
    
    def _execute_selection(self):
        """Execute the confirmed selection by writing to PLC"""
        logger.info(f"Executing: Mode={self.selected_mode}, Zone={self.selected_zone}, Time={self.selected_time}")
        logger.info(f"Starting {self.MODE_NAMES[self.selected_mode]} mode")
        
        if self.selected_mode == self.MODE_AUTO:
            # Auto mode - set mode and trigger remote command
            self.modbus.write_register(MW_MODE_OVERRIDE, 1)  # Auto
            self.modbus.write_register(MW_REMOTE_CMD, 50)  # Auto start command
            
        elif self.selected_mode == self.MODE_MANUAL:
            # Manual mode - set zone, time, mode, and pulse start
            self.modbus.write_register(MW_SET_SELECTED, self.selected_zone)
            self.modbus.write_register(MW_MANUAL_TIME, self.selected_time)
            self.modbus.write_register(MW_MODE_OVERRIDE, 0)  # Manual
            self.modbus.write_register(MW_MANUAL_START, 1)  # Pulse start
            
        elif self.selected_mode == self.MODE_TEST:
            # Test mode - set zone and trigger test
            self.modbus.write_register(MW_SET_SELECTED, self.selected_zone)
            self.modbus.write_register(MW_SPECIAL_MODE, 1)  # Test trigger
            
        elif self.selected_mode == self.MODE_BLOW:
            # Blow mode - set zone and trigger blow
            self.modbus.write_register(MW_SET_SELECTED, self.selected_zone)
            self.modbus.write_register(MW_SPECIAL_MODE, 2)  # Blow trigger
    
    def _render_overview(self):
        """Render overview view (2x8)"""
        # Read current status
        status_regs = self.modbus.read_registers(MW_STATUS_ZONE, 4)
        mode_reg = self.modbus.read_registers(MW_MODE_OVERRIDE, 1)
        
        zone = status_regs[0] if status_regs else 0
        pump_on = (status_regs[1] == 1) if status_regs else False
        mode = "A" if (mode_reg and mode_reg[0] == 1) else "M"
        
        # Line 0: Mode and Zone
        line0 = f"{mode} Z:{zone}"
        # Line 1: Pump status / Press OK to enter menu
        if pump_on:
            line1 = "P:ON"
        else:
            line1 = "OK:Menu"
        
        self.lcd.write_line(0, line0)
        self.lcd.write_line(1, line1)
    
    def _render_mode_select(self):
        """Render mode selection view"""
        # Line 0: Label
        line0 = "Mode"
        # Line 1: Current selection
        line1 = self.MODE_NAMES[self.selected_mode]
        
        self.lcd.write_line(0, line0, align='center')
        self.lcd.write_line(1, line1, align='center')
    
    def _render_zone_select(self):
        """Render zone selection view"""
        # Line 0: Label
        line0 = "Zone"
        # Line 1: Selected zone
        line1 = f"  {self.selected_zone}"
        
        self.lcd.write_line(0, line0, align='center')
        self.lcd.write_line(1, line1)
    
    def _render_time_select(self):
        """Render time selection view (Manual mode only)"""
        # Line 0: Label
        line0 = "Time"
        # Line 1: Selected time
        line1 = f"{self.selected_time:3d}min"
        
        self.lcd.write_line(0, line0, align='center')
        self.lcd.write_line(1, line1, align='center')
    
    def _render_confirm(self):
        """Render confirmation view"""
        # Line 0: Mode abbreviation + Zone (+ Time for Manual)
        if self.selected_mode == self.MODE_MANUAL:
            line0 = f"{self.MODE_ABBR[self.selected_mode]} Z{self.selected_zone} {self.selected_time}m"
        elif self.selected_mode == self.MODE_AUTO:
            line0 = f"{self.MODE_ABBR[self.selected_mode]} All"
        else:  # Test/Blow
            line0 = f"{self.MODE_ABBR[self.selected_mode]} Z{self.selected_zone}"
        
        # Line 1: Hold OK to start
        line1 = "Hold OK"
        
        self.lcd.write_line(0, line0, align='center')
        self.lcd.write_line(1, line1, align='center')
    
    def update_display(self):
        """Update display based on current view"""
        try:
            if self.current_view == Display2View.OVERVIEW:
                self._render_overview()
            elif self.current_view == Display2View.MODE_SELECT:
                self._render_mode_select()
            elif self.current_view == Display2View.ZONE_SELECT:
                self._render_zone_select()
            elif self.current_view == Display2View.TIME_SELECT:
                self._render_time_select()
            elif self.current_view == Display2View.CONFIRM:
                self._render_confirm()
        except Exception as e:
            logger.error(f"Error updating Display 2: {e}")
    
    def start_manual_irrigation(self):
        """Start manual irrigation with selected zone (time determined by auto mode settings)"""
        logger.info(f"Starting manual irrigation: Zone {self.selected_zone}")
        
        # Write selected zone
        self.modbus.write_register(MW_SET_SELECTED, self.selected_zone)
        
        # Pulse manual start
        self.modbus.write_register(MW_MANUAL_START, 1)
        
        # Return to overview
        self.current_view = Display2View.OVERVIEW
        self.update_display()
    
    def _update_loop(self):
        """Background thread for button handling and display updates"""
        last_buttons = {'left': False, 'right': False, 'ok': False, 'back': False}
        button_hold_timers = {'left': False, 'right': False, 'ok': False, 'back': False}
        update_counter = 0
        display_update_interval = 10  # Update display every 10 cycles (1 second)
        
        while self.running:
            try:
                # Read buttons from Modbus
                buttons = self.read_buttons()
                
                # Handle button state changes and hold detection
                button_pressed = False
                for name, pressed in buttons.items():
                    # Detect button press (edge detection: was off, now on)
                    if pressed and not last_buttons[name]:
                        # Button just pressed
                        self.handle_button_press(name, is_held=False)
                        button_pressed = True
                        button_hold_timers[name] = time.time()
                    elif pressed and last_buttons[name]:
                        # Button is being held
                        if button_hold_timers[name] and name == 'ok':
                            hold_time = time.time() - button_hold_timers[name]
                            if hold_time >= self.hold_duration:
                                # OK button held for required duration (>2s for confirmation)
                                self.handle_button_press(name, is_held=True)
                                button_hold_timers[name] = None  # Prevent repeated triggers
                                button_pressed = True
                    elif not pressed and last_buttons[name]:
                        # Button released
                        button_hold_timers[name] = None
                
                last_buttons = buttons.copy()
                
                # Update display only periodically or when button pressed
                update_counter += 1
                if button_pressed or update_counter >= display_update_interval:
                    self.update_display()
                    update_counter = 0
                
                time.sleep(0.1)  # 100ms polling rate for responsive button handling
            except Exception as e:
                logger.error(f"Error in Display 2 update loop: {e}")
                time.sleep(1)
    
    def start(self):
        """Start display and button handling"""
        if not self.running:
            logger.info("Starting Display 2")
            self.running = True
            self.thread = threading.Thread(target=self._update_loop, daemon=True)
            self.thread.start()
    
    def stop(self):
        """Stop display and button handling"""
        if self.running:
            logger.info("Stopping Display 2")
            self.running = False
            if self.thread:
                self.thread.join(timeout=2)
            self.lcd.clear()
            self.lcd.close()
            self.modbus.close()


class AutoModeTransitionScheduler:
    """
    Scheduler for transitioning to auto mode at 21:00 daily.
    Does NOT trigger watering - only sets mode to auto passively.
    If a sequence is running, waits until it completes.
    """
    
    # Constants
    MAX_WAIT_HOURS = 4
    CHECK_INTERVAL_SECONDS = 30
    LOG_INTERVAL_CYCLES = 10  # Log every 5 minutes (10 * 30 seconds)
    
    def __init__(self, modbus_host: str = "127.0.0.1", modbus_port: int = 502,
                 transition_hour: int = 21, transition_minute: int = 0):
        """
        Initialize Auto Mode Transition Scheduler
        
        Args:
            modbus_host: Modbus TCP host
            modbus_port: Modbus TCP port
            transition_hour: Hour to transition (0-23), default 21 for 21:00
            transition_minute: Minute to transition (0-59)
        """
        self.modbus = ModbusReader(modbus_host, modbus_port)
        self.transition_hour = transition_hour
        self.transition_minute = transition_minute
        self.running = False
        self.thread = None
        self.last_transition_date = None
    
    def is_sequence_running(self) -> bool:
        """Check if a sequence is currently running"""
        # Read Status_Steg (MW52) - if non-zero, sequence is running
        steg_regs = self.modbus.read_registers(MW_STATUS_STEG, 1)
        if steg_regs:
            return steg_regs[0] != 0
        return False
    
    def transition_to_auto_mode(self):
        """Passively transition to auto mode without triggering watering"""
        logger.info("Transitioning to auto mode (passive, no watering trigger)")
        
        # Check if sequence is running
        if self.is_sequence_running():
            logger.info("Sequence currently running, waiting for completion before transitioning...")
            # Wait for sequence to complete (check every 30 seconds, max wait time based on MAX_WAIT_HOURS)
            max_wait_cycles = (self.MAX_WAIT_HOURS * 60 * 60) // self.CHECK_INTERVAL_SECONDS
            for i in range(max_wait_cycles):
                time.sleep(self.CHECK_INTERVAL_SECONDS)
                if not self.is_sequence_running():
                    logger.info("Sequence completed, now transitioning to auto mode")
                    break
                if i % self.LOG_INTERVAL_CYCLES == 0:  # Log every 5 minutes
                    logger.debug("Still waiting for sequence to complete...")
        
        # Set mode to auto (MW60 = 1)
        success = self.modbus.write_register(MW_MODE_OVERRIDE, 1)
        if success:
            logger.info("Successfully transitioned to auto mode at 21:00")
        else:
            logger.error("Failed to write auto mode to Modbus")
    
    def _scheduler_loop(self):
        """Background scheduler loop for 21:00 transition"""
        while self.running:
            try:
                now = datetime.now()
                current_date = now.date()
                current_hour = now.hour
                current_minute = now.minute
                
                # Check if it's time to transition and we haven't transitioned today
                if (current_hour == self.transition_hour and 
                    current_minute == self.transition_minute and
                    current_date != self.last_transition_date):
                    
                    logger.info(f"Auto mode transition time reached: {self.transition_hour:02d}:{self.transition_minute:02d}")
                    self.transition_to_auto_mode()
                    self.last_transition_date = current_date
                
                # Sleep for check interval before next check
                time.sleep(self.CHECK_INTERVAL_SECONDS)
            except Exception as e:
                logger.error(f"Error in auto mode transition scheduler loop: {e}")
                time.sleep(60)
    
    def start(self):
        """Start the auto mode transition scheduler"""
        if not self.running:
            logger.info(f"Starting auto mode transition scheduler (transition at {self.transition_hour:02d}:{self.transition_minute:02d})")
            self.running = True
            self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self.thread.start()
    
    def stop(self):
        """Stop the auto mode transition scheduler"""
        if self.running:
            logger.info("Stopping auto mode transition scheduler")
            self.running = False
            if self.thread:
                self.thread.join(timeout=2)


class AutoScheduler:
    """
    Scheduler for auto-mode watering at 01:00
    Checks conditions before triggering
    """
    
    def __init__(self, modbus_host: str = "127.0.0.1", modbus_port: int = 502,
                 schedule_hour: int = 1, schedule_minute: int = 0):
        """
        Initialize Auto Scheduler
        
        Args:
            modbus_host: Modbus TCP host
            modbus_port: Modbus TCP port
            schedule_hour: Hour to trigger (0-23)
            schedule_minute: Minute to trigger (0-59)
        """
        self.modbus = ModbusReader(modbus_host, modbus_port)
        self.schedule_hour = schedule_hour
        self.schedule_minute = schedule_minute
        self.running = False
        self.thread = None
        self.last_trigger_date = None
    
    def check_conditions(self) -> tuple[bool, str]:
        """
        Check if conditions allow auto-watering
        
        Returns:
            (allowed, reason) tuple
        """
        # Read block reason
        block_regs = self.modbus.read_registers(MW_BLOCK_REASON, 1)
        if not block_regs:
            return False, "Modbus communication failed"
        
        block_reason = BlockReason(block_regs[0])
        
        if block_reason == BlockReason.OK:
            return True, "Conditions OK"
        elif block_reason == BlockReason.RAIN_THRESHOLD:
            return False, "Rain threshold exceeded"
        elif block_reason == BlockReason.MOISTURE_THRESHOLD:
            return False, "Moisture threshold exceeded"
        elif block_reason == BlockReason.ANTI_COLLISION:
            return False, "System busy"
        elif block_reason == BlockReason.E_STOP:
            return False, "Emergency stop active"
        else:
            return False, f"Unknown block reason: {block_reason}"
    
    def trigger_auto_watering(self):
        """Trigger auto-watering by pulsing Remote_Command"""
        logger.info("Triggering auto-watering")
        
        # Set mode to auto
        self.modbus.write_register(MW_MODE_OVERRIDE, 1)
        
        # Pulse Remote_Command (MW10 = 50)
        self.modbus.write_register(10, 50)  # MW_REMOTE_CMD
        time.sleep(1)
        self.modbus.write_register(10, 0)
        
        logger.info("Auto-watering triggered")
    
    def _scheduler_loop(self):
        """Background scheduler loop"""
        while self.running:
            try:
                now = datetime.now()
                current_date = now.date()
                current_hour = now.hour
                current_minute = now.minute
                
                # Check if it's time to trigger and we haven't triggered today
                if (current_hour == self.schedule_hour and 
                    current_minute == self.schedule_minute and
                    current_date != self.last_trigger_date):
                    
                    logger.info(f"Schedule time reached: {self.schedule_hour:02d}:{self.schedule_minute:02d}")
                    
                    # Check conditions
                    allowed, reason = self.check_conditions()
                    logger.info(f"Condition check: {reason}")
                    
                    if allowed:
                        self.trigger_auto_watering()
                        self.last_trigger_date = current_date
                    else:
                        logger.warning(f"Auto-watering blocked: {reason}")
                        self.last_trigger_date = current_date  # Mark as attempted
                
                # Sleep for 30 seconds before next check
                time.sleep(30)
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)
    
    def start(self):
        """Start the scheduler"""
        if not self.running:
            logger.info(f"Starting auto-scheduler (trigger at {self.schedule_hour:02d}:{self.schedule_minute:02d})")
            self.running = True
            self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self.thread.start()
    
    def stop(self):
        """Stop the scheduler"""
        if self.running:
            logger.info("Stopping scheduler")
            self.running = False
            if self.thread:
                self.thread.join(timeout=2)


def main():
    """Example main function demonstrating display usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Display Manager for Fotbollsplan Bevattning")
    parser.add_argument("--d1-addr", type=lambda x: int(x, 0), default=0x27,
                        help="I2C address for Display 1 (20x4)")
    parser.add_argument("--d2-addr", type=lambda x: int(x, 0), default=0x3F,
                        help="I2C address for Display 2 (2x8)")
    parser.add_argument("--modbus-host", default="127.0.0.1",
                        help="Modbus TCP host")
    parser.add_argument("--modbus-port", type=int, default=502,
                        help="Modbus TCP port")
    parser.add_argument("--d1-interval", type=float, default=4.0,
                        help="Display 1 update interval (seconds)")
    parser.add_argument("--enable-scheduler", action="store_true",
                        help="Enable auto-watering scheduler")
    parser.add_argument("--schedule-hour", type=int, default=1,
                        help="Hour for auto-watering (0-23)")
    parser.add_argument("--schedule-minute", type=int, default=0,
                        help="Minute for auto-watering (0-59)")
    parser.add_argument("--enable-auto-mode-transition", action="store_true",
                        help="Enable 21:00 auto mode transition")
    parser.add_argument("--transition-hour", type=int, default=21,
                        help="Hour for auto mode transition (0-23, default: 21)")
    parser.add_argument("--transition-minute", type=int, default=0,
                        help="Minute for auto mode transition (0-59)")
    parser.add_argument("--simulate", action="store_true",
                        help="Simulate without I2C hardware")
    
    args = parser.parse_args()
    
    display1 = None
    display2 = None
    scheduler = None
    auto_mode_scheduler = None
    
    try:
        if not args.simulate:
            # Initialize Display 1
            logger.info("Initializing Display 1 (20x4)...")
            display1 = Display1Manager(
                i2c_addr=args.d1_addr,
                modbus_host=args.modbus_host,
                modbus_port=args.modbus_port,
                update_interval=args.d1_interval
            )
            display1.start()
            
            # Initialize Display 2
            logger.info("Initializing Display 2 (2x8)...")
            display2 = Display2Manager(
                i2c_addr=args.d2_addr,
                modbus_host=args.modbus_host,
                modbus_port=args.modbus_port
            )
            display2.start()
        else:
            logger.info("Running in simulation mode (no I2C)")
        
        # Initialize scheduler if enabled
        if args.enable_scheduler:
            logger.info("Initializing auto-watering scheduler...")
            scheduler = AutoScheduler(
                modbus_host=args.modbus_host,
                modbus_port=args.modbus_port,
                schedule_hour=args.schedule_hour,
                schedule_minute=args.schedule_minute
            )
            scheduler.start()
        
        # Initialize auto mode transition scheduler if enabled
        if args.enable_auto_mode_transition:
            logger.info("Initializing auto mode transition scheduler (21:00)...")
            auto_mode_scheduler = AutoModeTransitionScheduler(
                modbus_host=args.modbus_host,
                modbus_port=args.modbus_port,
                transition_hour=args.transition_hour,
                transition_minute=args.transition_minute
            )
            auto_mode_scheduler.start()
        
        logger.info("Display manager running. Press Ctrl+C to exit.")
        
        # Keep running
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.exception(f"Error: {e}")
    finally:
        if display1:
            display1.stop()
        if display2:
            display2.stop()
        if scheduler:
            scheduler.stop()
        if auto_mode_scheduler:
            auto_mode_scheduler.stop()


if __name__ == "__main__":
    main()
