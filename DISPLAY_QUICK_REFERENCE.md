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
**Type**: Interactive with 4 buttons (via PLC inputs DI11-DI14)  
**For manual zone control**

### Button Functions

```
    ┌───────┐
    │  OK   │  - Confirm (hold >2s)
    └───────┘
┌───────┐ ┌───────┐
│ LEFT  │ │ RIGHT │  - Decrease/Increase zone
└───────┘ └───────┘
    ┌───────┐
    │ BACK  │  - Cancel/Back
    └───────┘
```

Buttons are read from PLC via Modbus (MW64).

### View Navigation
**OK**: Enter zone selection  
**BACK**: Return to overview  
**LEFT/RIGHT**: Adjust zone when in selection view

Views: OVERVIEW → ZONE SELECTION → OVERVIEW

### View Details

#### VIEW 1: OVERVIEW
```
A Z:2
P:ON
```
- **A/M**: Auto/Manual mode
- **Z**: Current zone (1-7)
- **P**: Pump (ON/OFF)
- **Press OK** to enter zone selection

#### VIEW 2: ZONE SELECTION
```
Zone
  3
```
- **RIGHT**: Increment zone (7→1 wrap)
- **LEFT**: Decrement zone (1→7 wrap)
- **OK (hold >2s)**: Confirm zone selection
- **BACK**: Cancel and return to overview
- **Range**: 1-7

**Note:** Manual mode uses auto-configured times (Set_Tid_Center/Horn)

### Manual Operation Workflow

1. **Press OK** to enter zone selection
2. **Press LEFT/RIGHT** to select zone (1-7)
3. **Hold OK >2s** to confirm zone
4. **Press physical START button** or trigger via API
5. Display shows OVERVIEW with active zone

### Quick Actions

| Task | Steps |
|------|-------|
| Check current status | View OVERVIEW display |
| Select zone 5 | OK → LEFT/RIGHT to 5 → Hold OK >2s |
| Cancel selection | Press BACK |
| View system mode | Check OVERVIEW, see A/M indicator |

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
| Buttons don't work | Check PLC Modbus connection, verify DI11-DI14 wiring |
| Values won't change | Verify in Zone Selection view, check Modbus MW64 |

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
