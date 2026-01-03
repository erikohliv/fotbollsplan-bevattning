#!/usr/bin/env python3
"""
Display Menu Enhancements - Tillägg till Display1Manager
Innehåller nya menyer och funktioner för Display 1 + Arcade Buttons

Lägg till dessa metoder i Display1Manager-klassen i display_manager.py
"""


def render_progressbar(self, percent: int, width: int = 10) -> str:
    """
    Render ASCII progressbar
    
    Args:
        percent: Progress 0-100
        width: Bar width in characters
        
    Returns:
        str: Progressbar som "[████------]"
    """
    filled = int((percent / 100.0) * width)
    bar = '█' * filled + '-' * (width - filled)
    return f"[{bar}]"


def _render_status_view_enhanced(self, status: dict):
    """
    Enhanced status view med progressbar och lock-ikon
    
    Format (20x4):
    Auto Z:2/2 PUMP:ON🔓
    Stage:3 [██████----]
    T:18C M:45% R:2mm
    Status: OK
    """
    self.lcd.clear()
    
    # Line 1: Mode, Zone, Pump, Lock status
    mode = status.get('mode', 'Manual')[:4]  # Max 4 chars
    zone = status.get('zone', 0)
    sel_zone = status.get('selected_zone', 0)
    pump = "ON " if status.get('pump_on') else "OFF"
    lock_icon = "🔓" if not self.buttons.locked else "🔒"
    
    line1 = f"{mode} Z:{zone}/{sel_zone} PUMP:{pump}{lock_icon}"
    self.lcd.write_line(0, line1[:20])
    
    # Line 2: Stage + Progressbar
    steg = status.get('steg', 0)
    # Beräkna progress baserat på stage (0-100%)
    # Stage 0=0%, 10=20%, 20=40%, 22=50%, 30=100%
    progress_map = {0: 0, 10: 20, 20: 40, 22: 50, 30: 100}
    progress = progress_map.get(steg, 0)
    progressbar = self.render_progressbar(progress, 10)
    
    line2 = f"Stage:{steg} {progressbar}"
    self.lcd.write_line(1, line2[:20])
    
    # Line 3: Temp, Moisture, Rain
    temp = status.get('temp', 0)
    moisture = status.get('moisture', 0)
    rain = status.get('rain', 0)
    line3 = f"T:{temp}C M:{moisture}% R:{rain}mm"
    self.lcd.write_line(2, line3[:20])
    
    # Line 4: Block status
    block_reason = status.get('block_reason', 0)
    block_text = self._get_block_text(block_reason)
    line4 = f"Status: {block_text}"
    self.lcd.write_line(3, line4[:20])


def _render_error_view(self, status: dict):
    """
    Render fel-vy med scrollande lista om flera fel
    
    Format (20x4):
       ⚠️ LARM ⚠️
     E-STOP AKTIV
   1. Tryck RESET-knapp
   2. Bekräfta i meny
    """
    self.lcd.clear()
    
    # Titel
    self.lcd.write_line(0, "   ⚠️ LARM ⚠️", align='center')
    
    block_reason = status.get('block_reason', 0)
    
    # E-STOP special case
    if block_reason == BlockReason.E_STOP:
        self.lcd.write_line(1, "  E-STOP AKTIV")
        self.lcd.write_line(2, "1. Tryck RESET-knapp")
        self.lcd.write_line(3, "2. Bekräfta i meny")
    else:
        # Andra fel
        error_text = self._get_block_text(block_reason)
        self.lcd.write_line(1, error_text[:20], align='center')
        self.lcd.write_line(2, "")
        self.lcd.write_line(3, "Tryck OK för meny")


def _render_unlock_view(self):
    """
    Visa unlock-prompt
    
    Format (20x4):
       🔒 LÅST 🔒
    
    Tryck sekvens:
    NER→UPP→UPP→OK
    """
    self.lcd.clear()
    self.lcd.write_line(0, "   🔒 LÅST 🔒", align='center')
    self.lcd.write_line(1, "")
    self.lcd.write_line(2, " Tryck sekvens:")
    self.lcd.write_line(3, " NER→UPP→UPP→OK")


def _render_timeout_warning(self):
    """
    Visa timeout-varning (60s kvar)
    
    Format (20x4):
      AUTO-LOCK OM
        60 SEK
    Tryck knapp för
      att förlänga
    """
    remaining = self.buttons.get_time_until_lock()
    
    self.lcd.clear()
    self.lcd.write_line(0, "  AUTO-LOCK OM", align='center')
    self.lcd.write_line(1, f"    {remaining} SEK", align='center')
    self.lcd.write_line(2, " Tryck knapp för")
    self.lcd.write_line(3, "   att förlänga")


