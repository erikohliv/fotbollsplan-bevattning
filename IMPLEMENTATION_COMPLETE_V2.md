# Hardware Refactor V2 - Implementation Summary

## Status: ✅ COMPLETE

Implementation date: 2026-01-01

## Overview
This document summarizes the complete hardware refactor V2 for the fotbollsplan-bevattning irrigation control system. All planned changes have been successfully implemented and code-reviewed.

## Changes Implemented

### 1. Hardware Input Mapping (hardware_map.csv) ✅
**Complete remap of digital inputs to match new control panel:**

| Old Mapping | New Mapping | Change Description |
|-------------|-------------|-------------------|
| DI3 (Switch_Auto) | I05 (Button_Set_Auto) | 1-0-2 switch → Pulse button |
| DI10 (Switch_Manual) | I06 (Button_Set_Manual) | 1-0-2 switch → Pulse button |
| DI8 (E_Stop) | I03 (E_Stop) | Pin reassignment |
| - | I08 (Soft_Starter_Fault) | **NEW** - Fault signal |
| - | I10 (Motor_Protection) | **NEW** - Critical alarm |
| - | A2 (Soil_Temperature) | **NEW** - Temperature sensor |

### 2. PLC Logic (Fotbollsplan_Master_Version12.st) ✅

#### Auto/Manual Latch Logic
```structured-text
(* Edge detection for I05 Auto button *)
IF Button_Set_Auto AND NOT Prev_Button_Set_Auto THEN
  System_Mode_Latched := 1;  (* Auto *)
  ModeIsAuto := TRUE;
  ModeRegister := 1;
END_IF;

(* Edge detection for I06 Manual button *)
IF Button_Set_Manual AND NOT Prev_Button_Set_Manual THEN
  System_Mode_Latched := 0;  (* Manual *)
  ModeIsAuto := FALSE;
  ModeRegister := 0;
END_IF;
```

#### Motor Protection (I10)
- **Trigger:** Rising edge on I10
- **Action:** Immediate pump stop, BlockReason=7, EventMask bit 5
- **Reset:** Requires I10 inactive + reset button

#### Soft Starter Fault (I08)
- **Trigger:** Rising edge on I08
- **Action:** Immediate pump stop, BlockReason=8
- **Priority:** Respects E-stop(4) and Motor Protection(7), overrides all others
- **Reset:** Automatic when I08 goes low

#### Soil Temperature (A2)
- Reads from %IW1 (0-10V analog input)
- Stores raw value in MW37
- Scaling/conversion can be done in Python or PLC based on sensor specs

### 3. Python/FastAPI Updates ✅

#### New Modbus Registers (api_main.py)
```python
MW_SOIL_TEMP_RAW = 37        # Soil temperature raw (0-27648)
MW_MODE_OVERRIDE = 60        # Latched Auto/Manual state
MW_EVENTMASK = 72            # bit5=Motor Protection (new)
MW_BLOCK_REASON = 73         # codes 7 & 8 added
```

#### Block Reason Priority
```
0 = OK
1 = Rain threshold
2 = Moisture threshold
3 = Anti-collision
4 = E-stop (highest)
5 = Pressure fault
6 = Flow fault
7 = Motor protection (critical)
8 = Soft starter fault (high)
```

### 4. Display Manager (display_manager.py) ✅

#### Removed
- Display2Manager class (deprecated, kept for compatibility)
- Display2View enum
- Menu button Modbus reading (DI11-DI14)

#### Added
- **ArcadeButtonManager** class
  - I2C address: 0x20 (configurable)
  - Security lock: 10 min timeout
  - Unlock sequence support
  - **NOTE:** `read_buttons()` is placeholder - must be adapted to actual hardware

### 5. Weather & Seasonal Logic (bevattning_controller.py) ✅

#### Location Update
```python
DEFAULT_LATITUDE = "56.05"    # Håkanryd, Bromölla
DEFAULT_LONGITUDE = "14.40"   # Håkanryd, Bromölla
```

#### Seasonal Checks
- **Winter block** (Dec-Mar): No watering allowed
- **October warning** (Oct 15-31): Blowout reminder
- **Spring reminder** (April): System activation check

#### Fallback Prompts
When API or sensors fail, user is prompted:
1. **Run on Sensor** - Use sensor data only
2. **Force Ready** - Override all checks
3. **Abort** - Cancel watering

