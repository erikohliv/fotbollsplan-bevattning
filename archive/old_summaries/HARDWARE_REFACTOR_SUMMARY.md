# Hardware Refactor Implementation Summary

## Overview
This document summarizes the major hardware refactor implementation based on the updated `documentation/forbindningstabell.csv` (Single Source of Truth).

**Date**: 2025-12-20  
**Branch**: `copilot/refactor-hardware-implementation`

---

## Hardware Changes Implemented

### 1. Pump Control System
**Before**: Siemens LOGO! PLC controlling VFD (Variable Frequency Drive)  
**After**: Direct control via UNIPI Relä 8 → Soft Starter

- Removed all references to "Siemens LOGO" and "VFD"
- Updated to "Mjukstartare (Soft Starter)"
- Pump now controlled directly by PLC output `%QX0.7` (Relä 8)
- Modbus register MW100 still used for control, but hardware path simplified

### 2. Menu Button Input System
**Before**: 4 buttons connected to Raspberry Pi GPIO pins (17, 27, 22, 23)  
**After**: 4 buttons connected to UNIPI PLC inputs (DI11-DI14)

Button mapping changes:
| Button | Old GPIO | New PLC Input | Modbus |
|--------|----------|---------------|--------|
| Left   | GPIO 17  | DI11 (%IX1.2) | MW64 bit0 |
| Right  | GPIO 27  | DI12 (%IX1.3) | MW64 bit1 |
| OK     | GPIO 22  | DI13 (%IX1.4) | MW64 bit2 |
| Back   | GPIO 23  | DI14 (%IX1.5) | MW64 bit3 |

Buttons are now read via Modbus register MW64 as a bitmask.

### 3. Sensor Terminal X3 (New)
Added new sensor terminal for external connections:

| Sensor | PLC Input | Modbus Register | Purpose |
|--------|-----------|-----------------|---------|
| Flow Switch | DI6 (%IX0.6) | MW55 | Dry-run protection |
| Pressure Sensor | AI2 (%IW1) | MW33 | Pump pressure monitoring (0-100%) |

### 4. Auto/Manual Mode Switch
**Before**: Single input `%IX0.2` (Mode_AutoManual)  
**After**: Two separate inputs from 1-0-2 spring-return switch

| Mode | PLC Input | Description |
|------|-----------|-------------|
| Auto | DI3 (%IX0.2) | Auto mode position |
| Manual | DI10 (%IX1.1) | Manual mode position |
| Neutral | Both LOW | Default/neutral position |

The PLC now reads both inputs and sets mode based on which one is HIGH.

---

## Files Modified

### Core Code Files

#### 1. `Fotbollsplan_Master_Version12.st` (PLC Program)
**Major Changes**:
- Updated header documentation with hardware refactor notes
- Removed obsolete inputs: `Display_Button_1`, `Display_Button_2`, `Mode_AutoManual`, `Manual_NextZone`, `Blow_Button`
- Added new inputs: `Mode_Auto`, `Mode_Manual`, `Flow_Switch`, `Reset_Button`, `Menu_Left`, `Menu_Right`, `Menu_OK`, `Menu_Back`
- Added analog input: `Analog_Pressure_Raw` (AI2)
- Updated Modbus registers (see Modbus Register Changes section)
- Added logic to read pressure sensor and scale to 0-100%
- Added logic to read flow switch status to MW55
- Added logic to read menu buttons and pack into bitmask at MW64
- Updated mode switch logic to handle two separate inputs

#### 2. `api_main.py` (FastAPI Backend)
**Major Changes**:
- Updated Modbus register constants to match new PLC mappings:
  ```python
  MW_PRESSURE = 33            # New: Tryckgivare (was AutoOverride)
  MW_AUTO_OVERRIDE = 34       # Moved from 33
  MW_REGEN_THRESHOLD = 35     # Moved from 34
  MW_MOISTURE_THRESHOLD = 36  # Moved from 35
  MW_FLOW_SWITCH = 55         # New: Flödesvakt status
  MW_MENU_BUTTONS = 64        # Changed from ManualRunTimeReg
  ```

#### 3. `display_manager.py` (Display Control)
**Major Changes**:
- Removed all GPIO-related code (RPi.GPIO imports, GPIO initialization, cleanup)
- Replaced `read_buttons()` to read from Modbus register MW64 instead of GPIO
- Updated button names: `up`/`down` → `left`/`right`/`ok`/`back`
- Updated button handling logic:
  - `ok`: Enter zone selection / Confirm (long press >2s)
  - `left`: Decrease zone
  - `right`: Increase zone
  - `back`: Return to overview
- Updated Modbus register constants to match API

