(*
  Fotbollsplan_Master_Version12.st
  - Ventiler öppnas före pumpstart.
  - Pump stängs av först vid stop/zonbyte, därefter ventiler efter CloseDelay, för att minimera vattenslag.
  - Heartbeat (1s) bit+counter: MW70 (bit0 toggle), MW71 counter.
  - Event/Alarm mask: MW72 (bit0 E-stop, bit1 fukt/regen-block, bit2 sekvens aktiv, bit3 anti-kollision, bit4 AutoOverride).
  - Block reason: MW73 (0=OK, 1=Regen>thr, 2=Moisture>thr, 3=Anti-kollision/Pump upptagen, 4=E-stop).
  - ManualRunTime REMOVED: Manual mode nu använder samma tider som auto mode (Set_Tid_Center/Set_Tid_Horn).
  - LED outputs REMOVED: Aktiv zon och återstående tid visas på display istället.
  - Display Button 1/2: Öka/minska zon, håll 3s för att bekräfta.
  - Manual mode: Kör endast den valda zonen (inte full sekvens som auto mode).
  - 21:00 auto mode transition: Hanteras av Python display_manager, inte PLC.
  - Anti-kollision: Om sekvens redan kör/pump aktiv blockeras ny start (sätter bit3/code 3).
  - Next-knapp: DEPRECATED, använd display-knappar istället.
*)

