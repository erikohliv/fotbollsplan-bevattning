#!/usr/bin/env python3
"""
Minimal Modbus TCP Server för UniPi 1.1
Ersätter Evok för enkel Modbus TCP → I2C-kommunikation
"""
import logging
from pymodbus.server import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.transaction import ModbusRtuFramer
import smbus2
import threading
import time

# Konfiguration
I2C_BUS = 1
MCP23008_ADDRESS = 0x20  # UniPi 1.1 reläkontroller
MODBUS_PORT = 502

# MCP23008 Register
MCP_IODIR = 0x00  # I/O Direction (0=output, 1=input)
MCP_GPIO = 0x09   # GPIO Register
MCP_OLAT = 0x0A   # Output Latch

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UniPi11Modbus:
    """Hanterar I2C-kommunikation med UniPi 1.1"""
    
    def __init__(self):
        try:
            self.bus = smbus2.SMBus(I2C_BUS)
            self._init_mcp23008()
            logger.info("✓ UniPi 1.1 I2C initialiserad")
        except Exception as e:
            logger.error(f"✗ Kunde inte initiera I2C: {e}")
            raise
    
    def _init_mcp23008(self):
        """Initierar MCP23008 - alla pins som utgångar"""
        try:
            self.bus.write_byte_data(MCP23008_ADDRESS, MCP_IODIR, 0x00)  # Alla utgångar
            self.bus.write_byte_data(MCP23008_ADDRESS, MCP_GPIO, 0x00)   # Alla låga
            logger.info("✓ MCP23008 initialiserad (8 relän)")
        except Exception as e:
            logger.warning(f"✗ MCP23008-init misslyckades: {e}")
    
    def set_relay(self, relay_num, state):
        """
        Sätt reläläge (1-8)
        relay_num: 1-8
        state: True/False eller 1/0
        """
        if not (1 <= relay_num <= 8):
            logger.error(f"Ogiltigt reländummer: {relay_num}")
            return False
        
        try:
            # Läs nuvarande värde
            current = self.bus.read_byte_data(MCP23008_ADDRESS, MCP_OLAT)
            
            # UniPi 1.1 reläer är mappade omvänt (pin 7 = R1, pin 0 = R8)
            pin = 8 - relay_num
            
            if state:
                new_value = current | (1 << pin)  # Sätt bit
            else:
                new_value = current & ~(1 << pin)  # Nollställ bit
            
            self.bus.write_byte_data(MCP23008_ADDRESS, MCP_OLAT, new_value)
            logger.debug(f"Relä {relay_num} → {'ON' if state else 'OFF'}")
            return True
        except Exception as e:
            logger.error(f"✗ Kunde inte sätta relä {relay_num}: {e}")
            return False
    
    def get_relays(self):
        """Läs alla reläers tillstånd"""
        try:
            value = self.bus.read_byte_data(MCP23008_ADDRESS, MCP_OLAT)
            # Konvertera till lista (R1-R8)
            relays = []
            for i in range(8):
                pin = 7 - i  # Omvänd mappning
                relays.append(bool(value & (1 << pin)))
            return relays
        except Exception as e:
            logger.error(f"✗ Kunde inte läsa reläer: {e}")
            return [False] * 8


class ModbusUniPiUpdater(threading.Thread):
    """Synkar Modbus datastore med UniPi hårdvara"""
    
    def __init__(self, context, unipi):
        super().__init__(daemon=True)
        self.context = context
        self.unipi = unipi
        self.running = True
    
    def run(self):
        logger.info("✓ Modbus sync-tråd startad")
        while self.running:
            try:
                # Läs coils från Modbus (adress 0-7 = R1-R8)
                slave_context = self.context[0x01]
                coils = slave_context.getValues(1, 0, count=8)  # Function code 1 = Read Coils
                
                # Uppdatera hårdvaran
                for i, state in enumerate(coils):
                    relay_num = i + 1
                    self.unipi.set_relay(relay_num, bool(state))
                
                time.sleep(0.1)  # 10 Hz uppdatering
            except Exception as e:
                logger.error(f"✗ Sync-fel: {e}")
                time.sleep(1)
    
    def stop(self):
        self.running = False


def run_server():
    """Startar Modbus TCP-servern"""
    logger.info("=== UniPi 1.1 Modbus TCP Server ===")
    
    # Initialisera UniPi
    unipi = UniPi11Modbus()
    
    # Skapa Modbus datastore
    # Coils (DO): 0-7 = R1-R8
    # Discrete Inputs (DI): 0-11 = I01-I12 (läses inte ännu, kräver mer hårdvara)
    # Holding Registers (AO): 0-1 = Analoga utgångar
    # Input Registers (AI): 0-1 = Analoga ingångar
    
    store = ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0, [0]*12),     # Discrete Inputs
        co=ModbusSequentialDataBlock(0, [0]*8),      # Coils (Relays)
        hr=ModbusSequentialDataBlock(0, [0]*10),     # Holding Registers
        ir=ModbusSequentialDataBlock(0, [0]*10)      # Input Registers
    )
    context = ModbusServerContext(slaves={0x01: store}, single=False)
    
    # Starta sync-tråd
    updater = ModbusUniPiUpdater(context, unipi)
    updater.start()
    
    # Device identification
    identity = ModbusDeviceIdentification()
    identity.VendorName = 'UniPi'
    identity.ProductCode = 'UniPi 1.1'
    identity.VendorUrl = 'https://unipi.technology'
    identity.ProductName = 'UniPi 1.1 I/O Controller'
    identity.ModelName = 'UniPi 1.1'
    identity.MajorMinorRevision = '1.0.0'
    
    logger.info(f"✓ Startar Modbus TCP Server på port {MODBUS_PORT}")
    logger.info("  - Coils 0-7: Relän R1-R8")
    logger.info("  - Discrete Inputs 0-11: Ingångar I01-I12 (ej implementerat)")
    logger.info("  - Input Registers 0-1: Analoga ingångar (ej implementerat)")
    
    try:
        StartTcpServer(
            context=context,
            identity=identity,
            address=("0.0.0.0", MODBUS_PORT)
        )
    except KeyboardInterrupt:
        logger.info("Stänger ner...")
        updater.stop()
    except Exception as e:
        logger.error(f"✗ Server-fel: {e}")
        updater.stop()
        raise


if __name__ == "__main__":
    run_server()