def _render_main_menu(self):
    """
    Huvudmeny
    
    Format (20x4):
      HUVUDMENY
    
    > Starta Zon
      Stoppa Pump
      Användarstyrning
    """
    self.lcd.clear()
    self.lcd.write_line(0, "  HUVUDMENY", align='center')
    self.lcd.write_line(1, "")
    
    menu_items = ["Starta Zon", "Stoppa Pump", "Användarstyrning"]
    # Visa 2 items i taget med scroll
    max_items = 2
    start_idx = max(0, min(self.menu_selection, len(menu_items) - max_items))
    
    for i in range(max_items):
        idx = start_idx + i
        if idx < len(menu_items):
            prefix = "> " if idx == self.menu_selection else "  "
            self.lcd.write_line(2 + i, prefix + menu_items[idx])


def _render_zone_select(self):
    """
    Zonval
    
    Format (20x4):
      VÄLJ ZON
    
    > Zon 1
      Zon 2
    """
    self.lcd.clear()
    self.lcd.write_line(0, "   VÄLJ ZON", align='center')
    self.lcd.write_line(1, "")
    
    # Visa 2 zoner i taget
    start_zone = max(1, self.selected_zone - 1)
    for i in range(2):
        zone_num = start_zone + i
        if zone_num <= 7:
            prefix = "> " if zone_num == self.selected_zone else "  "
            self.lcd.write_line(2 + i, f"{prefix}Zon {zone_num}")


def _render_time_select(self):
    """
    Tidsval (minuter)
    
    Format (20x4):
      VÄLJ TID
    
      10 minuter
    UPP/NER ändra
    """
    self.lcd.clear()
    self.lcd.write_line(0, "   VÄLJ TID", align='center')
    self.lcd.write_line(1, "")
    self.lcd.write_line(2, f"  {self.selected_time} minuter", align='center')
    self.lcd.write_line(3, " UPP/NER ändra")


def _render_schedule_select(self):
    """
    Schemaläggning: Nu eller senare?
    
    Format (20x4):
    STARTA ZON
    
    > Starta Nu
      Schemalägg
    """
    self.lcd.clear()
    self.lcd.write_line(0, "  STARTA ZON", align='center')
    self.lcd.write_line(1, "")
    
    options = ["Starta Nu", "Schemalägg"]
    for i, option in enumerate(options):
        prefix = "> " if i == self.selected_schedule_mode else "  "
        self.lcd.write_line(2 + i, prefix + option)


def _render_schedule_time(self):
    """
    Välj starttid (HH:MM)
    
    Format (20x4):
      VÄLJ STARTTID
    
        06:00
    UPP/NER ändra tim
    """
    self.lcd.clear()
    self.lcd.write_line(0, " VÄLJ STARTTID", align='center')
    self.lcd.write_line(1, "")
    time_str = f"{self.selected_hour:02d}:{self.selected_minute:02d}"
    self.lcd.write_line(2, f"    {time_str}", align='center')
    self.lcd.write_line(3, "UPP/NER ändra tim")


def _render_confirm(self):
    """
    Bekräfta start
    
    Format (20x4):
    STARTA ZON 2?
      10 min
    [OK] Starta
    [←] Avbryt
    """
    self.lcd.clear()
    self.lcd.write_line(0, f" STARTA ZON {self.selected_zone}?", align='center')
    
    if self.selected_schedule_mode == 0:
        # Starta nu
        self.lcd.write_line(1, f"   {self.selected_time} min", align='center')
    else:
        # Schemalagt
        time_str = f"{self.selected_hour:02d}:{self.selected_minute:02d}"
        self.lcd.write_line(1, f"  Kl {time_str}", align='center')
    
    self.lcd.write_line(2, "[OK] Starta")
    self.lcd.write_line(3, "[←] Avbryt")


def _render_running(self, status: dict):
    """
    Körning pågår
    
    Format (20x4):
    ✓ ZON 2 STARTAR
    
     Återgår till
      status...
    """
    self.lcd.clear()
    zone = status.get('zone', self.selected_zone)
    self.lcd.write_line(0, f" ✓ ZON {zone} STARTAR", align='center')
    self.lcd.write_line(1, "")
    self.lcd.write_line(2, "  Återgår till")
    self.lcd.write_line(3, "    status...")


def _render_unlocked_confirmation(self):
    """
    Bekräfta upplåsning
    
    Format (20x4):
    
       ✓ UPPLÅST
    
    Aktiv i 10 min
    """
    self.lcd.clear()
    self.lcd.write_line(0, "")
    self.lcd.write_line(1, "   ✓ UPPLÅST", align='center')
    self.lcd.write_line(2, "")
    self.lcd.write_line(3, " Aktiv i 10 min")


