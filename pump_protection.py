#!/usr/bin/env python3
"""
Smart Pump Protection - Digital Sensor Implementation

Skyddar pumpen mot:
1. Slangbrott (Flow=1, Pressure=0) - KRITISKT
2. Torrkörning (Flow=0, Pressure=0) - KRITISKT
3. Normal avslutning vid slangvinda (Flow=0, Pressure=1) - NORMALT

Använder digitala sensorer (Tryckvakt och Flödesvakt).
"""
import logging
import time
from datetime import datetime
from typing import Optional

logger = logging.getLogger("bevattning.pump_protection")

# === KONFIGURATION ===
START_GRACE_PERIOD = 25  # Sekunder (Generös tid för mjukstart att bygga tryck)
SLANGBROTT_DELAY = 2     # Sekunder (Filtertid innan larm vid tryckfall i drift)
TORRKORNING_DELAY = 10   # Sekunder (Filtertid innan larm vid vattenbrist)


class PumpState:
    """Håller persistent state för pump-övervakning mellan anrop"""
    
    def __init__(self):
        self.time_running = 0.0
        self.timer_slangbrott = 0.0
        self.timer_torrkorning = 0.0
        self.last_check: Optional[float] = None
        self.pump_was_active = False
        self.start_count = 0
        self.start_history = []  # Lista med timestamps för starter
    
    def update(self, pump_active: bool, delta_time: float):
        """
        Uppdatera timers baserat på pump-status
        
        Args:
            pump_active: True om pumpen är PÅ
            delta_time: Tid sedan senaste update (sekunder)
        """
        # Detektera pump-start (rising edge)
        if pump_active and not self.pump_was_active:
            self.start_count += 1
            self.start_history.append(time.time())
            logger.info(f"🔵 Pump STARTAD (#{self.start_count})")
        
        # Detektera pump-stopp (falling edge)
        if not pump_active and self.pump_was_active:
            logger.info(f"⚫ Pump STOPPAD (körde {self.time_running:.1f}s)")
        
        if pump_active:
            self.time_running += delta_time
        else:
            # Reset timers vid stopp
            self.time_running = 0.0
            self.timer_slangbrott = 0.0
            self.timer_torrkorning = 0.0
        
        self.pump_was_active = pump_active
    
    def reset(self):
        """Reset all state (används vid error reset)"""
        logger.info("Pump protection state reset")
        self.__init__()


def check_pump_safety(
    state: PumpState,
    pump_active: bool,
    flow_detected: bool,
    pressure_ok: bool,
    delta_time: float
) -> str:
    """
    Checkar säkerheten baserat på digitala sensorer.
    
    Args:
        state: Persistent state-objekt
        pump_active: True om pumpen är PÅ (från MW51)
        flow_detected: True om flöde (från I07/MW55)
        pressure_ok: True om tryck OK (från I09/MW33)
        delta_time: Tid sedan senaste check (sekunder)
    
    Returns:
        str: "OK", "STOP_NORMAL", "ALARM_SLANGBROTT", "ALARM_TORRKORNING"
    """
    
    # Uppdatera state
    state.update(pump_active, delta_time)
    
    if not pump_active:
        return "OK"  # Pumpen är av, inget att checka
    
    # === FAS 1: UPPSTART (Maskning) ===
    if state.time_running < START_GRACE_PERIOD:
        # Reset alarm-timers under grace period
        state.timer_slangbrott = 0.0
        state.timer_torrkorning = 0.0
        logger.debug(f"Grace period: {state.time_running:.1f}s / {START_GRACE_PERIOD}s")
        return "OK"
    
    # === FAS 2: DRIFT (Skarpt läge) ===
    
    # A. SLANGBROTT (Högsta prio)
    # Vatten flödar (1) men trycket orkar inte hålla sig uppe (0) -> Läckage!
    if flow_detected and not pressure_ok:
        state.timer_slangbrott += delta_time
        state.timer_torrkorning = 0.0  # Reset andra timern
        
        if state.timer_slangbrott > SLANGBROTT_DELAY:
            logger.error(f"🚨 SLANGBROTT: Flöde=JA, Tryck=NEJ (tid={state.timer_slangbrott:.1f}s)")
            return "ALARM_SLANGBROTT"
        else:
            logger.warning(f"⚠️ Möjligt slangbrott: {state.timer_slangbrott:.1f}s / {SLANGBROTT_DELAY}s")
            return "OK"
    
    # B. TORRKÖRNING
    # Inget flöde (0) och inget tryck (0) -> Vattnet är slut eller pumpfel
    elif not flow_detected and not pressure_ok:
        state.timer_torrkorning += delta_time
        state.timer_slangbrott = 0.0
        
        if state.timer_torrkorning > TORRKORNING_DELAY:
            logger.error(f"🚨 TORRKÖRNING: Flöde=NEJ, Tryck=NEJ (tid={state.timer_torrkorning:.1f}s)")
            return "ALARM_TORRKORNING"
        else:
            logger.warning(f"⚠️ Möjlig torrkörning: {state.timer_torrkorning:.1f}s / {TORRKORNING_DELAY}s")
            return "OK"
    
    # C. SLANGVINDA KLAR (Normalt stopp)
    # Inget flöde (0) men trycket är kvar (1)
    # Slangvindan har stängt ventilen -> Pumpen jobbar mot stängd ventil (Deadhead)
    elif not flow_detected and pressure_ok:
        logger.info("✅ Slangvinda stängd (Flöde=NEJ, Tryck=JA) - Normal avslutning")
        return "STOP_NORMAL"
    
    # D. Normal drift
    else:  # flow_detected and pressure_ok
        # Reset alla timers
        state.timer_slangbrott = 0.0
        state.timer_torrkorning = 0.0
        logger.debug("✅ Normal drift: Flöde=JA, Tryck=JA")
        return "OK"


def get_diagnostics(state: PumpState, pump_active: bool, flow_detected: bool, pressure_ok: bool) -> dict:
    """
    Hämta diagnostik-data för loggning/troubleshooting
    
    Returns:
        dict med aktuell status och timers
    """
    return {
        "pump_active": pump_active,
        "flow_detected": flow_detected,
        "pressure_ok": pressure_ok,
        "time_running": round(state.time_running, 1),
        "timer_slangbrott": round(state.timer_slangbrott, 1),
        "timer_torrkorning": round(state.timer_torrkorning, 1),
        "start_count": state.start_count,
        "timestamp": datetime.now().isoformat()
    }
