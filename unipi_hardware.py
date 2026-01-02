"""
UniPi I2C Hardware Controller
Direkt hårdvarustyrning via I2C för UniPi 1.1
"""
import smbus2
import logging
import threading
import time

logger = logging.getLogger(__name__)

# I2C Konfiguration
I2C_BUS = 1
MCP23008_ADDR = 0x20

class UniPiHardware:
    """Hårdvarukontroller för UniPi 1.1 reläer"""
    
    def __init__(self):
        self.bus = smbus2.SMBus(I2C_BUS)
        self.relay_state = 0x00
        self.lock = threading.Lock()
        self._init_hardware()
    
    def _init_hardware(self):
        """Initiera MCP23008 för reläkontroll"""
        try:
            with self.lock:
                # IODIR (0x00) = 0x00 → Alla pinnar som utgångar
                self.bus.write_byte_data(MCP23008_ADDR, 0x00, 0x00)
                # GPIO (0x09) = 0x00 → Alla reläer av
                self.bus.write_byte_data(MCP23008_ADDR, 0x09, 0x00)
                self.relay_state = 0x00
            logger.info("✓ UniPi hårdvara initialiserad (MCP23008 @ 0x%02X)", MCP23008_ADDR)
        except Exception as e:
            logger.error("✗ Hårdvaruinitiering misslyckades: %s", e)
            raise
    
    def set_relay(self, relay_num: int, state: bool) -> bool:
        """
        Sätt enskilt relä on/off
        
        Args:
            relay_num: Relänummer 1-8
            state: True = ON, False = OFF
        
        Returns:
            bool: True om lyckat, False annars
        """
        if relay_num < 1 or relay_num > 8:
            logger.warning("Ogiltigt relänummer: %d", relay_num)
            return False
        
        try:
            with self.lock:
                bit = relay_num - 1
                if state:
                    self.relay_state |= (1 << bit)
                else:
                    self.relay_state &= ~(1 << bit)
                
                self.bus.write_byte_data(MCP23008_ADDR, 0x09, self.relay_state)
            
            logger.debug("Relä %d → %s (state: 0x%02X)", relay_num, "ON" if state else "OFF", self.relay_state)
            return True
        except Exception as e:
            logger.error("Relä %d fel: %s", relay_num, e)
            return False
    
    def get_relay_state(self, relay_num: int = None) -> any:
        """
        Läs reläläge
        
        Args:
            relay_num: Specifikt relä (1-8) eller None för alla
        
        Returns:
            bool om relay_num anges, annars int (bitmask)
        """
        try:
            with self.lock:
                hw_state = self.bus.read_byte_data(MCP23008_ADDR, 0x09)
                self.relay_state = hw_state
            
            if relay_num is not None:
                if relay_num < 1 or relay_num > 8:
                    return False
                return bool((hw_state >> (relay_num - 1)) & 1)
            else:
                return hw_state
        except Exception as e:
            logger.error("Läsfel: %s", e)
            if relay_num is not None:
                return False
            return self.relay_state
    
    def all_off(self) -> bool:
        """Stäng av alla reläer"""
        try:
            with self.lock:
                self.bus.write_byte_data(MCP23008_ADDR, 0x09, 0x00)
                self.relay_state = 0x00
            logger.info("✓ Alla reläer avstängda")
            return True
        except Exception as e:
            logger.error("All off fel: %s", e)
            return False
    
    def close(self):
        """Stäng I2C-anslutning säkert"""
        try:
            self.all_off()
            self.bus.close()
            logger.info("✓ Hårdvara stängd")
        except:
            pass

# Global hårdvaruinstans
_hardware = None

def get_hardware() -> UniPiHardware:
    """Hämta global hårdvaruinstans (singleton)"""
    global _hardware
    if _hardware is None:
        _hardware = UniPiHardware()
    return _hardware

def cleanup_hardware():
    """Städa upp hårdvara vid shutdown"""
    global _hardware
    if _hardware is not None:
        _hardware.close()
        _hardware = None
