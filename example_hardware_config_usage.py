#!/usr/bin/env python3
"""
Example script showing how to use hardware_config.json in the irrigation system.

This demonstrates:
- Loading the configuration
- Checking zone status
- Identifying high pressure zones
- Suggesting valve upgrades
"""
import json
from pathlib import Path


def load_hardware_config(config_path="hardware_config.json"):
    """Load and return the hardware configuration"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_zone_info(config, zone_id):
    """Get information for a specific zone"""
    for zone in config['zones']:
        if zone['zone_id'] == zone_id:
            return zone
    return None


def check_high_pressure_zones(config):
    """Identify zones with high pressure warnings"""
    high_pressure = []
    for zone in config['zones']:
        if zone['estimated_pressure_bar'] > 10:
            high_pressure.append(zone)
    return high_pressure


def suggest_valve_upgrade(config, zone_id):
    """Suggest valve upgrade for a zone if it has high pressure"""
    zone = get_zone_info(config, zone_id)
    if not zone:
        return f"Zone {zone_id} not found"
    
    if zone['estimated_pressure_bar'] > 10:
        current_valve = zone['valve_installed']
        fc_valve = config['component_catalog']['valves']['throttled']
        
        if current_valve == fc_valve['id']:
            return f"Zone {zone_id} already has Flow Control valve ({fc_valve['model']})"
        else:
            return (f"Zone {zone_id} ({zone['location']}): "
                   f"REKOMMENDATION - Byt till {fc_valve['model']} "
                   f"för att reducera tryck från {zone['estimated_pressure_bar']} bar")
    else:
        return f"Zone {zone_id} har optimalt tryck ({zone['estimated_pressure_bar']} bar)"


def main():
    """Main example function"""
    print("=== Fotbollsplan Bevattning - Hardware Configuration Example ===\n")
    
    # Load configuration
    config = load_hardware_config()
    print(f"Loaded configuration: {config['project_meta']['name']}")
    print(f"Last updated: {config['project_meta']['last_updated']}\n")
    
    # Display pump info
    pump = config['pump_station']
    print(f"Pump: {pump['model']}")
    print(f"  Power: {pump['specs']['power_kw']} kW")
    print(f"  Max Head: {pump['specs']['max_head_m']} m")
    print(f"  Max Flow: {pump['specs']['max_flow_l_min']} l/min")
    print(f"  ⚠️  {pump['constraints']['warning']}\n")
    
    # Display all zones
    print("Zones Overview:")
    print("-" * 80)
    for zone in config['zones']:
        status_icon = "✓" if "OPTIMAL" in zone['status'] else "⚠️"
        print(f"{status_icon} Zone {zone['zone_id']}: {zone['location']:25s} | "
              f"{zone['sprinkler']:20s} | "
              f"Flow: {zone['target_flow_l_min']:3d} l/min | "
              f"Pressure: {zone['estimated_pressure_bar']:4.1f} bar")
    print("-" * 80)
    print()
    
    # Check for high pressure zones
    high_pressure_zones = check_high_pressure_zones(config)
    if high_pressure_zones:
        print(f"⚠️  {len(high_pressure_zones)} zones with high pressure detected:\n")
        for zone in high_pressure_zones:
            print(f"  Zone {zone['zone_id']} ({zone['location']}): "
                  f"{zone['estimated_pressure_bar']} bar - {zone['status']}")
        print()
        
        # Suggest upgrades
        print("Rekommenderade åtgärder:")
        for zone in high_pressure_zones:
            print(f"  • {suggest_valve_upgrade(config, zone['zone_id'])}")
        print()
    
    # Example: Check specific zone
    print("\nExample: Checking Zone 4 details")
    zone4 = get_zone_info(config, 4)
    if zone4:
        print(f"  Location: {zone4['location']}")
        print(f"  Sprinkler: {zone4['sprinkler']}")
        print(f"  Current valve: {zone4['valve_installed']}")
        print(f"  Target flow: {zone4['target_flow_l_min']} l/min")
        print(f"  Estimated pressure: {zone4['estimated_pressure_bar']} bar")
        print(f"  Status: {zone4['status']}")
    
    print("\n✓ Configuration loaded and analyzed successfully!")


if __name__ == "__main__":
    main()
