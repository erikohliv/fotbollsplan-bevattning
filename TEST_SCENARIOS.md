# Test Scenarios for Markfuktgivare Integration

## Test Environment Setup

All tests can be run without connected hardware using the built-in simulation modes.

## 1. Dry-Run Mode Tests

### Test 1.1: Basic Dry-Run (No Modbus Writes)
```bash
python3 bevattning_controller.py --dry-run --auto-start
```

**Expected:**
- Weather data fetched from Open-Meteo
- No Modbus writes performed
- Log message: "=== DRY RUN MODE - Ingen Modbus-skrivning utförd ==="
- CSV log file created with status "not_written"

### Test 1.2: Dry-Run with Simulated Data
```bash
python3 bevattning_controller.py --simulate --dry-run --auto-start \
  --simulate-markfukt-value 45
```

**Expected:**
- Uses default weather (temp=15C, rain=0mm)
- Uses simulated moisture: 45%
- Log message: "Använder simulerad markfukt: 45%"
- No pulsing of Remote_Command
- Log message: "=== SIMULATE MODE: Skulle pulserat Remote_Command (MW10) ==="

## 2. Moisture Sensor Tests

### Test 2.1: Normal Moisture Level
```bash
python3 bevattning_controller.py --simulate --dry-run --auto-start \
  --simulate-markfukt-value 50
```

**Expected:**
- Moisture: 50% (below 80% threshold)
- Irrigation times: 60 min (center), 25 min (horn)
- Log message: "BEVATTNING KÖRNING: Normala förhållanden"

### Test 2.2: High Moisture - Blocking
```bash
python3 bevattning_controller.py --simulate --dry-run --auto-start \
  --simulate-markfukt-value 85 --moisture-threshold 80
```

**Expected:**
- Moisture: 85% (above 80% threshold)
- Irrigation times: 0 min (blocked)
- **WARNING** log: "BEVATTNING BLOCKERAD: Markfukt 85% >= 80"
- Log message: "=== BEVATTNING BLOCKERAD: Tider satta till 0 ==="

### Test 2.3: Moisture at Threshold
```bash
python3 bevattning_controller.py --simulate --dry-run --auto-start \
  --simulate-markfukt-value 80 --moisture-threshold 80
```

**Expected:**
- Moisture: 80% (exactly at threshold)
- Irrigation blocked (>= comparison)
- Irrigation times: 0 min

### Test 2.4: Custom Threshold
```bash
python3 bevattning_controller.py --simulate --dry-run --auto-start \
  --simulate-markfukt-value 70 --moisture-threshold 60
```

**Expected:**
- Moisture: 70% (above custom 60% threshold)
- Irrigation blocked
- Irrigation times: 0 min

## 3. Combined Condition Tests

### Test 3.1: High Moisture + Simulated Rain
```bash
python3 bevattning_controller.py --simulate --dry-run --auto-start \
  --simulate-markfukt-value 85
```

**Expected:**
- Multiple blocking conditions checked
- Rain check performed first (higher priority)
- If rain > threshold: blocked due to rain
- Else if moisture > threshold: blocked due to moisture

### Test 3.2: Low Temperature Reduction
```bash
python3 bevattning_controller.py --simulate --dry-run --auto-start \
  --simulate-markfukt-value 30 --temp-min 10
```

**Expected:**
- Temperature check happens (default temp=15C > 10C)
- Moisture OK (30% < 80%)
- Normal irrigation times

## 4. Event Logging Tests

### Test 4.1: Verify Enhanced Logging Output
```bash
python3 bevattning_controller.py --simulate --dry-run --auto-start \
  --simulate-markfukt-value 45 2>&1 | grep "==="
```

**Expected Output:**
```
=== Bevattningsscript Körning Startad ===
=== DRY RUN MODE - Ingen Modbus-skrivning utförd ===
=== SIMULATE MODE: Skulle pulserat Remote_Command (MW10) ===
```

### Test 4.2: Blocking Event Logging
```bash
python3 bevattning_controller.py --simulate --dry-run --auto-start \
  --simulate-markfukt-value 90 2>&1 | grep -E "WARNING|BLOCKERAD"
```

**Expected:**
```
WARNING: BEVATTNING BLOCKERAD: Markfukt 90% >= 80
=== BEVATTNING BLOCKERAD: Tider satta till 0 ===
```

### Test 4.3: CSV Log File
```bash
python3 bevattning_controller.py --simulate --dry-run --auto-start \
  --simulate-markfukt-value 45
tail -n 1 ~/bevattning_log.csv
```

**Expected Fields:**
- Timestamp
- temp=15.0
- rain24h=0.0
- moisture=45
- Normal drift
- 60 (tid_center)
- 25 (tid_horn)
- not_written

## 5. PLC Integration Tests (Requires Hardware/Modbus Simulator)

### Test 5.1: Analog Input Scaling (PLC Side)

