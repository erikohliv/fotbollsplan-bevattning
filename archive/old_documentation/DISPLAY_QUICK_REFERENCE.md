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

## Display 2 (2x8) - Manual Control & Mode Selection
**Location**: Operator panel  
**Type**: Interactive with 4 buttons (via PLC inputs DI11-DI14)  
**For complete irrigation control**

### Button Functions

```
    ┌───────┐
    │  OK   │  - Confirm / Advance (hold >2s on CONFIRM)
    └───────┘
┌───────┐ ┌───────┐
│ LEFT  │ │ RIGHT │  - Decrease/Increase value
└───────┘ └───────┘
    ┌───────┐
    │ BACK  │  - Go back / Cancel
    └───────┘
```

Buttons are read from PLC via Modbus (MW64).

### Complete Menu System

**Flow**: OVERVIEW → MODE → ZONE → TIME (if Manual) → CONFIRM → Execute

#### VIEW 1: OVERVIEW
```
A Z:2
OK:Menu
```
- **A/M**: Current system mode (Auto/Manual)
- **Z**: Current active zone (1-7)
- **P:ON/OFF**: Pump status when running
- **OK:Menu**: Press OK to enter menu system

#### VIEW 2: MODE SELECT
```
  Mode
 Manual
```
**Modes Available**:
- **Auto**: Full sequence (all zones, configured times)
- **Manual**: Single zone with custom time
- **Test**: Short test run on selected zone
- **Blow**: Blow-out mode on selected zone

**Controls**:
- **LEFT/RIGHT**: Cycle through modes
- **OK**: Confirm mode and advance to zone selection
- **BACK**: Return to overview

#### VIEW 3: ZONE SELECT
```
  Zone
   3
```
- **LEFT**: Decrease zone (1 ← 7)
- **RIGHT**: Increase zone (1 → 7)
- **OK**: Confirm zone (advances to TIME or CONFIRM based on mode)
- **BACK**: Return to mode selection
- **Range**: 1-7

**Note**: Zone selection skipped for Auto mode (runs all zones)

#### VIEW 4: TIME SELECT (Manual Mode Only)
```
  Time
 15min
```
- **LEFT**: Decrease time by 1 minute (min: 1)
- **RIGHT**: Increase time by 1 minute (max: 240)
- **OK**: Confirm time and advance to confirm screen
- **BACK**: Return to zone selection
- **Range**: 1-240 minutes

#### VIEW 5: CONFIRM
```
 M Z3 15m
 Hold OK
```
**Display Format**:
- **A All**: Auto mode (all zones)
- **M Z3 15m**: Manual zone 3, 15 minutes
- **T Z5**: Test mode zone 5
- **B Z2**: Blow mode zone 2

**Action**:
- **Hold OK >2s**: Execute selection and start irrigation
- **BACK**: Return to previous view (TIME or ZONE)

### Complete Operation Workflows

#### Auto Mode
1. **OVERVIEW** → Press OK
2. **MODE** → Select "Auto" → OK
3. **CONFIRM** "A All" → Hold OK >2s
4. System runs all zones with configured times

#### Manual Mode
1. **OVERVIEW** → Press OK
2. **MODE** → Select "Manual" → OK
3. **ZONE** → Choose zone (e.g., 3) → OK
4. **TIME** → Set minutes (e.g., 15) → OK
5. **CONFIRM** "M Z3 15m" → Hold OK >2s
6. System runs zone 3 for 15 minutes

#### Test Mode
1. **OVERVIEW** → Press OK
2. **MODE** → Select "Test" → OK
3. **ZONE** → Choose zone → OK
4. **CONFIRM** "T Z5" → Hold OK >2s
5. System runs short test on zone 5

#### Blow Mode (Winterization)
1. **OVERVIEW** → Press OK
2. **MODE** → Select "Blow" → OK
3. **ZONE** → Choose zone → OK
4. **CONFIRM** "B Z2" → Hold OK >2s
5. System runs blow-out on zone 2

### Quick Actions

| Task | Steps |
|------|-------|
| Check current status | View OVERVIEW display |
| Start auto watering | OK → Auto → OK → Hold OK |
| Manual zone 5, 20 min | OK → Manual → OK → Zone 5 → OK → 20 min → OK → Hold OK |
| Test zone 3 | OK → Test → OK → Zone 3 → OK → Hold OK |
| Cancel at any time | Press BACK button |

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
