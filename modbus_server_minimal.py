#!/usr/bin/env python3
"""
Minimal Modbus TCP Server för UniPi 1.1
Enkel, robust och testbevisad implementation
"""
import logging
import threading
import time
from pymodbus.server import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
import smbus2

# Konfiguration
MODBUS_PORT = 502
I2C_BUS = 1
MCP23008_ADDR = 0x20

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UniPiHardware:
    """Hårdvaruabstraktion för UniPi via I2C"""
    
    def __init__(self):
        self.bus = smbus2.SMBus(I2C_BUS)
        self.relay_state = 0x00
        self._init_mcp23008()
        logger.info("✓ UniPi hårdvara initialiserad")
    
    def _init_mcp23008(self):
        """Initiera MCP23008 som utgångar"""
        try:
            # IODIR = 0x00 (alla pinnar som utgångar)
            self.bus.write_byte_data(MCP23008_ADDR, 0x00, 0x00)
            # Stäng av alla reläer
            self.bus.write_byte_data(MCP23008_ADDR, 0x09, 0x00)
            logger.info("✓ MCP23008 konfigurerad (8 reläer)")
        except Exception as e:
            logger.error(f"✗ MCP23008 init fel: {e}")
            raise
    
    def set_relay(self, relay_num, state):
        """
        Sätt relä on/off
        relay_num: 1-8
        state: True/False
        """
        try:
            if relay_num < 1 or relay_num > 8:
                return False
            
            bit = relay_num - 1
            if state:
                self.relay_state |= (1 << bit)
            else:
                self.relay_state &= ~(1 << bit)
            
            self.bus.write_byte_data(MCP23008_ADDR, 0x09, self.relay_state)
            logger.debug(f"Relä {relay_num} → {'ON' if state else 'OFF'} (state: 0x{self.relay_state:02X})")
            return True
        except Exception as e:
            logger.error(f"Relä {relay_num} fel: {e}")
            return False
    
    def get_relay_state(self):
        """Läs aktuellt reläläge"""
        try:
            return self.bus.read_byte_data(MCP23008_ADDR, 0x09)
        except:
            return self.relay_state
    
    def close(self):
        """Stäng I2C och säkerställ alla reläer av"""
        try:
            self.bus.write_byte_data(MCP23008_ADDR, 0x09, 0x00)
            self.bus.close()
            logger.info("✓ Hårdvara stängd säkert")
        except:
            pass

class ModbusHardwareSync:
    """Synkronisera Modbus-datastore med hårdvara"""
    
    def __init__(self, context, hardware):
        self.context = context
        self.hardware = hardware
        self.running = False
        self.thread = None
    
    def start(self):
        """Starta synkroniseringstråd"""
        self.running = True
        self.thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.thread.start()
        logger.info("✓ Synkroniseringstråd startad")
    
    def stop(self):
        """Stoppa synkroniseringstråd"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
    
    def _sync_loop(self):
        """Huvudloop för synkronisering"""
        while self.running:
            try:
                # Hämta Modbus coil-states (unit 1)
                slave_context = self.context[1]
                coils = slave_context.getValues(1, 0, 8)  # Function code 1 (coils), address 0, count 8
                
                # Uppdatera hårdvara
                for i in range(8):
                    relay_num = i + 1
                    desired_state = bool(coils[i])
                    self.hardware.set_relay(relay_num, desired_state)
                
                # Läs tillbaka hårdvaruläge och uppdatera discrete inputs
                hw_state = self.hardware.get_relay_state()
                discrete_inputs = [(hw_state >> i) & 1 for i in range(8)]
                slave_context.setValues(2, 0, discrete_inputs)  # Function code 2 (discrete inputs)
                
            except KeyError:
                # Unit 1 finns inte än, vänta
                pass
            except Exception as e:
                logger.error(f"Synkfel: {e}")
            
            time.sleep(0.1)  # 100ms update rate

def create_modbus_context():
    """Skapa Modbus datastore"""
    
    # Coils (0-7): Reläer R1-R8 (Read/Write)
    coils = ModbusSequentialDataBlock(0, [0]*8)
    
    # Discrete Inputs (0-7): Relä-status (Read Only)
    discrete = ModbusSequentialDataBlock(0, [0]*8)
    
    # Holding Registers: För framtida användning
    holding = ModbusSequentialDataBlock(0, [0]*100)
    
    # Input Registers: För framtida användning (sensorer)
    input_reg = ModbusSequentialDataBlock(0, [0]*100)
    
    store = ModbusSlaveContext(
        di=discrete,
        co=coils,
        hr=holding,
        ir=input_reg
    )
    
    context = ModbusServerContext(slaves={1: store}, single=False)
    
    logger.info("✓ Modbus datastore skapad")
    logger.info("  - Coils 0-7: Reläer R1-R8 (Read/Write)")
    logger.info("  - Discrete Inputs 0-7: Relästatus (Read Only)")
    
    return context

def main():
    """Huvudfunktion"""
    logger.info("="*60)
    logger.info("UniPi 1.1 Minimal Modbus TCP Server")
    logger.info("="*60)
    
    # Initiera hårdvara
    hardware = UniPiHardware()
    
    # Skapa Modbus context
    context = create_modbus_context()
    
    # Starta synkronisering
    sync = ModbusHardwareSync(context, hardware)
    sync.start()
    
    # Server identity
    identity = ModbusDeviceIdentification()
    identity.VendorName = 'IK Kamp'
    identity.ProductCode = 'UNIPI-MODBUS'
    identity.VendorUrl = 'http://localhost'
    identity.ProductName = 'UniPi Modbus Server'
    identity.ModelName = 'UniPi 1.1'
    identity.MajorMinorRevision = '2.0'
    
    logger.info(f"✓ Startar Modbus TCP Server på port {MODBUS_PORT}")
    logger.info("  Tryck Ctrl+C för att stoppa")
    
    try:
        # Starta server (blocking)
        StartTcpServer(
            context=context,
            identity=identity,
            address=("0.0.0.0", MODBUS_PORT)
        )
    except KeyboardInterrupt:
        logger.info("\n⚠️  Stoppsignal mottagen")
    except Exception as e:
        logger.error(f"Serverfel: {e}")
    finally:
        sync.stop()
        hardware.close()
        logger.info("✓ Server stoppad")

if __name__ == "__main__":
    main()