**PLC Test Procedure:**
1. Set %IW0 (Analog input) to 0 → Expect MW30 = 0%
2. Set %IW0 to 13824 (mid-range) → Expect MW30 = 50%
3. Set %IW0 to 27648 (full scale) → Expect MW30 = 100%
4. Set %IW0 to 30000 (overflow) → Expect MW30 = 100% (clamped)

**Scaling Formula in PLC:**
```
MW30 = (IW0 * 100) / 27648
Clamped to 0-100%
```

### Test 5.2: Error Reset Functionality

**Via Python/API:**
```python
# Write to MW82 (ErrorReset)
write_register(82, 1)
time.sleep(0.5)
# Read MW73 (BlockReason)
block_reason = read_register(73)
# Expect: BlockReason cleared (0) if not E-stop
```

**Via FastAPI:**
```bash
curl -X POST -H "X-API-Key: <key>" \
  http://localhost:8000/menu/reset-error
```

**Expected:**
- MW82 pulsed (1 → 0)
- MW73 (BlockReason) cleared if not E-stop (4)
- Stuck sequences reset
- Anti-collision cleared if no sequence

### Test 5.3: Python Write to MW30 (Override Analog)

**Test Procedure:**
```bash
# Python writes directly to MW30 override analog sensor
python3 bevattning_controller.py --auto-start --simulate-markfukt-value 60
```

**Expected:**
- Python writes 60 to MW30
- PLC uses Python value (60%) instead of analog scaling
- BlockReason set if 60% >= threshold

## 6. Error Condition Tests

### Test 6.1: Modbus Connection Failure
```bash
python3 bevattning_controller.py --auto-start --host 192.168.99.99
```

**Expected:**
- Log: "Kunde inte ansluta till Modbus för skrivning."
- Script completes without crash
- CSV log shows "not_written"

### Test 6.2: Missing pymodbus
```bash
pip uninstall pymodbus -y
python3 bevattning_controller.py --simulate --dry-run --auto-start
```

**Expected:**
- Log: "pymodbus saknas — hoppar Modbus-skrivning"
- Script continues with simulation
- No crash

## 7. Loop Mode Tests

### Test 7.1: Loop Mode with Caching
```bash
python3 bevattning_controller.py --loop --interval 1 --simulate --dry-run --auto-start
# Let run for 2-3 iterations, then Ctrl+C
```

**Expected:**
- First iteration: Fetches weather (or fails gracefully)
- Subsequent iterations: Uses cached weather (within 10 min)
- Log: "Using cached weather data (age: X seconds)"
- Multiple CSV log entries

### Test 7.2: Exponential Backoff on Failures
```bash
python3 bevattning_controller.py --loop --interval 1 --auto-start \
  --host 192.168.99.99  # Invalid host
```

**Expected:**
- First failure: retry after 10s
- Second failure: retry after 20s
- Third failure: retry after 40s
- Max delay capped at 300s (default)

## Test Results Summary Template

| Test ID | Description | Status | Notes |
|---------|-------------|--------|-------|
| 1.1 | Basic Dry-Run | ✅ | |
| 1.2 | Simulated Data | ✅ | |
| 2.1 | Normal Moisture | ✅ | |
| 2.2 | High Moisture Block | ✅ | |
| 2.3 | Threshold Test | ✅ | |
| 2.4 | Custom Threshold | ✅ | |
| 3.1 | Combined Conditions | ⚠️ | Requires internet |
| 3.2 | Temperature Reduction | ✅ | |
| 4.1 | Enhanced Logging | ✅ | |
| 4.2 | Blocking Logs | ✅ | |
| 4.3 | CSV Logging | ✅ | |
| 5.1 | Analog Scaling | ⏳ | Requires hardware |
| 5.2 | Error Reset | ⏳ | Requires hardware |
| 5.3 | Python Override | ⏳ | Requires Modbus |
| 6.1 | Connection Failure | ✅ | |
| 6.2 | Missing Dependency | ✅ | |
| 7.1 | Loop with Cache | ✅ | |
| 7.2 | Exponential Backoff | ✅ | |

## Hardware Tests (Requires Physical Setup)

### Analog Sensor Wiring
```
Soil Moisture Sensor → UNIPI 1.1
  Signal (0-10V) → AI0 (%IW0)
  GND → GND
  +12V → Power supply
```

### Verification Steps:
1. Connect sensor to UNIPI AI0
2. Monitor MW30 register value
3. Manually vary soil moisture (dry soil → wet soil)
4. Verify MW30 changes from ~0% to ~100%
5. Verify PLC blocks irrigation when MW30 > MoistureThreshold

### Reset Button Test (if physical button added):
1. Create fault condition (simulate E-stop or high moisture)
2. Press physical reset button
3. Verify BlockReason clears
4. Verify sequence resets if stuck

---

## Notes

- All simulation tests can be run **without hardware**
- Hardware tests require UNIPI 1.1 and Raspberry Pi
- API tests require running FastAPI server
- Modbus tests require PLC/Modbus simulator or actual hardware
- Tests marked ✅ have been validated in dry-run mode
- Tests marked ⏳ require hardware setup
- Tests marked ⚠️ may have external dependencies
