#!/usr/bin/env python3
"""
Zone Configuration Manager (zone_config.py)
Hanterar zonkonfiguration för bevattningssystemet.
Sparar enabled/disabled status för varje zon i zone_config.json.
Thread-safe med fil-locking för att undvika konflikter.
"""
import json
import os
import threading
from datetime import datetime
from typing import Dict, List, Optional
import logging

try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    # Windows doesn't have fcntl
    HAS_FCNTL = False

# Configure logger
logger = logging.getLogger("bevattning.zone_config")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    logger.addHandler(_handler)


class ZoneConfig:
    """
    Hanterar zonkonfiguration med JSON-persistence.
    Thread-safe och validerar mot hardware_map.csv.
    """
    
    def __init__(self, config_file: str = 'zone_config.json', hardware_map: str = 'hardware_map.csv'):
        """
        Initialisera ZoneConfig.
        
        Args:
            config_file: Sökväg till JSON-konfigurationsfil
            hardware_map: Sökväg till hardware_map.csv för validering
        """
        self.config_file = os.path.abspath(config_file)
        self.hardware_map = hardware_map
        self._lock = threading.RLock()
        self._valid_zones = self._load_valid_zones()
        self._config = self._load_or_create_config()
        logger.info("ZoneConfig initialiserad: %d enabled, %d disabled", 
                   len(self.get_enabled_zones()), 
                   len([z for z in self._valid_zones if not self.is_zone_enabled(z)]))
    
    def _load_valid_zones(self) -> List[int]:
        """
        Läs giltiga zon-ID från hardware_map.csv.
        Zoner är definierade som Valve_1 till Valve_7.
        
        Returns:
            Lista med giltiga zon-ID (1-7)
        """
        valid_zones = []
        
        # Kontrollera om hardware_map finns
        if not os.path.exists(self.hardware_map):
            logger.warning("hardware_map.csv saknas, använder standard zoner 1-7")
            return list(range(1, 8))
        
        try:
            import csv
            with open(self.hardware_map, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    variabel = row.get('Variabel', '')
                    if variabel.startswith('Valve_'):
                        try:
                            zone_id = int(variabel.split('_')[1])
                            valid_zones.append(zone_id)
                        except (ValueError, IndexError):
                            continue
            
            if valid_zones:
                valid_zones.sort()
                logger.debug("Laddade zoner från hardware_map.csv: %s", valid_zones)
                return valid_zones
            else:
                logger.warning("Inga zoner hittades i hardware_map.csv, använder standard 1-7")
                return list(range(1, 8))
        except Exception as e:
            logger.error("Fel vid läsning av hardware_map.csv: %s", e)
            return list(range(1, 8))
    
    def _validate_zone_id(self, zone_id: int) -> None:
        """
        Validera att zon-ID är giltigt.
        
        Args:
            zone_id: Zon-ID att validera
            
        Raises:
            ValueError: Om zon-ID är ogiltigt
        """
        if zone_id not in self._valid_zones:
            raise ValueError(f"Ogiltigt zon-ID {zone_id}. Giltiga zoner: {self._valid_zones}")
    
    def _load_or_create_config(self) -> Dict:
        """
        Läs konfiguration från fil eller skapa default.
        
        Returns:
            Konfigurationsdict
        """
        with self._lock:
            if os.path.exists(self.config_file):
                try:
                    with open(self.config_file, 'r', encoding='utf-8') as f:
                        if HAS_FCNTL:
                            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                        try:
                            config = json.load(f)
                            logger.info("Konfiguration laddad från %s", self.config_file)
                            return config
                        finally:
                            if HAS_FCNTL:
                                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                except Exception as e:
                    logger.error("Fel vid läsning av config: %s, skapar ny", e)
            
            # Skapa default config
            logger.info("Skapar default zonkonfiguration")
            return self._create_default_config()
    
    def _create_default_config(self) -> Dict:
        """
        Skapa default-konfiguration med alla zoner enabled.
        
        Returns:
            Default konfigurationsdict
        """
        now = datetime.now().isoformat()
        config = {
            "version": "1.0",
            "last_updated": now,
            "zones": {}
        }
        
        for zone_id in self._valid_zones:
            config["zones"][str(zone_id)] = {
                "enabled": True,
                "name": f"Zone {zone_id}",
                "last_modified": now
            }
        
        # Spara default config
        self._save_config(config)
        return config
    
    def _save_config(self, config: Optional[Dict] = None) -> None:
        """
        Spara konfiguration till fil med backup och thread-safety.
        
        Args:
            config: Konfiguration att spara (None = använd self._config)
        """
        if config is None:
            config = self._config
        
        config["last_updated"] = datetime.now().isoformat()
        
        with self._lock:
            # Skapa backup om filen finns
            if os.path.exists(self.config_file):
                backup_file = self.config_file + '.backup'
                try:
                    import shutil
                    shutil.copy2(self.config_file, backup_file)
                    logger.debug("Backup skapad: %s", backup_file)
                except Exception as e:
                    logger.warning("Kunde inte skapa backup: %s", e)
            
            # Skriv ny config
            try:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    if HAS_FCNTL:
                        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                        logger.debug("Konfiguration sparad till %s", self.config_file)
                    finally:
                        if HAS_FCNTL:
                            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except Exception as e:
                logger.error("Fel vid sparning av config: %s", e)
                # Försök återställa från backup
                backup_file = self.config_file + '.backup'
                if os.path.exists(backup_file):
                    try:
                        import shutil
                        shutil.copy2(backup_file, self.config_file)
                        logger.info("Konfiguration återställd från backup")
                    except Exception as e2:
                        logger.error("Kunde inte återställa från backup: %s", e2)
                raise
    
    def is_zone_enabled(self, zone_id: int) -> bool:
        """
        Kontrollera om en zon är enabled.
        
        Args:
            zone_id: Zon-ID (1-7)
            
        Returns:
            True om zon är enabled, False annars
            
        Raises:
            ValueError: Om zon-ID är ogiltigt
        """
        self._validate_zone_id(zone_id)
        
        with self._lock:
            zone_key = str(zone_id)
            if zone_key not in self._config.get("zones", {}):
                # Om zonen saknas i config, anta enabled
                logger.warning("Zon %d saknas i config, antar enabled", zone_id)
                return True
            
            return self._config["zones"][zone_key].get("enabled", True)
    
    def set_zone_enabled(self, zone_id: int, enabled: bool, name: Optional[str] = None) -> None:
        """
        Sätt zon som enabled eller disabled.
        
        Args:
            zone_id: Zon-ID (1-7)
            enabled: True för enabled, False för disabled
            name: Valfri beskrivning/namn
            
        Raises:
            ValueError: Om zon-ID är ogiltigt
        """
        self._validate_zone_id(zone_id)
        
        with self._lock:
            zone_key = str(zone_id)
            
            # Säkerställ att zonen finns i config
            if zone_key not in self._config.get("zones", {}):
                self._config.setdefault("zones", {})[zone_key] = {
                    "enabled": True,
                    "name": f"Zone {zone_id}",
                    "last_modified": datetime.now().isoformat()
                }
            
            # Uppdatera status
            old_enabled = self._config["zones"][zone_key].get("enabled", True)
            self._config["zones"][zone_key]["enabled"] = enabled
            self._config["zones"][zone_key]["last_modified"] = datetime.now().isoformat()
            
            if name is not None:
                self._config["zones"][zone_key]["name"] = name
            
            # Spara till disk
            self._save_config()
            
            # Logga ändringen
            status = "enabled" if enabled else "disabled"
            if old_enabled != enabled:
                if enabled:
                    logger.info("✅ Zone %d enabled", zone_id)
                else:
                    logger.warning("❌ Zone %d disabled", zone_id)
            else:
                logger.debug("Zone %d status oförändrad: %s", zone_id, status)
    
    def get_all_zones(self) -> Dict[int, Dict]:
        """
        Hämta alla zoner med deras status.
        
        Returns:
            Dict med zon-ID som nyckel och zondata som värde
        """
        with self._lock:
            result = {}
            for zone_id in self._valid_zones:
                zone_key = str(zone_id)
                if zone_key in self._config.get("zones", {}):
                    result[zone_id] = self._config["zones"][zone_key].copy()
                else:
                    # Default om zonen saknas
                    result[zone_id] = {
                        "enabled": True,
                        "name": f"Zone {zone_id}",
                        "last_modified": datetime.now().isoformat()
                    }
            return result
    
    def get_enabled_zones(self) -> List[int]:
        """
        Hämta lista med endast enabled zoner.
        
        Returns:
            Lista med zon-ID för enabled zoner
        """
        with self._lock:
            enabled = []
            for zone_id in self._valid_zones:
                if self.is_zone_enabled(zone_id):
                    enabled.append(zone_id)
            return enabled
    
    def get_disabled_zones(self) -> List[int]:
        """
        Hämta lista med endast disabled zoner.
        
        Returns:
            Lista med zon-ID för disabled zoner
        """
        with self._lock:
            disabled = []
            for zone_id in self._valid_zones:
                if not self.is_zone_enabled(zone_id):
                    disabled.append(zone_id)
            return disabled
    
    def toggle_zone(self, zone_id: int) -> bool:
        """
        Växla enabled/disabled status för en zon.
        
        Args:
            zone_id: Zon-ID (1-7)
            
        Returns:
            Ny status (True=enabled, False=disabled)
            
        Raises:
            ValueError: Om zon-ID är ogiltigt
        """
        self._validate_zone_id(zone_id)
        current_status = self.is_zone_enabled(zone_id)
        new_status = not current_status
        self.set_zone_enabled(zone_id, new_status)
        return new_status
