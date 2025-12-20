#!/usr/bin/env python3
"""
Test and simulation script for Display Manager
Tests display functionality without requiring actual I2C hardware
"""

import time
import logging
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)

logger = logging.getLogger("test_display")


class MockSMBus:
    """Mock SMBus for testing without I2C hardware"""
    
    def __init__(self, bus_num):
        self.bus_num = bus_num
        logger.info(f"MockSMBus initialized on bus {bus_num}")
    
    def write_byte(self, addr, data):
        # Simulate successful write
        pass
    
    def close(self):
        pass


class MockSMBusModule:
    """Mock smbus module"""
    SMBus = MockSMBus


class MockModbusClient:
    """Mock Modbus client for testing"""
    
    def __init__(self, host, port=502, timeout=2):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.connected = False
        
        # Simulated register values
        self.registers = {
            50: 2,    # Current zone
            51: 1,    # Pump on
            52: 3,    # Stage
            53: 2,    # Selected zone
            55: 1,    # Flow switch (1=flow OK)
            60: 1,    # Mode (1=Auto)
            61: 0,    # Manual start
            63: 0,    # Set selected zone
            64: 0,    # Menu buttons (bitmask)
            65: 15,   # Manual runtime (minutes)
            66: 0,    # Special mode (0=none, 1=Test, 2=Blow)
            70: 1,    # Heartbeat bit
            71: 123,  # Heartbeat counter
            72: 0,    # Event mask
            73: 0,    # Block reason (0=OK)
            30: 45,   # Moisture
            31: 2,    # Rain 24h
            32: 18,   # Temperature
            33: 75,   # Pressure
        }
    
    def connect(self):
        self.connected = True
        logger.debug(f"MockModbus connected to {self.host}:{self.port}")
        return True
    
    def close(self):
        self.connected = False
        logger.debug("MockModbus closed")
    
    def read_holding_registers(self, address, count, unit=1):
        """Simulate reading registers"""
        result = Mock()
        result.isError = Mock(return_value=False)
        result.registers = [self.registers.get(address + i, 0) for i in range(count)]
        logger.debug(f"Read registers {address}-{address+count-1}: {result.registers}")
        return result
    
    def write_register(self, address, value, unit=1):
        """Simulate writing register"""
        self.registers[address] = value
        logger.info(f"Write register {address} = {value}")
        result = Mock()
        result.isError = Mock(return_value=False)
        return result


class MockGPIO:
    """Mock GPIO for button simulation"""
    
    BCM = "BCM"
    IN = "IN"
    OUT = "OUT"
    PUD_UP = "PUD_UP"
    
    def __init__(self):
        self.pins = {}
        self.button_states = {17: True, 27: True, 22: True, 23: True}  # Pull-up (not pressed)
    
    def setmode(self, mode):
        logger.info(f"GPIO setmode: {mode}")
    
    def setwarnings(self, enable):
        pass
    
    def setup(self, pin, mode, pull_up_down=None):
        self.pins[pin] = {'mode': mode, 'pull': pull_up_down}
        logger.debug(f"GPIO setup pin {pin}: {mode}")
    
    def input(self, pin):
        return self.button_states.get(pin, True)
    
    def cleanup(self):
        logger.info("GPIO cleanup")
    
    def simulate_button_press(self, pin):
        """Simulate a button press"""
        logger.info(f"Simulating button press on pin {pin}")
        self.button_states[pin] = False  # Active low
    
    def simulate_button_release(self, pin):
        """Simulate a button release"""
        self.button_states[pin] = True


def test_display1_views():
    """Test Display 1 auto-rotating views"""
    logger.info("=" * 60)
    logger.info("Testing Display 1 (20x4) Auto-Rotating Views")
    logger.info("=" * 60)
    
    with patch('display_manager.smbus', MockSMBusModule), \
         patch('display_manager.ModbusTcpClient', MockModbusClient):
        
        from display_manager import Display1Manager, Display1View
        
        # Initialize display
        display = Display1Manager(
            i2c_addr=0x27,
            modbus_host="127.0.0.1",
            update_interval=2.0
        )
        
        # Test each view manually
        logger.info("\nTesting STATUS view:")
        display.current_view = Display1View.STATUS
        display.update_display()
        
        logger.info("\nTesting BLOCK_CONDITIONS view:")
        display.current_view = Display1View.BLOCK_CONDITIONS
        display.update_display()
        
        logger.info("\nTesting PUMP_STATE view:")
        display.current_view = Display1View.PUMP_STATE
        display.update_display()
        
        logger.info("\nTesting CONNECTIVITY view:")
        display.current_view = Display1View.CONNECTIVITY
        display.update_display()
        
        logger.info("\nStarting auto-rotation for 10 seconds...")
        display.start()
        time.sleep(10)
        display.stop()
        
        logger.info("Display 1 test completed successfully!")


