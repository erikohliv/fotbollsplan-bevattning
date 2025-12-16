#!/usr/bin/env python3
"""
Bevattning Scheduler
Runs the bevattning controller at scheduled times (01:00 daily)
"""
import argparse
import logging
import time
from datetime import datetime, timedelta
import sys
import os

# Import the controller
import bevattning_controller

logger = logging.getLogger("bevattning_scheduler")
logger.setLevel(logging.DEBUG)
_formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
_console = logging.StreamHandler()
_console.setFormatter(_formatter)
_console.setLevel(logging.INFO)
logger.addHandler(_console)

# Default schedule time (01:00)
DEFAULT_SCHEDULE_HOUR = 1
DEFAULT_SCHEDULE_MINUTE = 0


def wait_until_next_schedule(hour=DEFAULT_SCHEDULE_HOUR, minute=DEFAULT_SCHEDULE_MINUTE):
    """
    Calculate seconds to wait until next scheduled time.
    Returns the number of seconds to wait.
    """
    now = datetime.now()
    # Create target time for today
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # If target time has passed today, schedule for tomorrow
    if now >= target:
        target = target + timedelta(days=1)
    
    wait_seconds = (target - now).total_seconds()
    logger.info("Next scheduled run at %s (in %.1f hours)", 
                target.strftime("%Y-%m-%d %H:%M:%S"), 
                wait_seconds / 3600)
    return wait_seconds


def check_block_conditions(args):
    """
    Check if auto-watering should be blocked.
    Returns (should_block, reason) tuple.
    """
    # Read block_reason from Modbus if available
    if bevattning_controller.ModbusTcpClient is not None:
        try:
            client = bevattning_controller.open_modbus_client(args.host, args.port)
            if client.connect():
                # Read MW73 (BlockReasonReg)
                rr = client.read_holding_registers(
                    bevattning_controller.MW_BLOCK_REASON,
                    1, 
                    unit=args.unit
                )
                client.close()
                
                if rr and hasattr(rr, 'registers') and rr.registers:
                    block_reason = rr.registers[0]
                    if block_reason != 0:
                        reasons = {
                            1: "Rain > threshold",
                            2: "Moisture > threshold", 
                            3: "Anti-collision/pump busy",
                            4: "E-stop active"
                        }
                        reason_text = reasons.get(block_reason, f"Unknown ({block_reason})")
                        logger.warning("Auto-watering blocked: %s (BlockReason=%d)", 
                                     reason_text, block_reason)
                        return True, reason_text
        except Exception as e:
            logger.warning("Could not check block_reason from Modbus: %s", e)
    
    return False, None


def run_scheduled_watering(args):
    """
    Execute the scheduled watering task.
    Checks block conditions before running.
    """
    logger.info("=" * 60)
    logger.info("Starting scheduled auto-watering at %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 60)
    
    # Check if watering should be blocked
    should_block, block_reason = check_block_conditions(args)
    
    if should_block:
        logger.info("Skipping auto-watering due to block condition: %s", block_reason)
        return
    
    # Run the controller with auto-start enabled
    try:
        result = bevattning_controller.main_once(args)
        logger.info("Scheduled watering completed successfully")
        logger.info("Result: %s", result)
    except Exception as e:
        logger.exception("Error during scheduled watering: %s", e)


def main():
    parser = bevattning_controller.build_argparser()
    parser.description = "Bevattning scheduler - runs controller at 01:00 daily"
    parser.add_argument("--schedule-hour", type=int, default=DEFAULT_SCHEDULE_HOUR,
                       help="Hour to run daily (0-23, default: 1 for 01:00)")
    parser.add_argument("--schedule-minute", type=int, default=DEFAULT_SCHEDULE_MINUTE,
                       help="Minute to run daily (0-59, default: 0)")
    parser.add_argument("--run-now", action="store_true",
                       help="Run immediately instead of waiting for scheduled time")
    
    args = parser.parse_args()
    
    # Ensure auto-start is enabled for scheduled runs
    if not args.run_now:
        args.auto_start = True
    
    if args.log_file:
        fh = logging.FileHandler(args.log_file)
        fh.setFormatter(_formatter)
        fh.setLevel(logging.DEBUG)
        logger.addHandler(fh)
    
    try:
        if args.run_now:
            logger.info("Running immediately (--run-now)")
            run_scheduled_watering(args)
        elif args.once:
            # Wait until next scheduled time and run once
            wait_seconds = wait_until_next_schedule(args.schedule_hour, args.schedule_minute)
            time.sleep(wait_seconds)
            run_scheduled_watering(args)
        else:
            # Continuous scheduler mode - run daily at scheduled time
            logger.info("Starting scheduler in continuous mode")
            logger.info("Daily schedule: %02d:%02d", args.schedule_hour, args.schedule_minute)
            
            while True:
                wait_seconds = wait_until_next_schedule(args.schedule_hour, args.schedule_minute)
                time.sleep(wait_seconds)
                run_scheduled_watering(args)
                
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.exception("Unexpected error in scheduler: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