PROGRAM Fotbollsplan_Master
  VAR_EXTERNAL
    (* UTGÅNGAR - ventiler och pump *)
    Ventil_1 : BOOL; Ventil_2 : BOOL; Ventil_3 : BOOL;
    Ventil_4 : BOOL; Ventil_5 : BOOL; Ventil_6 : BOOL; Ventil_7 : BOOL;
    Signal_Pump : BOOL; (* Går till Siemens LOGO/VFD-ingång *)

    (* FYSISKA KNAPPAR / SWITCHAR *)
    Stop_Puls        : BOOL; (* %IX0.0 *)
    Start_Puls       : BOOL; (* %IX0.1 *)
    Mode_AutoManual  : BOOL; (* %IX0.2 *)
    Manual_NextZone  : BOOL; (* %IX0.3 - deprecated, use display buttons *)
    Display_Button_1 : BOOL; (* %IX0.4 - Display increase zone *)
    Test_Button      : BOOL; (* %IX0.5 *)
    Blow_Button      : BOOL; (* %IX0.6 *)
    EStop_NC         : BOOL; (* %IX0.7 *)
    Display_Button_2 : BOOL; (* %IX1.0 - Display decrease zone *)

    (* MODBUS / HOLDING REGISTER *)
    Remote_Command : INT; (* %MW10 *)
    Set_Tid_Center : INT; (* %MW20 *)
    Set_Tid_Horn   : INT; (* %MW21 *)

    Markfukt       : INT; (* %MW30 *)
    Regen_24h_mm   : INT; (* %MW31 *)
    Temp_C         : INT; (* %MW32 *)
    AutoOverride   : INT; (* %MW33 *)

    RegenThreshold_mm : INT; (* %MW34 *)
    MoistureThreshold : INT; (* %MW35 *)

    OpenDelaySec  : INT; (* %MW40 *)
    PauseDelaySec : INT; (* %MW41 *)
    CloseDelaySec : INT; (* %MW42 *)

    Status_CurrentZone : INT; (* %MW50 *)
    Status_PumpOn      : INT; (* %MW51 *)
    Status_Steg        : INT; (* %MW52 *)

    SelectedZoneReg    : INT; (* %MW53 - vald zon *)
    ModeRegister       : INT; (* %MW60 - 1=Auto, 0=Manual override *)
    ManualStartReg     : INT; (* %MW61 - skriv 1 för manual start (PLC nollar) *)
    SetSelectedZoneReg : INT; (* %MW63 - skriv 1..7 för direktval (PLC nollar) *)

    ManualRunTimeReg   : INT; (* %MW64 - minuter, 1..240 *)

    HeartbeatReg       : INT; (* %MW70 - bit0 togglar 1s *)
    HeartbeatCountReg  : INT; (* %MW71 - räknare ++ per 1s, wrap 0..65535 *)

    EventMaskReg       : INT; (* %MW72 - bitmask enligt ovan *)
    BlockReasonReg     : INT; (* %MW73 - block reason code *)
  END_VAR

  VAR
    System_Mode : INT := 1;
    Steg : INT := 0;
    Nuvarande_Zon : INT := 0;

    SelectedZone : INT := 1;
    ManualRun : BOOL := FALSE;
    ManualRunZone : INT := 0;
    (* Manual mode now uses same times as auto mode, no separate ManualRunTime *)

    (* Display button hold detection for zone confirmation *)
    DisplayBtn1_HoldTimer : TON;
    DisplayBtn2_HoldTimer : TON;
    DisplayBtn1_Prev : BOOL := FALSE;
    DisplayBtn2_Prev : BOOL := FALSE;
    ZoneConfirmed : BOOL := FALSE;
    
    (* 21:00 auto mode transition *)
    LastAutoTransitionDay : INT := 0;
    
    Tmr_StopDeb : TON;
    Prev_Stop_Puls : BOOL := FALSE;
    Stop_Request : BOOL := FALSE;

    Tmr_StartDeb : TON;
    Prev_Start_Puls : BOOL := FALSE;
    Start_Request : BOOL := FALSE;

    Tmr_NextDeb : TON;
    Prev_Next_Puls : BOOL := FALSE;
    Next_Request : BOOL := FALSE;

    Tmr_TestDeb : TON;
    Prev_Test_Puls : BOOL := FALSE;
    Test_Request : BOOL := FALSE;

    Tmr_BlowDeb : TON;
    Prev_Blow_Puls : BOOL := FALSE;
    Blow_Request : BOOL := FALSE;

    Tmr_OpenDelay : TON;
    Tmr_Run       : TON;
    Tmr_Pause     : TON;
    Tmr_StopClose : TON;
    Tmr_CloseDelay: TON; (* används vid stop/zonbyte *)

    Tid_Att_Kora : TIME := T#0s;
    OpenDelayTIME  : TIME := T#5s;
    PauseDelayTIME : TIME := T#10s;
    CloseDelayTIME : TIME := T#10s;

    mins : INT := 0;
    PrevRemoteCmd : INT := 0;
    ModeIsAuto : BOOL := TRUE;

    HeartbeatToggle : BOOL := FALSE;
    Tmr_Heartbeat : TON;
    HeartbeatCounter : INT := 0;

    EventMask : INT := 0;
    BlockReason : INT := 0;

    AntiCollisionBlock : BOOL := FALSE;
  END_VAR

  (* Init defaults *)
  IF RegenThreshold_mm = 0 THEN RegenThreshold_mm := 5; END_IF;
  IF MoistureThreshold = 0 THEN MoistureThreshold := 80; END_IF;
  IF OpenDelaySec = 0 THEN OpenDelaySec := 5; END_IF;
  IF PauseDelaySec = 0 THEN PauseDelaySec := 10; END_IF;
  IF CloseDelaySec = 0 THEN CloseDelaySec := 10; END_IF;
  (* ManualRunTimeReg is deprecated - manual mode uses auto times *)

  OpenDelayTIME := T#1s * OpenDelaySec;
  PauseDelayTIME := T#1s * PauseDelaySec;
  CloseDelayTIME := T#1s * CloseDelaySec;

  (* Status/reg uppdateringar *)
  Status_CurrentZone := Nuvarande_Zon;
  IF Signal_Pump THEN Status_PumpOn := 1; ELSE Status_PumpOn := 0; END_IF;
  Status_Steg := Steg;

  (* Heartbeat 1s *)
  Tmr_Heartbeat(IN := TRUE, PT := T#1s);
  IF Tmr_Heartbeat.Q THEN
    Tmr_Heartbeat(IN := FALSE, PT := T#1s);
    HeartbeatToggle := NOT HeartbeatToggle;
    HeartbeatCounter := HeartbeatCounter + 1;
    IF HeartbeatCounter > 65535 THEN HeartbeatCounter := 0; END_IF;
  END_IF;
  HeartbeatReg := 0;
  IF HeartbeatToggle THEN HeartbeatReg := HeartbeatReg OR 1; END_IF;
  HeartbeatCountReg := HeartbeatCounter;

  (* E-STOP (NC) *)
  IF NOT EStop_NC THEN
    Signal_Pump := FALSE;
    Tmr_StopClose(IN := TRUE, PT := CloseDelayTIME);
    IF Tmr_StopClose.Q THEN
      Ventil_1 := FALSE; Ventil_2 := FALSE; Ventil_3 := FALSE;
      Ventil_4 := FALSE; Ventil_5 := FALSE; Ventil_6 := FALSE; Ventil_7 := FALSE;
      Tmr_StopClose(IN := FALSE, PT := CloseDelayTIME);
    END_IF;
    Remote_Command := 0;
    Steg := 0;
    Nuvarande_Zon := 0;
    EventMask := EventMask OR 1; (* bit0 E-stop *)
    BlockReason := 4;
    RETURN;
  END_IF;

  (* Mode override *)
  IF ModeRegister <> 0 THEN
    ModeIsAuto := (ModeRegister = 1);
  ELSE
    ModeIsAuto := Mode_AutoManual;
  END_IF;

  (* Hantera skrivningar från Modbus *)
  IF (SetSelectedZoneReg >= 1) AND (SetSelectedZoneReg <= 7) THEN
    SelectedZone := SetSelectedZoneReg;
    SetSelectedZoneReg := 0;
  END_IF;

  IF ManualStartReg = 1 THEN
    Start_Request := TRUE;
    ManualStartReg := 0;
  END_IF;

  (* Display Button 1: Increase zone (hold 3s to confirm) *)
  IF Display_Button_1 AND NOT DisplayBtn1_Prev THEN
    (* Button just pressed - increment zone *)
    SelectedZone := SelectedZone + 1;
    IF SelectedZone > 7 THEN SelectedZone := 1; END_IF;
    DisplayBtn1_HoldTimer(IN := FALSE, PT := T#3s);
    ZoneConfirmed := FALSE;
  END_IF;
  
  IF Display_Button_1 THEN
    DisplayBtn1_HoldTimer(IN := TRUE, PT := T#3s);
    IF DisplayBtn1_HoldTimer.Q AND NOT ZoneConfirmed THEN
      (* Button held for 3 seconds - confirm zone selection *)
      ZoneConfirmed := TRUE;
      (* Confirmation indicated by selected zone being set *)
    END_IF;
  ELSE
    DisplayBtn1_HoldTimer(IN := FALSE, PT := T#3s);
  END_IF;
  DisplayBtn1_Prev := Display_Button_1;

  (* Display Button 2: Decrease zone (hold 3s to confirm) *)
  IF Display_Button_2 AND NOT DisplayBtn2_Prev THEN
    (* Button just pressed - decrement zone *)
    SelectedZone := SelectedZone - 1;
    IF SelectedZone < 1 THEN SelectedZone := 7; END_IF;
    DisplayBtn2_HoldTimer(IN := FALSE, PT := T#3s);
    ZoneConfirmed := FALSE;
  END_IF;
  
  IF Display_Button_2 THEN
    DisplayBtn2_HoldTimer(IN := TRUE, PT := T#3s);
    IF DisplayBtn2_HoldTimer.Q AND NOT ZoneConfirmed THEN
      (* Button held for 3 seconds - confirm zone selection *)
      ZoneConfirmed := TRUE;
      (* Confirmation indicated by selected zone being set *)
    END_IF;
  ELSE
    DisplayBtn2_HoldTimer(IN := FALSE, PT := T#3s);
  END_IF;
  DisplayBtn2_Prev := Display_Button_2;

  (* Debounce Next: roterar 1..7 *)
  Tmr_NextDeb(IN := (Manual_NextZone <> Prev_Next_Puls), PT := T#50ms);
  IF Tmr_NextDeb.Q THEN
    Prev_Next_Puls := Manual_NextZone;
    Tmr_NextDeb(IN := FALSE, PT := T#50ms);
    IF Prev_Next_Puls THEN
      SelectedZone := SelectedZone + 1;
      IF SelectedZone > 7 THEN SelectedZone := 1; END_IF;
    END_IF;
  END_IF;

  (* Debounce start/stop/test/blow *)
  Tmr_StartDeb(IN := (Start_Puls <> Prev_Start_Puls), PT := T#50ms);
  IF Tmr_StartDeb.Q THEN
    Prev_Start_Puls := Start_Puls;
    Tmr_StartDeb(IN := FALSE, PT := T#50ms);
    IF Prev_Start_Puls THEN Start_Request := TRUE; END_IF;
  END_IF;

  Tmr_StopDeb(IN := (Stop_Puls <> Prev_Stop_Puls), PT := T#50ms);
  IF Tmr_StopDeb.Q THEN
    Prev_Stop_Puls := Stop_Puls;
    Tmr_StopDeb(IN := FALSE, PT := T#50ms);
    IF Prev_Stop_Puls THEN Stop_Request := TRUE; END_IF;
  END_IF;

  Tmr_TestDeb(IN := (Test_Button <> Prev_Test_Puls), PT := T#50ms);
  IF Tmr_TestDeb.Q THEN
    Prev_Test_Puls := Test_Button;
    Tmr_TestDeb(IN := FALSE, PT := T#50ms);
    IF Prev_Test_Puls THEN Test_Request := TRUE; END_IF;
  END_IF;

  Tmr_BlowDeb(IN := (Blow_Button <> Prev_Blow_Puls), PT := T#50ms);
  IF Tmr_BlowDeb.Q THEN
    Prev_Blow_Puls := Blow_Button;
    Tmr_BlowDeb(IN := FALSE, PT := T#50ms);
    IF Prev_Blow_Puls THEN Blow_Request := TRUE; END_IF;
  END_IF;

  SelectedZoneReg := SelectedZone;

  (* Anti-kollision: blockera start om sekvens aktiv *)
  AntiCollisionBlock := (Steg <> 0);
  IF AntiCollisionBlock THEN
    EventMask := EventMask OR 8; (* bit3 *)
    BlockReason := 3;
  END_IF;

  (* STOPP: kontrollerad nedstängning, pump av först *)
  IF Stop_Request THEN
    Signal_Pump := FALSE; (* pump av först *)
    Tmr_CloseDelay(IN := TRUE, PT := CloseDelayTIME);
    IF Tmr_CloseDelay.Q THEN
      Ventil_1 := FALSE; Ventil_2 := FALSE; Ventil_3 := FALSE;
      Ventil_4 := FALSE; Ventil_5 := FALSE; Ventil_6 := FALSE; Ventil_7 := FALSE;
      Tmr_CloseDelay(IN := FALSE, PT := CloseDelayTIME);
      Stop_Request := FALSE;
      Steg := 0;
      System_Mode := 1;
      Remote_Command := 0;
      Nuvarande_Zon := 0;
    END_IF;
    RETURN;
  END_IF;

  (* Manual mode *)
  IF NOT ModeIsAuto THEN
    IF Start_Request AND NOT AntiCollisionBlock THEN
      Start_Request := FALSE;
      ManualRun := TRUE;
      ManualRunZone := SelectedZone;
      (* Manual mode now runs full sequence from selected zone to zone 7 *)
      (* Uses same times as auto mode (Set_Tid_Center/Set_Tid_Horn) *)
      Nuvarande_Zon := ManualRunZone;
      Steg := 10;
      System_Mode := 2;
      BlockReason := 0;
    END_IF;
  END_IF;

  (* Auto mode start via Remote_Command rising edge *)
  IF ModeIsAuto THEN
    IF (Remote_Command = 50) AND (PrevRemoteCmd <> 50) THEN
      IF AutoOverride = 1 THEN
        Nuvarande_Zon := 1;
        Steg := 10;
        System_Mode := 5;
        BlockReason := 0;
      ELSE
        IF Regen_24h_mm > RegenThreshold_mm THEN
          Remote_Command := 0;
          BlockReason := 1;
        ELSIF Markfukt >= MoistureThreshold THEN
          Remote_Command := 0;
          BlockReason := 2;
        ELSE
          Nuvarande_Zon := 1;
          Steg := 10;
          System_Mode := 5;
          BlockReason := 0;
        END_IF;
      END_IF;
    END_IF;
    PrevRemoteCmd := Remote_Command;
  END_IF;

  (* SEKVENS *)
  CASE Steg OF
    0:
      Signal_Pump := FALSE;
      Ventil_1 := FALSE; Ventil_2 := FALSE; Ventil_3 := FALSE;
      Ventil_4 := FALSE; Ventil_5 := FALSE; Ventil_6 := FALSE; Ventil_7 := FALSE;
      Tmr_OpenDelay(IN := FALSE, PT := OpenDelayTIME);
      Tmr_Run(IN := FALSE, PT := T#1s);
      Tmr_Pause(IN := FALSE, PT := PauseDelayTIME);
      Tmr_CloseDelay(IN := FALSE, PT := CloseDelayTIME);

    10: (* Förbered zon: ventil först, pump efter OpenDelay *)
      (* Both auto and manual mode use Set_Tid_Center/Set_Tid_Horn *)
      IF Nuvarande_Zon <= 3 THEN
        mins := Set_Tid_Center;
        IF mins <= 0 THEN
          Tid_Att_Kora := T#30m;
        ELSE
          IF mins > 240 THEN mins := 240; END_IF;
          Tid_Att_Kora := T#1m * mins;
        END_IF;
      ELSE
        mins := Set_Tid_Horn;
        IF mins <= 0 THEN
          Tid_Att_Kora := T#15m;
        ELSE
          IF mins > 240 THEN mins := 240; END_IF;
          Tid_Att_Kora := T#1m * mins;
        END_IF;
      END_IF;

      Ventil_1 := FALSE; Ventil_2 := FALSE; Ventil_3 := FALSE;
      Ventil_4 := FALSE; Ventil_5 := FALSE; Ventil_6 := FALSE; Ventil_7 := FALSE;
      CASE Nuvarande_Zon OF
        1: Ventil_1 := TRUE;
        2: Ventil_2 := TRUE;
        3: Ventil_3 := TRUE;
        4: Ventil_4 := TRUE;
        5: Ventil_5 := TRUE;
        6: Ventil_6 := TRUE;
        7: Ventil_7 := TRUE;
      END_CASE;

      Tmr_OpenDelay(IN := TRUE, PT := OpenDelayTIME);
      IF Tmr_OpenDelay.Q THEN
        Tmr_OpenDelay(IN := FALSE, PT := OpenDelayTIME);
        Signal_Pump := TRUE; (* pump på efter ventiler har öppnat *)
        Tmr_Run(IN := TRUE, PT := Tid_Att_Kora);
        Steg := 20;
      END_IF;

    20: (* Kör med pump på *)
      IF NOT (Ventil_1 OR Ventil_2 OR Ventil_3 OR Ventil_4 OR Ventil_5 OR Ventil_6 OR Ventil_7) THEN
        Signal_Pump := FALSE;
        Steg := 0;
      ELSE
        IF Tmr_Run.Q THEN
          Tmr_Run(IN := FALSE, PT := Tid_Att_Kora);
          Signal_Pump := FALSE; (* pump av först *)
          Tmr_CloseDelay(IN := TRUE, PT := CloseDelayTIME);
          Steg := 22;
          (* Clear ManualRun flag - sequence will continue to next zones *)
          IF ManualRun THEN ManualRun := FALSE; END_IF;
        END_IF;
      END_IF;

    22: (* Stäng ventiler efter CloseDelay, förbered paus inför nästa zon *)
      IF Tmr_CloseDelay.Q THEN
        Tmr_CloseDelay(IN := FALSE, PT := CloseDelayTIME);
        Ventil_1 := FALSE; Ventil_2 := FALSE; Ventil_3 := FALSE;
        Ventil_4 := FALSE; Ventil_5 := FALSE; Ventil_6 := FALSE; Ventil_7 := FALSE;
        Tmr_Pause(IN := TRUE, PT := PauseDelayTIME);
        Steg := 30;
      END_IF;

    30: (* Paus mellan zoner, pump är av *)
      IF Tmr_Pause.Q THEN
        Tmr_Pause(IN := FALSE, PT := PauseDelayTIME);
        (* Manual mode: stoppa efter en zon. Auto mode: fortsätt till nästa zon *)
        IF (System_Mode = 2) OR (Nuvarande_Zon >= 7) THEN
          (* Manual mode (System_Mode=2) eller sista zonen i auto mode *)
          System_Mode := 1;
          Steg := 0;
          Remote_Command := 0;
          Nuvarande_Zon := 0;
        ELSE
          (* Auto mode: fortsätt till nästa zon *)
          Nuvarande_Zon := Nuvarande_Zon + 1;
          Steg := 10;
        END_IF;
      END_IF;

    90: (* Test-körning kort *)
      Ventil_1 := FALSE; Ventil_2 := FALSE; Ventil_3 := FALSE;
      Ventil_4 := FALSE; Ventil_5 := FALSE; Ventil_6 := FALSE; Ventil_7 := FALSE;
      CASE Nuvarande_Zon OF
        1: Ventil_1 := TRUE;
        2: Ventil_2 := TRUE;
        3: Ventil_3 := TRUE;
        4: Ventil_4 := TRUE;
        5: Ventil_5 := TRUE;
        6: Ventil_6 := TRUE;
        7: Ventil_7 := TRUE;
      END_CASE;
      Tmr_OpenDelay(IN := TRUE, PT := OpenDelayTIME);
      IF Tmr_OpenDelay.Q THEN
        Tmr_OpenDelay(IN := FALSE, PT := OpenDelayTIME);
        Signal_Pump := TRUE;
        Tmr_Run(IN := TRUE, PT := T#10s);
        IF Tmr_Run.Q THEN
          Tmr_Run(IN := FALSE, PT := T#10s);
          Signal_Pump := FALSE;
          Tmr_CloseDelay(IN := TRUE, PT := CloseDelayTIME);
          IF Tmr_CloseDelay.Q THEN
            Tmr_CloseDelay(IN := FALSE, PT := CloseDelayTIME);
            Ventil_1 := FALSE; Ventil_2 := FALSE; Ventil_3 := FALSE;
            Ventil_4 := FALSE; Ventil_5 := FALSE; Ventil_6 := FALSE; Ventil_7 := FALSE;
            Steg := 0;
          END_IF;
        END_IF;
      END_IF;

    95: (* Blow-körning längre *)
      Ventil_1 := FALSE; Ventil_2 := FALSE; Ventil_3 := FALSE;
      Ventil_4 := FALSE; Ventil_5 := FALSE; Ventil_6 := FALSE; Ventil_7 := FALSE;
      CASE Nuvarande_Zon OF
        1: Ventil_1 := TRUE;
        2: Ventil_2 := TRUE;
        3: Ventil_3 := TRUE;
        4: Ventil_4 := TRUE;
        5: Ventil_5 := TRUE;
        6: Ventil_6 := TRUE;
        7: Ventil_7 := TRUE;
      END_CASE;
      Tmr_OpenDelay(IN := TRUE, PT := OpenDelayTIME);
      IF Tmr_OpenDelay.Q THEN
        Tmr_OpenDelay(IN := FALSE, PT := OpenDelayTIME);
        Signal_Pump := TRUE;
        Tmr_Run(IN := TRUE, PT := T#30s);
        IF Tmr_Run.Q THEN
          Tmr_Run(IN := FALSE, PT := T#30s);
          Signal_Pump := FALSE;
          Tmr_CloseDelay(IN := TRUE, PT := CloseDelayTIME);
          IF Tmr_CloseDelay.Q THEN
            Tmr_CloseDelay(IN := FALSE, PT := CloseDelayTIME);
            Ventil_1 := FALSE; Ventil_2 := FALSE; Ventil_3 := FALSE;
            Ventil_4 := FALSE; Ventil_5 := FALSE; Ventil_6 := FALSE; Ventil_7 := FALSE;
            Steg := 0;
          END_IF;
        END_IF;
      END_IF;
  END_CASE;

  (* Event/Alarm mask *)
  EventMask := 0;
  BlockReasonReg := BlockReason;
  (* bit0 E-stop hanteras ovan *)
  (* bit1 fukt/regen block *)
  IF (Regen_24h_mm > RegenThreshold_mm) OR (Markfukt >= MoistureThreshold) THEN
    EventMask := EventMask OR 2;
  END_IF;
  (* bit2 sekvens aktiv *)
  IF Steg <> 0 THEN EventMask := EventMask OR 4; END_IF;
  (* bit3 anti-kollision *)
  IF AntiCollisionBlock THEN EventMask := EventMask OR 8; END_IF;
  (* bit4 AutoOverride *)
  IF AutoOverride = 1 THEN EventMask := EventMask OR 16; END_IF;
  EventMaskReg := EventMask;

END_PROGRAM

CONFIGURATION Config0
  VAR_GLOBAL
    Ventil_1 AT %QX0.0 : BOOL;
    Ventil_2 AT %QX0.1 : BOOL;
    Ventil_3 AT %QX0.2 : BOOL;
    Ventil_4 AT %QX0.3 : BOOL;
    Ventil_5 AT %QX0.4 : BOOL;
    Ventil_6 AT %QX0.5 : BOOL;
    Ventil_7 AT %QX0.6 : BOOL;
    Signal_Pump AT %QX0.7 : BOOL;

    Stop_Puls AT %IX0.0 : BOOL;
    Start_Puls AT %IX0.1 : BOOL;
    Mode_AutoManual AT %IX0.2 : BOOL;
    Manual_NextZone AT %IX0.3 : BOOL;
    Display_Button_1 AT %IX0.4 : BOOL;
    Test_Button AT %IX0.5 : BOOL;
    Blow_Button AT %IX0.6 : BOOL;
    EStop_NC AT %IX0.7 : BOOL;
    Display_Button_2 AT %IX1.0 : BOOL;

    Remote_Command AT %MW10 : INT;
    Set_Tid_Center AT %MW20 : INT;
    Set_Tid_Horn   AT %MW21 : INT;

    Markfukt AT %MW30 : INT;
    Regen_24h_mm AT %MW31 : INT;
    Temp_C AT %MW32 : INT;
    AutoOverride AT %MW33 : INT;

    RegenThreshold_mm AT %MW34 : INT;
    MoistureThreshold AT %MW35 : INT;

    OpenDelaySec AT %MW40 : INT;
    PauseDelaySec AT %MW41 : INT;
    CloseDelaySec AT %MW42 : INT;

    Status_CurrentZone AT %MW50 : INT;
    Status_PumpOn AT %MW51 : INT;
    Status_Steg AT %MW52 : INT;

    SelectedZoneReg AT %MW53 : INT;

    ModeRegister AT %MW60 : INT;
    ManualStartReg AT %MW61 : INT;
    SetSelectedZoneReg AT %MW63 : INT;

    ManualRunTimeReg AT %MW64 : INT;

    HeartbeatReg AT %MW70 : INT;
    HeartbeatCountReg AT %MW71 : INT;
    EventMaskReg AT %MW72 : INT;
    BlockReasonReg AT %MW73 : INT;
  END_VAR

  RESOURCE Res0 ON PLC
    TASK task0(INTERVAL := T#100ms, PRIORITY := 0);
    PROGRAM instance0 WITH task0 : Fotbollsplan_Master;
  END_RESOURCE
END_CONFIGURATION