def test_display2_buttons():
    """Test Display 2 button navigation"""
    logger.info("=" * 60)
    logger.info("Testing Display 2 (2x8) Button Navigation")
    logger.info("=" * 60)
    
    mock_gpio = MockGPIO()
    
    # Mock both the module and the import (no longer needed for GPIO but kept for compatibility)
    import sys
    sys.modules['RPi'] = type(sys)('RPi')
    sys.modules['RPi.GPIO'] = mock_gpio
    
    with patch('display_manager.smbus', MockSMBusModule), \
         patch('display_manager.ModbusTcpClient', MockModbusClient):
        
        from display_manager import Display2Manager, Display2View
        
        # Initialize display (button_pins parameter is deprecated but still accepted)
        display = Display2Manager(
            i2c_addr=0x3F,
            modbus_host="127.0.0.1"
        )
        
        # Test initial view
        logger.info("\nInitial view: OVERVIEW")
        assert display.current_view == Display2View.OVERVIEW
        display.update_display()
        
        # Test OK button (navigate to mode selection)
        logger.info("\nSimulating OK button press (enter menu)...")
        display.handle_button_press('ok')
        assert display.current_view == Display2View.MODE_SELECT
        logger.info(f"Current view: {display.current_view.name}")
        
        # Test RIGHT button (change mode)
        logger.info("\nSimulating RIGHT button press (change mode)...")
        initial_mode = display.selected_mode
        display.handle_button_press('right', is_held=False)
        logger.info(f"Mode changed from {initial_mode} to {display.selected_mode}")
        assert display.selected_mode == (initial_mode + 1) % 4
        
        # Test OK button (advance to zone selection)
        logger.info("\nSimulating OK button press (to zone selection)...")
        display.handle_button_press('ok')
        assert display.current_view == Display2View.ZONE_SELECT
        logger.info(f"Current view: {display.current_view.name}")
        
        # Test RIGHT button (increment zone)
        logger.info("\nSimulating RIGHT button press (increment zone)...")
        initial_zone = display.selected_zone
        display.handle_button_press('right', is_held=False)
        logger.info(f"Zone changed from {initial_zone} to {display.selected_zone}")
        assert display.selected_zone == initial_zone + 1
        
        # Test LEFT button (decrement zone)
        logger.info("\nSimulating LEFT button press (decrement zone)...")
        current_zone = display.selected_zone
        display.handle_button_press('left', is_held=False)
        logger.info(f"Zone changed from {current_zone} to {display.selected_zone}")
        assert display.selected_zone == current_zone - 1
        
        # Test BACK button (navigate back to mode select)
        logger.info("\nSimulating BACK button press...")
        display.handle_button_press('back', is_held=False)
        assert display.current_view == Display2View.MODE_SELECT
        logger.info(f"Current view: {display.current_view.name}")
        
        # Test BACK button again (navigate back to overview)
        logger.info("\nSimulating BACK button press (to overview)...")
        display.handle_button_press('back', is_held=False)
        assert display.current_view == Display2View.OVERVIEW
        logger.info(f"Current view: {display.current_view.name}")
        
        logger.info("\nDisplay 2 test completed successfully!")


