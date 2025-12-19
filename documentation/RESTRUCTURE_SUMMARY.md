# Omstrukturering av Förbindningstabell - Sammanfattning

## Översikt
Filen `Förbindningstabell_med_Modbus.csv` har omstrukturerats från ett enkelt linjärt format till ett professionellt dokumentformat med tydliga sektioner och rubriker.

## Vad som har ändrats

### 1. **Dokumenthuvud**
- Lagt till projekttitel och dokumentidentifiering
- Visuella separatorer (====) för tydlighet

### 2. **Projektinformation**
Ny sektion som beskriver:
- Beskrivning av systemet
- Huvudkomponenter
- Kommunikationsprotokoll
- Datum

### 3. **Systemöversikt**
Tabell som listar:
- Alla huvudkomponenter (UNIPI, Raspberry Pi, LOGO!, Displayer, etc.)
- Typ och antal
- Kommunikationsmetod
- Korta noteringar

### 4. **Elektriska Specifikationer**
Översiktstabell för:
- Spänningsnivåer (230VAC, 24VAC, 24VDC, 0-10V)
- Strömkrav
- Säkringsstorlekar
- Kabeltyper och områden

### 5. **Förbindningstabell - Detaljerad**
Originaldata omorganiserad i tydliga sektioner:

#### Sektion 1: Digitala Ingångar (DI)
- 15 rader med alla digitala ingångar
- Tydliga kolumnrubriker
- Inklusive nödstopp, knappar, och reservingångar

#### Sektion 2: Digitala Utgångar (DO) - Reläer
- 8 reläutgångar för ventiler och pump
- Koppling till plintrad X1

#### Sektion 3: Strömförsörjning
- 230VAC huvudmatning
- 24VAC för ventiler
- Gemensamma anslutningar

#### Sektion 4: Analoga Ingångar (AI)
- Markfuktgivare
- Reservsensorer
- Kopplingar via plintrad

#### Sektion 5: Analoga Utgångar (AO)
- Reservaktuatorer

#### Sektion 6: I2C Displayer
- Display 1 (20x4 LCD)
- Display 2 (2x8 LCD)
- GPIO-anslutningar

#### Sektion 7: Display 2 Knappar (GPIO)
- UP/DOWN/LEFT/RIGHT knappar
- GPIO-mappning

#### Sektion 8: Jordning & Skärm
- Skyddsjord för alla komponenter
- Kabelskärmar

#### Sektion 9: Nätverk & Kommunikation
- Ethernet-anslutningar
- Modbus TCP

### 6. **CAT7 Kabelfördelning - Översikt**
Ny sektion som visar:
- Kabel-ID (Cat7-A, Cat7-B, Cat7-C)
- Vilka ledare som används
- Funktion för varje kabel
- Optimering av kabelanvändning

### 7. **Modbus TCP Register - Översikt**
Helt ny tabell som sammanfattar:
- Alla Modbus-register (MW10-MW100)
- Registertyp (Holding)
- Beskrivning
- Läs/Skriv-rättigheter
- Datatyp och enhet

### 8. **PLC I/O Mappning - Översikt**
Ny tabell som visar:
- Alla I/O-adresser (%IX, %QX, %IW, %QW)
- Typ (Digital In/Out, Analog In/Out)
- Beskrivning
- Fysisk anslutning
- Koppling till Modbus-register

### 9. **Plintrad X1 - Layout**
Ny detaljerad tabell för plintrad:
- Plintnummer (1-12, COM, COM2, PE, ETH)
- Signaltyp
- I/O-typ
- Till vilken enhet
- Funktion
- Kabeltyp

### 10. **Tekniska Noter**
Utökad notsektion med:
- N1: Färgkodning
- N2: Intern vs extern installation
- N3: Plintrad X1 layout
- N4: Cat7 kabelanvändning
- N5: Display-anslutningar
- N6: Säkerhet (nödstopp NC)
- N7: Kommunikation
- N8: Strömförsörjning
- N9: Jordning
- N10: Modbus TCP

### 11. **Ändringshistorik**
Ny sektion för versionshantering:
- Version 1.0: Initial version
- Version 2.0: Omstrukturering 2025-12-19

## Fördelar med den nya strukturen

1. **Bättre Översikt**: Systemöversikt och specifikationer i början
2. **Lättare Navigation**: Tydliga sektioner med visuella separatorer
3. **Snabb Referens**: Nya översiktstabeller för Modbus, I/O, och plintrad
4. **Professionell**: Följer standarder för teknisk dokumentation
5. **Komplett**: All originaldata finns kvar plus mycket mer
6. **Användarvänlig**: Lättare att hitta information
7. **Dokumenterat**: Ändringshistorik och tekniska noter

## Filstorlek
- **Original**: 77 rader
- **Ny version**: 243 rader (+216% mer innehåll)
- **Backup**: Originalet sparad som `Förbindningstabell_med_Modbus_OLD.csv`

## Användning
Filen kan öppnas i:
- Excel eller LibreOffice Calc för formaterad vy
- Textredigerare för snabb sökning
- Git för versionshantering

## Kompatibilitet
All originaldata har bevarats och utökats. Inga befintliga referenser till Modbus-register eller I/O-adresser har ändrats.
