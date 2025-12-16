# Display Quick Reference Card

## Display 1 (20x4) - Status Monitor
**Location**: Main control panel  
**Type**: Auto-rotating (4 views, 4-second interval)  
**No user interaction required**

### View Rotation Sequence

#### 1. STATUS VIEW
```
Mode   Zone    Pump
Stage  Heartbeat
Temperature Moisture Rain
Status
```

#### 2. BLOCK CONDITIONS
```
Current blocking conditions
Moisture percentage
Rain forecast
Block reason
```

#### 3. PUMP STATE
```
Detailed pump information
Current zone
Stage number
```

#### 4. CONNECTIVITY
```
Modbus status
System heartbeat
Current time
```

---

## Display 2 (2x8) - Manual Control
**Location**: Operator panel  
**Type**: Interactive with 4 buttons  
**For manual zone control**

### Button Functions

```
    ┌───────┐
    │  UP   │  - Increment value
    └───────┘
┌───────┐ ┌───────┐
│ LEFT  │ │ RIGHT │  - Switch views
└───────┘ └───────┘
    ┌───────┐
    │ DOWN  │  - Decrement value
    └───────┘
```

### View Navigation
**LEFT**: ← Previous view  
**RIGHT**: → Next view  
Views cycle: OVERVIEW → ZONE → TIME → OVERVIEW

### View Details

#### VIEW 1: OVERVIEW
```
A Z:2
P:ON
```
- **A/M**: Auto/Manual mode
- **Z**: Current zone (1-7)
- **P**: Pump (ON/OFF)
- **No editing**

#### VIEW 2: ZONE SELECTION
```
Zone
  3
```
- **UP**: Next zone (7→1)
- **DOWN**: Previous zone (1→7)
- **Range**: 1-7

#### VIEW 3: TIME SELECTION
```
Time
 15min
```
- **UP**: +1 minute
- **DOWN**: -1 minute
- **Range**: 1-240 min

### Manual Operation Workflow

1. **Press RIGHT** until "Zone" appears
2. **Press UP/DOWN** to select zone (1-7)
3. **Press RIGHT** to "Time" view
4. **Press UP/DOWN** to set minutes (1-240)
5. **Trigger manual start** via PLC or API
6. Display returns to OVERVIEW

### Quick Actions

| Task | Steps |
|------|-------|
| Check current status | Wait for OVERVIEW or press LEFT/RIGHT to find it |
| Select zone 5 | RIGHT to Zone → UP/DOWN to 5 |
| Set 10 minutes | RIGHT to Time → UP/DOWN to 10 |
| View system mode | LEFT/RIGHT to OVERVIEW, check A/M |

---

## Auto-Watering Schedule

**Default Time**: 01:00 (1:00 AM)  
**Frequency**: Once per day  
**Conditions Checked**:
- ☂️ Rain forecast < threshold
- 💧 Soil moisture < threshold
- 🔄 System not busy
- 🛑 No emergency stop

**Status on Display 1**: View 2 shows block reason if watering is prevented

---

## Troubleshooting

### Display 1 Issues
| Problem | Solution |
|---------|----------|
| No text | Check I2C address (default: 0x27) |
| Not rotating | Check if service is running |
| Shows error | Check Modbus connection |

### Display 2 Issues
| Problem | Solution |
|---------|----------|
| No text | Check I2C address (default: 0x3F) |
| Buttons don't work | Check GPIO connections |
| Values won't change | Verify correct view (Zone/Time) |

### General
| Problem | Solution |
|---------|----------|
| Both displays blank | Check I2C: `i2cdetect -y 1` |
| Old data showing | Check Modbus connection to PLC |
| Service not running | `sudo systemctl start display-manager` |

---

## Service Commands

```bash
# Check status
sudo systemctl status display-manager

# Start service
sudo systemctl start display-manager

# Stop service
sudo systemctl stop display-manager

# Restart service
sudo systemctl restart display-manager

# View logs
journalctl -u display-manager -f
```

---

## Contact & Support

See **DISPLAY_MANAGER.md** for detailed documentation  
See **IMPLEMENTATION_SUMMARY.md** for technical details  
See **README.md** for system overview

---

**Version**: 1.0  
**Updated**: 2025-12-16  
**Compatible**: Raspberry Pi 3+, Python 3.7+