def test_auto_scheduler():
    """Test auto-watering scheduler"""
    logger.info("=" * 60)
    logger.info("Testing Auto-Watering Scheduler")
    logger.info("=" * 60)
    
    with patch('display_manager.ModbusTcpClient', MockModbusClient):
        from display_manager import AutoScheduler
        
        # Initialize scheduler (set to current time + 1 minute for testing)
        now = datetime.now()
        test_hour = now.hour
        test_minute = (now.minute + 1) % 60
        
        scheduler = AutoScheduler(
            modbus_host="127.0.0.1",
            schedule_hour=test_hour,
            schedule_minute=test_minute
        )
        
        # Test condition checking
        logger.info("\nChecking watering conditions...")
        allowed, reason = scheduler.check_conditions()
        logger.info(f"Conditions: allowed={allowed}, reason='{reason}'")
        assert allowed == True, "Should allow watering when block_reason=0"
        
        # Test manual trigger
        logger.info("\nManually triggering auto-watering...")
        scheduler.trigger_auto_watering()
        
        logger.info("\nScheduler test completed successfully!")


def test_modbus_integration():
    """Test Modbus register reading and writing"""
    logger.info("=" * 60)
    logger.info("Testing Modbus Integration")
    logger.info("=" * 60)
    
    # Create a shared mock client instance to persist register values
    mock_client_class = MockModbusClient
    
    with patch('display_manager.ModbusTcpClient', mock_client_class):
        from display_manager import ModbusReader
        
        modbus = ModbusReader(host="127.0.0.1", port=502)
        
        # Test reading registers
        logger.info("\nReading status registers...")
        regs = modbus.read_registers(50, 4)
        logger.info(f"Status registers (50-53): {regs}")
        assert regs is not None
        assert len(regs) == 4
        
        # Test reading environmental data
        logger.info("\nReading environmental registers...")
        env_regs = modbus.read_registers(30, 3)
        logger.info(f"Environmental registers (30-32): {env_regs}")
        logger.info(f"  Moisture: {env_regs[0]}%")
        logger.info(f"  Rain: {env_regs[1]}mm")
        logger.info(f"  Temperature: {env_regs[2]}°C")
        
        # Test writing register - just verify it returns success
        logger.info("\nWriting manual time register...")
        success = modbus.write_register(64, 10)
        assert success == True
        logger.info("Write successful")
        
        logger.info("\nModbus integration test completed successfully!")


def test_display_rendering():
    """Test display rendering without hardware"""
    logger.info("=" * 60)
    logger.info("Testing Display Rendering Logic")
    logger.info("=" * 60)
    
    with patch('display_manager.smbus', MockSMBusModule), \
         patch('display_manager.ModbusTcpClient', MockModbusClient):
        
        from display_manager import Display1Manager, Display2Manager, Display2View
        
        # Test Display 1
        logger.info("\nTesting Display 1 rendering...")
        d1 = Display1Manager(i2c_addr=0x27)
        
        # Get system status
        status = d1.get_system_status()
        logger.info(f"System status: {status}")
        assert 'zone' in status
        assert 'pump_on' in status
        assert 'mode' in status
        
        # Test Display 2
        logger.info("\nTesting Display 2 rendering...")
        d2 = Display2Manager(i2c_addr=0x3F)
        
        # Switch to zone selection view
        d2.current_view = Display2View.ZONE_SELECT
        
        # Test zone boundaries
        d2.selected_zone = 7
        d2.handle_button_press('right', is_held=False)  # RIGHT increases zone
        assert d2.selected_zone == 1, "Zone should wrap from 7 to 1"
        
        d2.selected_zone = 1
        d2.handle_button_press('left', is_held=False)  # LEFT decreases zone
        assert d2.selected_zone == 7, "Zone should wrap from 1 to 7"
        
        # Test mode selection
        d2.current_view = Display2View.MODE_SELECT
        d2.selected_mode = 0
        d2.handle_button_press('right', is_held=False)
        assert d2.selected_mode == 1, "Mode should change from Auto to Manual"
        
        logger.info("\nDisplay rendering test completed successfully!")


def run_all_tests():
    """Run all test suites"""
    logger.info("\n" + "=" * 60)
    logger.info("DISPLAY MANAGER TEST SUITE")
    logger.info("=" * 60 + "\n")
    
    try:
        test_modbus_integration()
        time.sleep(1)
        
        test_display_rendering()
        time.sleep(1)
        
        test_display1_views()
        time.sleep(1)
        
        test_display2_buttons()
        time.sleep(1)
        
        test_auto_scheduler()
        
        logger.info("\n" + "=" * 60)
        logger.info("ALL TESTS PASSED!")
        logger.info("=" * 60 + "\n")
        
        return True
    except Exception as e:
        logger.error(f"\nTEST FAILED: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