#### 4. `test_display_manager.py` (Unit Tests)
**Major Changes**:
- Updated button test cases to use new button names
- Added MW55 (Flow Switch) and MW33 (Pressure) to MockModbusClient
- Updated MW64 to represent menu buttons bitmask (was manual time)
- Fixed all assertions to work with new button layout

### Documentation Files

#### 5. `README.md` (Main Documentation)
**Sections Updated**:
- **Architecture**: Updated hardware description, removed LOGO reference
- **I/O Mapping**: Complete rewrite with new digital inputs and analog inputs
- **Modbus Registers**: Added MW33, MW55, MW64 documentation; moved MW34-36
- **Sequence & Anti-vattenslag**: Added flow switch protection, updated button references
- **Rekommenderad drift**: Updated pump control description

#### 6. `DISPLAY_MANAGER.md` (Display Manager Documentation)
**Sections Updated**:
- **Hardware Requirements**: Changed GPIO buttons to PLC Modbus buttons
- **Installation**: Removed GPIO/RPi.GPIO requirements
- **Configuration**: Replaced GPIO pin configuration with Modbus button mapping
- **Troubleshooting**: Changed GPIO tests to Modbus tests
- **Code Structure**: Updated Display2Manager description
- **Examples**: Replaced custom GPIO pin example with Modbus configuration

#### 7. `DISPLAY_QUICK_REFERENCE.md` (Quick Reference)
**Sections Updated**:
- **Button Functions**: Updated button layout diagram and descriptions
- **View Navigation**: Changed from 3 views (OVERVIEW/ZONE/TIME) to 2 views (OVERVIEW/ZONE)
- **Manual Operation Workflow**: Completely rewritten for new button layout
- **Quick Actions**: Updated all button references
- **Troubleshooting**: Changed GPIO connection checks to PLC Modbus checks

---

## Modbus Register Changes

### Register Mappings (Before → After)

| Register | Old Usage | New Usage | Notes |
|----------|-----------|-----------|-------|
| MW33 | AutoOverride | Pressure_Value | **MOVED**: Pressure sensor reading (0-100%) |
| MW34 | RegenThreshold_mm | AutoOverride | **MOVED FROM MW33** |
| MW35 | MoistureThreshold | RegenThreshold_mm | **MOVED FROM MW34** |
| MW36 | *(unused)* | MoistureThreshold | **MOVED FROM MW35** |
| MW55 | *(unused)* | FlowSwitchStatus | **NEW**: Flow switch (0=no flow, 1=flow OK) |
| MW64 | ManualRunTimeReg | MenuButtonsReg | **CHANGED**: Now bitmask for menu buttons |

### MW64 Bitmask Format

```
bit0 (0x01): LEFT button   (DI11)
bit1 (0x02): RIGHT button  (DI12)
bit2 (0x04): OK button     (DI13)
bit3 (0x08): BACK button   (DI14)
```

Example: `MW64 = 0x05` means LEFT and OK buttons are pressed.

---

## PLC I/O Changes Summary

### Digital Inputs

| Old I/O | Old Name | New I/O | New Name | Notes |
|---------|----------|---------|----------|-------|
| %IX0.2 | Mode_AutoManual | %IX0.2 | Mode_Auto | **Split**: Now only Auto position |
| *(none)* | *(none)* | %IX1.1 | Mode_Manual | **New**: Manual position of 1-0-2 switch |
| %IX0.3 | Manual_NextZone | %IX0.3 | Reset_Button | **Changed**: Now Reset/Acknowledge |
| %IX0.4 | Display_Button_1 | *(removed)* | *(removed)* | **Removed**: Moved to PLC |
| %IX0.6 | Blow_Button | %IX0.6 | Flow_Switch | **Changed**: Now flow sensor |
| %IX1.0 | Display_Button_2 | *(removed)* | *(removed)* | **Removed**: Moved to PLC |
| *(none)* | *(none)* | %IX1.2 | Menu_Left | **New**: Menu button |
| *(none)* | *(none)* | %IX1.3 | Menu_Right | **New**: Menu button |
| *(none)* | *(none)* | %IX1.4 | Menu_OK | **New**: Menu button |
| *(none)* | *(none)* | %IX1.5 | Menu_Back | **New**: Menu button |

### Analog Inputs

| I/O | Name | Usage |
|-----|------|-------|
| %IW0 | Analog_Markfukt_Raw | Soil moisture (0-10V → 0-100%) |
| %IW1 | Analog_Pressure_Raw | **NEW**: Pressure sensor (0-10V → 0-100%) |

### Digital Outputs

| I/O | Name | Connection |
|-----|------|------------|
| %QX0.0-6 | Ventil_1..7 | Valve solenoids |
| %QX0.7 | Signal_Pump | **CHANGED**: Now to Soft Starter (was LOGO!) |

---

## Testing Performed