def _render_user_control_menu(self):
    """
    Användarstyrning-menyn
    
    Format (20x4):
    ANVÄNDARSTYRNING
    
    > Aktivera
      Deaktivera
    """
    self.lcd.clear()
    self.lcd.write_line(0, "ANVÄNDARSTYRNING", align='center')
    self.lcd.write_line(1, "")
    
    try:
        from user_control import is_user_control_enabled
        current_status = is_user_control_enabled()
        status_text = "AKTIVT" if current_status else "INAKTIVT"
        self.lcd.write_line(1, f" Status: {status_text}", align='center')
    except:
        pass
    
    options = ["Aktivera", "Deaktivera"]
    for i, option in enumerate(options):
        prefix = "> " if i == self.menu_selection else "  "
        self.lcd.write_line(2 + i, prefix + option)


def handle_quick_start(self) -> bool:
    """
    Snabbstart: Håll OK i 3 sekunder från STATUS-vy
    Startar senast valda zon
    
    Returns:
        bool: True if quick-start triggered
    """
    # Visa countdown
    for i in range(3, 0, -1):
        buttons = self.buttons.read_buttons()
        if not buttons.get('ok'):
            return False  # Användaren släppte knappen
        
        self.lcd.clear()
        self.lcd.write_line(0, "   SNABBSTART", align='center')
        self.lcd.write_line(1, "")
        self.lcd.write_line(2, f" Startar Zon {self.last_started_zone}", align='center')
        self.lcd.write_line(3, f"    i {i} sek...", align='center')
        time.sleep(1)
    
    # Starta zon
    self.start_zone(self.last_started_zone, self.selected_time)
    return True


def start_zone(self, zone: int, duration_minutes: int):
    """
    Starta bevattning av zon via Modbus
    
    Args:
        zone: Zonnummer (1-7)
        duration_minutes: Körtid i minuter
    """
    logger.info(f"🚿 Startar Zon {zone}, {duration_minutes} min")
    
    # Skriv till Modbus
    # MW_MANUAL_ZONE = 70, MW_MANUAL_TIME = 71
    self.modbus.write_register(70, zone)
    self.modbus.write_register(71, duration_minutes)
    
    # Trigger start (sätt bit för manuell start)
    self.modbus.write_register(60, 2)  # MW_MANUAL_START = 2
    
    self.last_started_zone = zone


def stop_pump(self):
    """Stoppa pump via Modbus"""
    logger.info("🛑 Stoppar pump")
    self.modbus.write_register(60, 0)  # MW_MANUAL_START = 0


def _get_block_text(self, block_reason: int) -> str:
    """
    Get human-readable block reason text
    
    Args:
        block_reason: BlockReason enum value
        
    Returns:
        str: Text description
    """
    reason_map = {
        BlockReason.OK: "OK",
        BlockReason.RAIN_THRESHOLD: "REGN",
        BlockReason.MOISTURE_THRESHOLD: "FUKTIG",
        BlockReason.ANTI_COLLISION: "KOLLISION",
        BlockReason.E_STOP: "E-STOP"
    }
    return reason_map.get(block_reason, f"FEL {block_reason}")


