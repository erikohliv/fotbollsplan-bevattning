#!/usr/bin/env python3
"""
Test suite for zone_config.py
"""
import os
import json
import pytest
import tempfile
import shutil
from datetime import datetime
from zone_config import ZoneConfig


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def config_file(temp_dir):
    """Return path to temporary config file"""
    return os.path.join(temp_dir, 'test_zone_config.json')


@pytest.fixture
def hardware_map_file(temp_dir):
    """Create a temporary hardware_map.csv file"""
    hardware_map = os.path.join(temp_dir, 'test_hardware_map.csv')
    with open(hardware_map, 'w', encoding='utf-8') as f:
        f.write("Logisk_Adress,Fysisk_Port,Variabel,Typ,Hårdvara,Koppling_Plint,Funktion,Notering\n")
        f.write("%QX0.0,R1,Valve_1,DO,Solenoid 24V,X3:1,Bevattning,Zone 1\n")
        f.write("%QX0.1,R2,Valve_2,DO,Solenoid 24V,X3:2,Bevattning,Zone 2\n")
        f.write("%QX0.2,R3,Valve_3,DO,Solenoid 24V,X3:3,Bevattning,Zone 3\n")
        f.write("%QX0.3,R4,Valve_4,DO,Solenoid 24V,X3:4,Bevattning,Zone 4\n")
        f.write("%QX0.4,R5,Valve_5,DO,Solenoid 24V,X3:5,Bevattning,Zone 5\n")
        f.write("%QX0.5,R6,Valve_6,DO,Solenoid 24V,X3:6,Bevattning,Zone 6\n")
        f.write("%QX0.6,R7,Valve_7,DO,Solenoid 24V,X3:7,Bevattning,Zone 7\n")
    return hardware_map


def test_zone_config_creation(config_file, hardware_map_file):
    """Test att default config skapas korrekt"""
    zc = ZoneConfig(config_file=config_file, hardware_map=hardware_map_file)
    
    # Kontrollera att config-filen skapades
    assert os.path.exists(config_file), "Config-fil ska skapas"
    
    # Kontrollera att alla zoner är enabled som default
    for zone_id in range(1, 8):
        assert zc.is_zone_enabled(zone_id), f"Zone {zone_id} ska vara enabled som default"
    
    # Kontrollera enabled_zones listan
    enabled = zc.get_enabled_zones()
    assert len(enabled) == 7, "Alla 7 zoner ska vara enabled"
    assert sorted(enabled) == list(range(1, 8)), "Enabled zoner ska vara 1-7"


def test_enable_disable_zone(config_file, hardware_map_file):
    """Test att aktivera/inaktivera zon"""
    zc = ZoneConfig(config_file=config_file, hardware_map=hardware_map_file)
    
    # Inaktivera zon 5
    zc.set_zone_enabled(5, False, name="Zone 5 (Sönder spridare)")
    assert not zc.is_zone_enabled(5), "Zone 5 ska vara disabled"
    
    # Kontrollera att andra zoner är enabled
    assert zc.is_zone_enabled(1), "Zone 1 ska fortfarande vara enabled"
    assert zc.is_zone_enabled(7), "Zone 7 ska fortfarande vara enabled"
    
    # Aktivera zon 5 igen
    zc.set_zone_enabled(5, True)
    assert zc.is_zone_enabled(5), "Zone 5 ska vara enabled igen"
    
    # Kontrollera disabled_zones lista
    zc.set_zone_enabled(3, False)
    zc.set_zone_enabled(6, False)
    disabled = zc.get_disabled_zones()
    assert len(disabled) == 2, "Ska ha 2 disabled zoner"
    assert 3 in disabled, "Zone 3 ska vara disabled"
    assert 6 in disabled, "Zone 6 ska vara disabled"


def test_persistence(config_file, hardware_map_file):
    """Test att config sparas och laddas korrekt"""
    # Skapa första instansen och inaktivera några zoner
    zc1 = ZoneConfig(config_file=config_file, hardware_map=hardware_map_file)
    zc1.set_zone_enabled(2, False)
    zc1.set_zone_enabled(5, False, name="Zone 5 (Broken)")
    
    # Skapa ny instans som läser samma fil
    zc2 = ZoneConfig(config_file=config_file, hardware_map=hardware_map_file)
    
    # Kontrollera att status är samma
    assert not zc2.is_zone_enabled(2), "Zone 2 ska vara disabled efter reload"
    assert not zc2.is_zone_enabled(5), "Zone 5 ska vara disabled efter reload"
    assert zc2.is_zone_enabled(1), "Zone 1 ska vara enabled efter reload"
    
    # Kontrollera att namnet sparades
    all_zones = zc2.get_all_zones()
    assert all_zones[5]["name"] == "Zone 5 (Broken)", "Zone namn ska sparas"


def test_invalid_zone_id(config_file, hardware_map_file):
    """Test att ogiltiga zon-ID hanteras"""
    zc = ZoneConfig(config_file=config_file, hardware_map=hardware_map_file)
    
    # Testa ogiltiga zon-ID
    with pytest.raises(ValueError, match="Ogiltigt zon-ID"):
        zc.is_zone_enabled(0)
    
    with pytest.raises(ValueError, match="Ogiltigt zon-ID"):
        zc.is_zone_enabled(8)
    
    with pytest.raises(ValueError, match="Ogiltigt zon-ID"):
        zc.set_zone_enabled(10, False)