### Unit Tests
✅ All unit tests passing in `test_display_manager.py`:
- Modbus integration tests
- Display rendering tests
- Button handling tests (updated for new layout)
- Zone selection and confirmation tests
- Auto-scheduler tests

### Manual Testing Recommendations

1. **PLC Compilation**
   - Compile `Fotbollsplan_Master_Version12.st` in your PLC IDE
   - Verify no syntax errors
   - Upload to UNIPI PLC

2. **Menu Button Testing**
   - Press each physical button (DI11-DI14)
   - Read MW64 via Modbus
   - Verify bitmask values

3. **Flow Switch Testing**
   - Connect flow switch to DI6
   - Start pump with no flow → MW55 should be 0
   - Ensure water flow → MW55 should be 1

4. **Pressure Sensor Testing**
   - Connect pressure sensor to AI2
   - Read MW33 via Modbus
   - Verify 0-100% scaling

5. **Mode Switch Testing**
   - Set physical switch to Auto position → DI3 HIGH, DI10 LOW
   - Set physical switch to Manual position → DI3 LOW, DI10 HIGH
   - Set physical switch to Neutral → both LOW

6. **Display Manager Testing**
   ```bash
   python3 test_display_manager.py
   ```

7. **Integration Testing**
   - Start display manager service
   - Verify menu navigation works via PLC buttons
   - Test zone selection and confirmation
   - Verify pump control via Relä 8

---

## Migration Notes

### For System Administrators

1. **Hardware Wiring Changes Required**:
   - Disconnect menu buttons from Raspberry Pi GPIO
   - Connect menu buttons to UNIPI DI11-DI14
   - Connect flow switch to UNIPI DI6
   - Connect pressure sensor to UNIPI AI2
   - Rewire Auto/Man switch to provide two separate signals (DI3, DI10)
   - Change pump control from LOGO input to Soft Starter input

2. **Software Update**:
   - Pull latest code from `copilot/refactor-hardware-implementation` branch
   - Upload new PLC program to UNIPI
   - Restart display-manager service:
     ```bash
     sudo systemctl restart display-manager
     ```
   - Restart API service:
     ```bash
     sudo systemctl restart bevattning-api
     ```

3. **Configuration Verification**:
   - Check Modbus connectivity: `python3 -c "from pymodbus.client import ModbusTcpClient; c = ModbusTcpClient('127.0.0.1'); print(c.connect())"`
   - Verify I2C displays: `i2cdetect -y 1`
   - Test button reading: Read MW64 while pressing buttons

### Backward Compatibility

**⚠️ Breaking Changes**:
- Old GPIO button wiring will not work
- Old Modbus register addresses for MW33-36 have changed
- Manual time setting (MW64) is removed - manual mode now uses auto times

**No Impact On**:
- FastAPI endpoints (same functionality, different registers internally)
- Auto-watering scheduler
- Weather data integration (bevattning_controller.py)

---

## Security Considerations

### Flow Switch Protection
The new flow switch (DI6 → MW55) provides dry-run protection:
- Monitor MW55 during pump operation
- If MW55 = 0 (no flow) while pump is running → potential dry-run condition
- Consider adding logic to stop pump after X seconds with no flow

**Recommended PLC Enhancement** (future):
```structured-text
(* In pump control logic *)
IF Signal_Pump AND (FlowSwitchStatus = 0) THEN
  Tmr_FlowTimeout(IN := TRUE, PT := T#30s);
  IF Tmr_FlowTimeout.Q THEN
    Signal_Pump := FALSE; (* Stop pump - no flow detected *)
    BlockReason := 5; (* New code: Flow switch timeout *)
  END_IF;
ELSE
  Tmr_FlowTimeout(IN := FALSE, PT := T#30s);
END_IF;
```

---

## Future Enhancements

Potential improvements to consider:

1. **Flow Switch Integration**:
   - Add flow timeout logic in PLC
   - Add flow alarm to EventMask
   - Display flow status on LCD

2. **Pressure Monitoring**:
   - Add pressure thresholds (min/max)
   - Alert on low/high pressure
   - Log pressure trends

3. **Menu Button Feedback**:
   - Add visual feedback on LCD when button pressed
   - Add hold-duration indicator for OK button

4. **Soft Starter Integration**:
   - Add feedback from soft starter (run status, faults)
   - Monitor motor current if available

---

## References

- **Hardware Definition**: `documentation/forbindningstabell.csv`
- **PLC Program**: `Fotbollsplan_Master_Version12.st`
- **API Code**: `api_main.py`
- **Display Manager**: `display_manager.py`
- **Main Documentation**: `README.md`

---

## Contact

For questions or issues with this hardware refactor:
- Check GitHub Issues
- Review this summary document
- Refer to updated README.md and DISPLAY_MANAGER.md

**End of Hardware Refactor Summary**
