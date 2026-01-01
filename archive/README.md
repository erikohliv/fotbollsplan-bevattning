# Archive - System 1.0 Obsolete Files

## 📚 Purpose
This directory contains files from System 1.0 that are no longer actively used in System 2.0, but are preserved for historical reference and project documentation.

## 🔄 System Transition
These files were archived during the transition from **System 1.0** to **System 2.0**, which involved significant architectural changes:

### Major Changes in System 2.0:
- **Display 2 (D2) Removed**: According to `.github/copilot-instructions.md`, Display 2 has been removed from the system
- **New User Interface**: Physical control now uses 4 Arcade Buttons via I2C (PCF8574)
- **Simplified Architecture**: Streamlined system focusing on core functionality
- **Updated Documentation**: Active documentation moved to root level for easier access

## 📁 Directory Structure

### `old_documentation/`
Contains obsolete documentation files related to System 1.0 features:
- Display manager documentation (D2-related)
- Old installation guides and feature documentation
- Zone comparison and indexing documentation that has been superseded

**Files:**
- `DISPLAY_MANAGER.md`
- `DISPLAY_QUICK_REFERENCE.md`
- `DEPLOYMENT_SETUP.md`
- `INSTALL_FEATURES.md`
- `INSTALL_FLOW.md`
- `INSTALL_SUMMARY.md`
- `INDEX_ZONE_DOCUMENTATION.md`
- `QUICK_ANSWER_ZONE_COMPARISON.md`
- `VISUAL_ZONE_COMPARISON.md`

### `old_summaries/`
Contains implementation summaries and change logs from System 1.0 development:
- Hardware refactoring summaries
- Implementation completion reports
- Performance optimization notes
- Security and logging enhancement summaries

**Files:**
- `DASH_ENHANCEMENT_SUMMARY.md`
- `HARDWARE_REFACTOR_SUMMARY.md`
- `HARDWARE_REFACTOR_V2.md`
- `IMPLEMENTATION_COMPLETE_V2.md`
- `IMPLEMENTATION_SUMMARY.md`
- `IMPLEMENTATION_SUMMARY_LOGGING.md`
- `IMPLEMENTATION_SUMMARY_USER_MGMT.md`
- `LOGGING_ENHANCEMENTS.md`
- `OPTIMIZATION_SUMMARY.md`
- `PERFORMANCE_IMPROVEMENTS.md`
- `RESTRUCTURE_COMPLETE.md`
- `SCHEDULER_UPDATE.md`
- `SECURITY_SUMMARY.md`
- `SENSOR_REFACTOR_SUMMARY.md`

### `old_config/`
Contains obsolete configuration files from System 1.0:
- Old systemd service files (Display 2 service)
- Deprecated connection tables replaced by `hardware_map.csv`

**Files:**
- `systemd_display-manager.service` (Display 2 service - no longer used)
- `Förbindningstabell_med_Modbus.csv` (superseded by `hardware_map.csv` in root)

## 📖 Historical Context
These files document the evolution of the fotbollsplan-bevattning project and may be useful for:
- Understanding design decisions made during System 1.0
- Reference when troubleshooting legacy issues
- Learning about features that were tried and later removed or modified
- Project history and development timeline

## ⚠️ Important Notes
- **Do NOT use these files as current documentation** - refer to files in the repository root instead
- Active documentation includes:
  - `README.md` - Main project documentation
  - `INSTALLATION.md` - Current installation guide
  - `TEST_SCENARIOS.md` - Testing documentation
  - `USER_MANAGEMENT.md` - User management guide
  - `PIPE_NETWORK_DOCUMENTATION.md` - Current pipe network documentation
  - `MARKFUKTGIVARE_REVIEW.md` - Soil moisture sensor documentation
- Critical System 2.0 files remain in root:
  - `hardware_map.csv` - THE TRUTH for IO mapping
  - `bevattning_controller.py` - Main controller logic
  - `display_manager.py` - Display 1 and ArcadeButtonManager
  - `setup.sh` - Installation script

## 🔍 Git History
All files in this archive were moved (not deleted) to preserve their git history. Use `git log --follow <path/to/file>` to view the complete history of any archived file.

---
*Last Updated: 2026-01-01*
*System Version: 2.0*