def test_get_all_zones(config_file, hardware_map_file):
    """Test att get_all_zones returnerar korrekt data"""
    zc = ZoneConfig(config_file=config_file, hardware_map=hardware_map_file)
    
    # Inaktivera en zon med custom namn
    zc.set_zone_enabled(4, False, name="Zone 4 (Maintenance)")
    
    all_zones = zc.get_all_zones()
    
    # Kontrollera struktur
    assert len(all_zones) == 7, "Ska returnera alla 7 zoner"
    assert 1 in all_zones, "Zone 1 ska finnas"
    assert 7 in all_zones, "Zone 7 ska finnas"
    
    # Kontrollera data för zon 4
    zone_4 = all_zones[4]
    assert zone_4["enabled"] is False, "Zone 4 ska vara disabled"
    assert zone_4["name"] == "Zone 4 (Maintenance)", "Zone 4 namn ska vara satt"
    assert "last_modified" in zone_4, "last_modified ska finnas"


def test_toggle_zone(config_file, hardware_map_file):
    """Test att toggle_zone växlar status korrekt"""
    zc = ZoneConfig(config_file=config_file, hardware_map=hardware_map_file)
    
    # Zone 3 är enabled från start
    assert zc.is_zone_enabled(3), "Zone 3 ska vara enabled"
    
    # Toggle till disabled
    new_status = zc.toggle_zone(3)
    assert new_status is False, "Toggle ska returnera False (disabled)"
    assert not zc.is_zone_enabled(3), "Zone 3 ska vara disabled efter toggle"
    
    # Toggle tillbaka till enabled
    new_status = zc.toggle_zone(3)
    assert new_status is True, "Toggle ska returnera True (enabled)"
    assert zc.is_zone_enabled(3), "Zone 3 ska vara enabled efter andra toggle"


def test_backup_creation(config_file, hardware_map_file):
    """Test att backup skapas vid uppdatering"""
    zc = ZoneConfig(config_file=config_file, hardware_map=hardware_map_file)
    
    # Gör en ändring (detta skapar backup)
    zc.set_zone_enabled(1, False)
    
    # Kontrollera att backup-fil skapades
    backup_file = config_file + '.backup'
    assert os.path.exists(backup_file), "Backup-fil ska skapas"
    
    # Läs backup och verifiera innehåll
    with open(backup_file, 'r', encoding='utf-8') as f:
        backup_data = json.load(f)
    
    assert "zones" in backup_data, "Backup ska innehålla zones"
    assert "version" in backup_data, "Backup ska innehålla version"


def test_missing_hardware_map(config_file, temp_dir):
    """Test att systemet fungerar utan hardware_map.csv"""
    # Använd en icke-existerande hardware_map
    non_existent_map = os.path.join(temp_dir, 'non_existent.csv')
    
    zc = ZoneConfig(config_file=config_file, hardware_map=non_existent_map)
    
    # Ska fortfarande ha zoner 1-7 som default
    enabled = zc.get_enabled_zones()
    assert len(enabled) == 7, "Ska ha 7 zoner även utan hardware_map"
    assert sorted(enabled) == list(range(1, 8)), "Ska ha zoner 1-7"


def test_concurrent_access(config_file, hardware_map_file):
    """Test thread-safety med concurrent access"""
    import threading
    
    zc = ZoneConfig(config_file=config_file, hardware_map=hardware_map_file)
    errors = []
    
    def set_zones_disabled():
        try:
            for zone_id in range(1, 8):
                zc.set_zone_enabled(zone_id, False)
        except Exception as e:
            errors.append(str(e))
    
    def set_zones_enabled():
        try:
            for zone_id in range(1, 8):
                zc.set_zone_enabled(zone_id, True)
        except Exception as e:
            errors.append(str(e))
    
    # Starta flera trådar som inaktiverar/aktiverar
    threads = []
    for i in range(10):
        if i % 2 == 0:
            t = threading.Thread(target=set_zones_disabled)
        else:
            t = threading.Thread(target=set_zones_enabled)
        threads.append(t)
        t.start()
    
    # Vänta på att alla trådar är klara
    for t in threads:
        t.join()
    
    # Kontrollera att inga fel uppstod
    assert len(errors) == 0, f"Inga fel ska uppstå vid concurrent access: {errors}"
    
    # Bekräfta att alla zoner har en status (inte att alla är enabled)
    all_zones = zc.get_all_zones()
    assert len(all_zones) == 7, "Alla 7 zoner ska finnas efter concurrent operations"


def test_json_structure(config_file, hardware_map_file):
    """Test att JSON-strukturen matchar specifikationen"""
    zc = ZoneConfig(config_file=config_file, hardware_map=hardware_map_file)
    
    # Inaktivera zon 5 med custom namn
    zc.set_zone_enabled(5, False, name="Zone 5 (Sönder spridare)")
    
    # Läs JSON direkt
    with open(config_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Kontrollera struktur
    assert "version" in data, "JSON ska ha version"
    assert data["version"] == "1.0", "Version ska vara 1.0"
    assert "last_updated" in data, "JSON ska ha last_updated"
    assert "zones" in data, "JSON ska ha zones"
    
    # Kontrollera zon-struktur
    zone_5 = data["zones"]["5"]
    assert "enabled" in zone_5, "Zon ska ha enabled"
    assert zone_5["enabled"] is False, "Zone 5 ska vara disabled"
    assert "name" in zone_5, "Zon ska ha name"
    assert zone_5["name"] == "Zone 5 (Sönder spridare)", "Zone namn ska matcha"
    assert "last_modified" in zone_5, "Zon ska ha last_modified"
    
    # Kontrollera timestamp format
    try:
        datetime.fromisoformat(zone_5["last_modified"])
    except ValueError:
        pytest.fail("last_modified ska vara i ISO format")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