# Menu navigation handlers
def handle_menu_navigation(self):
    """
    Main menu navigation loop
    Handles all button presses and state transitions
    """
    while self.running:
        # Check lock status
        if self.buttons.locked:
            self._render_unlock_view()
            if self.buttons.check_unlock_sequence():
                self._render_unlocked_confirmation()
                time.sleep(2)
                self.menu_state = MenuState.AUTO_ROTATE
            continue
        
        # Check timeout warning
        if self.buttons.check_lock_timeout():
            self._render_timeout_warning()
            time.sleep(2)
            continue
        
        # Get status
        status = self.get_system_status()
        
        # Handle different menu states
        if self.menu_state == MenuState.AUTO_ROTATE:
            # Auto-rotating views
            self._render_status_view_enhanced(status)
            
            # Check for button press
            button = self.buttons.get_button_press()
            
            if button == 'ok':
                # Check for quick-start (hold OK for 3s)
                if self.handle_quick_start():
                    self.menu_state = MenuState.RUNNING
                else:
                    # Open main menu
                    self.menu_state = MenuState.MAIN_MENU
                    self.menu_selection = 0
        
        elif self.menu_state == MenuState.MAIN_MENU:
            self._render_main_menu()
            button = self.buttons.get_button_press()
            
            if button == 'up':
                self.menu_selection = max(0, self.menu_selection - 1)
            elif button == 'down':
                self.menu_selection = min(2, self.menu_selection + 1)  # 3 items: 0, 1, 2
            elif button == 'ok':
                if self.menu_selection == 0:  # Starta Zon
                    self.menu_state = MenuState.ZONE_SELECT
                elif self.menu_selection == 1:  # Stoppa Pump
                    self.stop_pump()
                    self.menu_state = MenuState.AUTO_ROTATE
                elif self.menu_selection == 2:  # Användarstyrning
                    self.menu_state = MenuState.USER_CONTROL_MENU
            elif button == 'left':
                self.menu_state = MenuState.AUTO_ROTATE
        
        elif self.menu_state == MenuState.USER_CONTROL_MENU:
            self._render_user_control_menu()
            button = self.buttons.get_button_press()
            
            if button == 'up' or button == 'down':
                # Toggle mellan Aktivera/Deaktivera
                self.menu_selection = 1 - self.menu_selection
            elif button == 'ok':
                # Aktivera eller deaktivera användarstyrning
                try:
                    from user_control import set_user_control, is_user_control_enabled
                    current_status = is_user_control_enabled()
                    
                    if self.menu_selection == 0:  # Aktivera
                        if not current_status:
                            set_user_control(True, "arcade_buttons")
                            self.show_feedback("✅ ANVÄNDARSTYRNING AKTIV", duration=5.0)
                            self.log_event("Användarstyrning aktiverad")
                            logger.info("🎮 Användarstyrning aktiverad via arcadknappar!")
                        else:
                            self.show_feedback("Redan aktivt!", duration=2.0)
                    else:  # Deaktivera
                        if current_status:
                            set_user_control(False, "arcade_buttons")
                            self.show_feedback("🔒 ANVÄNDARSTYRNING AV", duration=5.0)
                            self.log_event("Användarstyrning deaktiverad")
                            logger.info("🔒 Användarstyrning deaktiverad via arcadknappar!")
                        else:
                            self.show_feedback("Redan inaktivt!", duration=2.0)
                    
                    time.sleep(2)
                    self.menu_state = MenuState.MAIN_MENU
                except Exception as e:
                    logger.error(f"Kunde inte ändra användarstyrning: {e}")
                    self.show_feedback("Fel!", duration=2.0)
                    time.sleep(2)
                    self.menu_state = MenuState.MAIN_MENU
            elif button == 'left':
                self.menu_state = MenuState.MAIN_MENU
        
        elif self.menu_state == MenuState.ZONE_SELECT:
            self._render_zone_select()
            button = self.buttons.get_button_press()
            
            if button == 'up':
                self.selected_zone = max(1, self.selected_zone - 1)
            elif button == 'down':
                self.selected_zone = min(7, self.selected_zone + 1)
            elif button == 'ok':
                self.menu_state = MenuState.TIME_SELECT
            elif button == 'left':
                self.menu_state = MenuState.MAIN_MENU
        
        elif self.menu_state == MenuState.TIME_SELECT:
            self._render_time_select()
            button = self.buttons.get_button_press()
            
            if button == 'up':
                self.selected_time = min(60, self.selected_time + 5)
            elif button == 'down':
                self.selected_time = max(5, self.selected_time - 5)
            elif button == 'ok':
                self.menu_state = MenuState.SCHEDULE_SELECT
            elif button == 'left':
                self.menu_state = MenuState.ZONE_SELECT
        
        elif self.menu_state == MenuState.SCHEDULE_SELECT:
            self._render_schedule_select()
            button = self.buttons.get_button_press()
            
            if button == 'up' or button == 'down':
                self.selected_schedule_mode = 1 - self.selected_schedule_mode
            elif button == 'ok':
                if self.selected_schedule_mode == 0:
                    # Starta nu
                    self.menu_state = MenuState.CONFIRM
                else:
                    # Schemalägg
                    self.menu_state = MenuState.SCHEDULE_TIME
            elif button == 'left':
                self.menu_state = MenuState.TIME_SELECT
        
        elif self.menu_state == MenuState.SCHEDULE_TIME:
            self._render_schedule_time()
            button = self.buttons.get_button_press()
            
            if button == 'up':
                self.selected_hour = (self.selected_hour + 1) % 24
            elif button == 'down':
                self.selected_hour = (self.selected_hour - 1) % 24
            elif button == 'ok':
                self.menu_state = MenuState.CONFIRM
            elif button == 'left':
                self.menu_state = MenuState.SCHEDULE_SELECT
        
        elif self.menu_state == MenuState.CONFIRM:
            self._render_confirm()
            button = self.buttons.get_button_press()
            
            if button == 'ok':
                # Starta!
                self.start_zone(self.selected_zone, self.selected_time)
                self.menu_state = MenuState.RUNNING
                self._render_running(status)
                time.sleep(3)
                self.menu_state = MenuState.AUTO_ROTATE
            elif button == 'left':
                self.menu_state = MenuState.SCHEDULE_SELECT
        
        time.sleep(0.1)
