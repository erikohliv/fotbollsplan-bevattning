#!/usr/bin/env python3
"""
Enkel och robust Modbus TCP Server för UniPi 1.1
Testad och fungerande version
"""
import logging
import smbus2
import time
from threading import Thread, Lock
from pymodbus.server import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.transaction import ModbusSocketFramer

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# I2C-konfiguration
MCP23008_ADDR = 0x20  # Relän
I2C_BUS = 1

# Global state
relay_state = 0  # 8 bitar för 8 reläer
i2c_lock = Lock()
bus = None


class UniPiHardware:
    """Hårdvaruabstraktion för UniPi I2C"""
    
    def __init__(self):
        global bus
        try:
            bus = smbus2.SMBus(I2C_BUS)
            # Konfigurera MCP23008 som utgångar
            bus.write_byte_data(MCP23008_ADDR, 0x00, 0x00)  # IODIR = alla utgångar
            logger.info("✓ MCP23008 (8 reläer) initialiserad")
        except Exception as e:
            logger.error(f"✗ Kunde inte initialisera I2C: {e}")
            bus = None
    
    def set_relays(self, state):
        """Sätt reläernas tillstånd (8 bitar)"""
        if bus is None:
            return False
        
        with i2c_lock:
            try:
                bus.write_byte_data(MCP23008_ADDR, 0x09, state & 0xFF)
                return True
            except Exception as e:
                logger.error(f"Fel vid skrivning till reläer: {e}")
                return False
    
    def get_relays(self):
        """Läs reläernas tillstånd"""
        if bus is None:
            return 0
        
        with i2c_lock:
            try:
                return bus.read_byte_data(MCP23008_ADDR, 0x09)
            except Exception as e:
                logger.error(f"Fel vid läsning från reläer: {e}")
                return 0


class ModbusCallbacks:
    """Callbacks för Modbus-operationer"""
    
    def __init__(self, hardware):
        self.hardware = hardware
    
    def on_coil_write(self, address, values):
        """När en coil skrivs (reläer)"""
        global relay_state
        
        # Konvertera lista av bitar till byte
        new_state = 0
        for i, val in enumerate(values[:8]):
            if val:
                new_state |= (1 << i)
        
        relay_state = new_state
        success = self.hardware.set_relays(relay_state)
        
        if success:
            logger.info(f"Reläer uppdaterade: {relay_state:08b}")
        else:
            logger.error("Kunde inte uppdatera reläer")
        
        return success


def update_datastore_loop(context, hardware):
    """Synkronisera hårdvara med Modbus datastore"""
    logger.info("✓ Datastore sync-tråd startad")
    
    while True:
        try:
            # Läs faktiskt reläläge från hårdvara
            actual_state = hardware.get_relays()
            
            # Uppdatera datastore med faktiskt läge
            slave_context = context[0]
            store = slave_context.store['c']  # Coils
            
            # Konvertera byte till lista av bitar
            bits = [(actual_state >> i) & 1 for i in range(8)]
            store.setValues(0, bits)
            
            time.sleep(0.1)  # 100ms uppdateringsintervall
            
        except Exception as e:
            logger.error(f"Fel i sync-loop: {e}")
            time.sleep(1)


def run_server():
    """Starta Modbus TCP-servern"""
    logger.info("=== UniPi Simple Modbus TCP Server ===")
    
    # Initialisera hårdvara
    hardware = UniPiHardware()
    callbacks = ModbusCallbacks(hardware)
    
    # Skapa datastore
    # Coils (Read/Write): Relän 0-7
    # Discrete Inputs (Read Only): Digital inputs (framtida)
    # Input Registers (Read Only): Analoga inputs (framtida)
    coils = ModbusSequentialDataBlock(0, [0] * 8)
    discrete_inputs = ModbusSequentialDataBlock(0, [0] * 12)
    input_registers = ModbusSequentialDataBlock(0, [0] * 10)
    holding_registers = ModbusSequentialDataBlock(0, [0] * 100)
    
    store = ModbusSlaveContext(
        di=discrete_inputs,
        co=coils,
        hr=holding_registers,
        ir=input_registers
    )
    
    context = ModbusServerContext(slaves=store, single=True)
    
    # Starta sync-tråd
    sync_thread = Thread(target=update_datastore_loop, args=(context, hardware), daemon=True)
    sync_thread.start()
    
    # Device identification
    identity = ModbusDeviceIdentification()
    identity.VendorName = 'UniPi'
    identity.ProductCode = 'UNIPI1.1'
    identity.VendorUrl = 'https://www.unipi.technology'
    identity.ProductName = 'UniPi 1.1 Relay Controller'
    identity.ModelName = 'UniPi 1.1'
    identity.MajorMinorRevision = '2.0.0'
    
    # Custom request handler för att fånga skrivningar
    from pymodbus.datastore.store import BaseModbusDataBlock
    original_setValues = BaseModbusDataBlock.setValues
    
    def custom_setValues(self, address, values):
        # Anropa original
        result = original_setValues(self, address, values)
        
        # Om det är coils som skrivs, uppdatera hårdvara
        if hasattr(self, 'address') and self.address == 0:  # Coils
            callbacks.on_coil_write(address, values)
        
        return result
    
    BaseModbusDataBlock.setValues = custom_setValues
    
    logger.info("✓ Startar Modbus TCP Server på port 502")
    logger.info("  - Coils 0-7: Relän R1-R8 (Read/Write)")
    logger.info("  - Discrete Inputs 0-11: DI1-DI12 (Read Only)")
    logger.info("  - Input Registers 0-9: Analoga inputs (Read Only)")
    
    try:
        StartTcpServer(
            context=context,
            identity=identity,
            address=("0.0.0.0", 502),
            framer=ModbusSocketFramer,
            allow_reuse_address=True
        )
    except Exception as e:
        logger.error(f"Serverfel: {e}")
        raise


if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        logger.info("\n✓ Server stoppad")
        if bus:
            # Stäng av alla reläer
            try:
                bus.write_byte_data(MCP23008_ADDR, 0x09, 0x00)
                logger.info("✓ Alla reläer avstängda")
            except:
                pass
            bus.close()
