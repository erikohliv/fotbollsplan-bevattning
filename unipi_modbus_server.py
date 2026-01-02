#!/usr/bin/env python3
"""
Komplett Modbus TCP Server för UniPi 1.1
Hanterar alla I/O: Reläer, Digitala ingångar, Analoga ingångar
"""
import logging
from pymodbus.server import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.transaction import ModbusRtuFramer
import smbus2
import threading
import time

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("WARNING: RPi.GPIO not available - Digital inputs disabled")

try:
    import board
    import busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    ADS_AVAILABLE = True
except ImportError:
    ADS_AVAILABLE = False
    print("WARNING: adafruit-circuitpython-ads1x15 not available - Analog inputs disabled")

# Konfiguration
I2C_BUS = 1
MCP23008_ADDRESS = 0x20  # Reläkontroller
ADS1115_ADDRESS = 0x68   # ADC för analoga ingångar
MODBUS_PORT = 502

# MCP23008 Register
MCP_IODIR = 0x00  # I/O Direction (0=output, 1=input)
MCP_GPIO = 0x09   # GPIO Register
MCP_OLAT = 0x0A   # Output Latch

# UniPi 1.1 GPIO Mapping (BCM numbering)
# Från Evok config och UniPi pinout
DI_GPIO_PINS = [
    4,   # DI1 - I01
    17,  # DI2 - I02
    27,  # DI3 - I03
    23,  # DI4 - I04
    22,  # DI5 - I05
    24,  # DI6 - I06
    11,  # DI7 - I07
    7,   # DI8 - I08
    8,   # DI9 - I09
    9,   # DI10 - I10
    25,  # DI11 - I11
    10,  # DI12 - I12
]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UniPi11Modbus:
    """Hanterar I2C och GPIO-kommunikation med UniPi 1.1"""
    
    def __init__(self):
        try:
            # I2C för reläer
            self.bus = smbus2.SMBus(I2C_BUS)
            self._init_mcp23008()
            logger.info("✓ UniPi 1.1 I2C initialiserad")
            
            # GPIO för digitala ingångar
            if GPIO_AVAILABLE:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                for pin in DI_GPIO_PINS:
                    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                logger.info(f"✓ {len(DI_GPIO_PINS)} digitala ingångar initialiserade")
            else:
                logger.warning("✗ GPIO inte tillgängligt - digitala ingångar inaktiverade")
            
            # ADC för analoga ingångar
            if ADS_AVAILABLE:
                try:
                    i2c = busio.I2C(board.SCL, board.SDA)
                    self.ads = ADS.ADS1115(i2c, address=ADS1115_ADDRESS)
                    self.ai1 = AnalogIn(self.ads, ADS.P0)  # AI1 på kanal 0
                    self.ai2 = AnalogIn(self.ads, ADS.P1)  # AI2 på kanal 1
                    # Konfigurera gain för 0-10V (behöver spänningsdelare)
                    self.ads.gain = 1  # +/-4.096V range
                    logger.info("✓ ADC (ADS1115) initialiserad för analoga ingångar")
                except AttributeError:
                    # Alternativ syntax för äldre biblioteksversion
                    try:
                        from adafruit_ads1x15.single_ended import P0, P1
                        self.ai1 = self.ads.read_adc(0)  # Kanal 0
                        self.ai2 = self.ads.read_adc(1)  # Kanal 1  
                        logger.info("✓ ADC (ADS1115) initialiserad (legacy mode)")
                    except:
                        self.ads = None
                        logger.warning("✗ ADC kunde inte initieras med någon metod")
                except Exception as e:
                    self.ads = None
                    logger.warning(f"✗ ADC-init misslyckades: {e}")
            else:
                self.ads = None
                logger.warning("✗ ADS1115-bibliotek saknas - analoga ingångar inaktiverade")
                
        except Exception as e:
            logger.error(f"✗ Kunde inte initiera UniPi hårdvara: {e}")
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
    
    def read_digital_inputs(self):
        """
        Läs alla digitala ingångar (DI1-DI12)
        
        OBS: Vissa ingångar är inverterade (NC-kontakter):
        - DI3 (index 2): Nödstopp (NC) - LOW = OK, HIGH = LARM
        - DI10 (index 9): Motorskydd (NC) - LOW = OK, HIGH = LARM
        - DI11 (index 10): 24VDC säkring (NC) - LOW = OK, HIGH = LARM
        - DI12 (index 11): 24VAC säkring (NC) - LOW = OK, HIGH = LARM
        """
        if not GPIO_AVAILABLE:
            return [False] * 12
        
        # Index för NC-kontakter som ska inverteras
        NC_INPUTS = [2, 9, 10, 11]  # DI3, DI10, DI11, DI12
        
        try:
            inputs = []
            for idx, pin in enumerate(DI_GPIO_PINS):
                # GPIO.input returnerar 1 (HIGH) eller 0 (LOW)
                state = GPIO.input(pin)
                
                # Invertera NC-kontakter
                if idx in NC_INPUTS:
                    state = not state  # LOW (0) blir TRUE, HIGH (1) blir FALSE
                
                inputs.append(bool(state))
            return inputs
        except Exception as e:
            logger.error(f"✗ Kunde inte läsa digitala ingångar: {e}")
            return [False] * 12
    
    def read_analog_input(self, channel):
        """
        Läs analog ingång (1 eller 2)
        Returnerar värde 0-10V skalat till 0-10000 (för Modbus 16-bit register)
        """
        if not self.ads:
            return 0
        
        try:
            # Försök läsa med AnalogIn (nyare API)
            if hasattr(self, 'ai1') and hasattr(self, 'ai2'):
                if channel == 1:
                    voltage = self.ai1.voltage
                elif channel == 2:
                    voltage = self.ai2.voltage
                else:
                    return 0
            else:
                # Fallback till äldre API
                import adafruit_ads1x15.ads1115 as ADS
                if channel == 1:
                    voltage = self.ads.read_adc(0, gain=1) * 4.096 / 32767
                elif channel == 2:
                    voltage = self.ads.read_adc(1, gain=1) * 4.096 / 32767
                else:
                    return 0
            
            # Skala 0-4.096V till 0-10000 
            # OBS: UniPi 1.1 har spänningsdelare, så 0-10V → 0-3.3V på ADC
            # Justera multiplikator baserat på verklig hårdvara
            scaled_value = int((voltage / 3.3) * 10000)
            return max(0, min(10000, scaled_value))  # Begränsa till 0-10000
            
        except Exception as e:
            logger.error(f"✗ Kunde inte läsa analog ingång {channel}: {e}")
            return 0


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
                slave_context = self.context[0x01]
                
                # 1. Synka Coils (utgångar R1-R8) - Python → Hårdvara
                coils = slave_context.getValues(1, 0, count=8)  # Function code 1 = Read Coils
                for i, state in enumerate(coils):
                    relay_num = i + 1
                    self.unipi.set_relay(relay_num, bool(state))
                
                # 2. Synka Discrete Inputs (ingångar DI1-DI12) - Hårdvara → Modbus
                digital_inputs = self.unipi.read_digital_inputs()
                slave_context.setValues(2, 0, digital_inputs)  # Function code 2 = Discrete Inputs
                
                # 3. Synka Input Registers (analoga ingångar AI1-AI2) - Hårdvara → Modbus
                ai1_value = self.unipi.read_analog_input(1)
                ai2_value = self.unipi.read_analog_input(2)
                slave_context.setValues(4, 0, [ai1_value, ai2_value])  # Function code 4 = Input Registers
                
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
    logger.info("  - Coils 0-7: Relän R1-R8 (Read/Write)")
    logger.info("  - Discrete Inputs 0-11: Digitala ingångar DI1-DI12 (Read Only)")
    logger.info("  - Input Registers 0-1: Analoga ingångar AI1-AI2 (Read Only, 0-10000 = 0-10V)")
    
    try:
        StartTcpServer(
            context=context,
            identity=identity,
            address=("0.0.0.0", MODBUS_PORT)
        )
    except KeyboardInterrupt:
        logger.info("Stänger ner...")
        updater.stop()
        if GPIO_AVAILABLE:
            GPIO.cleanup()
    except Exception as e:
        logger.error(f"✗ Server-fel: {e}")
        updater.stop()
        if GPIO_AVAILABLE:
            GPIO.cleanup()
        raise


if __name__ == "__main__":
    run_server()