## Implementation Quality

### Code Review Results ✅
All code review issues addressed:
- [x] I2C address 0x20 documented with conflict warnings
- [x] PLC comment (%IX1.0 - I09) corrected
- [x] Soft starter priority logic fixed
- [x] Placeholder I2C implementation prominently marked

### Documentation ✅
- **HARDWARE_REFACTOR_V2.md**: Comprehensive hardware guide
  - Input/output mapping
  - Latch logic explanation
  - Motor protection details
  - I2C device notes with conflict warnings
  - Migration guide from V1
  - Testing procedures

## Testing Required

### Critical Tests
- [ ] **Mode latch verification**: Press I05 → verify MW60=1, press I06 → verify MW60=0
- [ ] **Motor protection response**: Simulate I10 high → verify pump stop + BlockReason=7
- [ ] **Soft starter fault**: Simulate I08 high → verify pump stop + BlockReason=8
- [ ] **Emergency stop**: Test I03 → verify system stop + BlockReason=4
- [ ] **Reset logic**: Test MW82 with various BlockReasons

### Hardware Integration
- [ ] **I2C arcade buttons**: 
  - Run `sudo i2cdetect -y 1` to verify address
  - Implement actual hardware protocol in `ArcadeButtonManager.read_buttons()`
  - Test button reading and security lock
- [ ] **Soil temperature**: Verify A2 analog input and MW37 reading
- [ ] **Display 1**: Verify continued operation without Display 2

### Seasonal & Fallback
- [ ] **Winter block**: Test in December - should prevent watering
- [ ] **Blowout warning**: Test Oct 15-31 - should show warning
- [ ] **API fallback**: Disconnect network → verify user prompt
- [ ] **Sensor fallback**: Disconnect sensor → verify user prompt

## Deployment Checklist

### Pre-deployment
1. [ ] Verify PLC firmware can be updated with new code
2. [ ] Backup existing PLC program
3. [ ] Test new code on bench/simulator if available
4. [ ] Verify all hardware is connected per new mapping

### Deployment
1. [ ] Upload new PLC program (Fotbollsplan_Master_Version12.st)
2. [ ] Deploy Python updates to Raspberry Pi
3. [ ] Restart API service: `sudo systemctl restart bevattning-api`
4. [ ] Restart display manager: `sudo systemctl restart display-manager`

### Post-deployment
1. [ ] Verify PLC is running (check MW70 heartbeat)
2. [ ] Test mode switching (I05/I06 buttons)
3. [ ] Verify API endpoints respond correctly
4. [ ] Test seasonal checks (if applicable)
5. [ ] Monitor system for 24 hours

## Known Issues / Future Work

### Arcade Button Implementation
- **Current status**: Placeholder I2C read implementation
- **Action required**: Update `ArcadeButtonManager.read_buttons()` to match actual hardware
- **Priority**: HIGH - Required for production use
- **Recommendation**: Determine button controller type (PCF8574, MCP23008, etc.) and implement accordingly

### I2C Address Conflict
- **Issue**: Default 0x20 may conflict with other I2C devices
- **Mitigation**: Documented in HARDWARE_REFACTOR_V2.md
- **Action**: Verify with `i2cdetect`, reconfigure if needed

### Display 2 Compatibility
- **Status**: Display2Manager kept but deprecated
- **Action**: Can be fully removed in future version after arcade buttons proven working

## Rollback Plan

If issues arise:
1. Restore PLC backup from pre-deployment
2. Revert git commit: `git revert ce3e021`
3. Redeploy previous version
4. Document issue for investigation

## Contacts & Support

- **GitHub Issues**: https://github.com/erikohliv/fotbollsplan-bevattning/issues
- **Documentation**: See HARDWARE_REFACTOR_V2.md
- **PLC Code**: Fotbollsplan_Master_Version12.st

## Conclusion

All hardware refactor V2 requirements have been successfully implemented:
- ✅ New input mapping with latch logic
- ✅ Motor protection and soft starter fault handling
- ✅ Arcade button framework (hardware-specific code pending)
- ✅ Seasonal checks and fallback prompts
- ✅ Comprehensive documentation
- ✅ Code review issues resolved

**Next steps**: Complete hardware testing and implement arcade button protocol.
