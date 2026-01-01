# GitHub Copilot Instructions för Fotbollsplan-bevattning (Systemversion 2.0)

## 1. Projektöversikt & Syfte
Detta projekt styr bevattning av en fotbollsplan via en Raspberry Pi 4 och UniPi Neuron PLC.
- **Python (Hjärnan):** Hämtar väder, fattar beslut, skickar kommandon.
- **PLC (Ryggraden):** Sköter hårdvarustyrning, säkerhetslogik och direkt input-avläsning.

Målet är ett robust system som är **enkelt att installera** och driftsätta.

## 2. Kritiska Hårdvaruregler (THE TRUTH)
Följ ALLTID denna konfiguration. Gissa aldrig.
- **Borttaget:** Display 2 (D2) är borta. Ta bort all kod som refererar till den.
- **Ny Input:** Användargränssnitt på plats styrs av 4 st Arkadknappar via I2C (PCF8574).
- **Huvudfil:** Logiken ligger i `bevattning_controller.py` (inte main.py).
- **IO-Mappning:** Se `hardware_map.csv`. Hårdkoda aldrig pinnar.

## 3. Säkerhet & Larm (PLC = SAFETY GUARDIAN)
Säkerheten hanteras primärt av PLC:n för maximal tillförlitlighet. Python-koden ska respektera detta.
1.  **Motorskydd (I10) & Nödstopp (I03):** PLC bryter pumpen direkt. Python ska upptäcka detta via Modbus och logga larmet.
2.  **Mjukstartare fel (I08):** PLC stoppar pumpen.
3.  **Driftövervakning:** Om Tryckvakt (I09) eller Flödesvakt (I07) larmar -> Python skickar stoppkommando och larmar användare.

## 4. Robusthet & Offline-läge
1.  **Lokal Prioritet:** PLC:n läser knapparna direkt. Även om Python-scriptet hänger sig eller startar om, ska fysiska knappar (Start/Stopp/Nödstopp) fungera via PLC-logiken.
2.  **Nätverksberoende:** `bevattning_controller.py` får inte krascha om internet saknas. Använd timeouts på alla API-anrop (OpenMeteo).

## 5. Installation & Setup (MAKE IT SIMPLE)
Installationen ska vara så automatiserad som möjligt.
- **Skript:** Sträva efter att ha ett `setup.sh` som:
    1.  Skapar Python `venv` (Virtual Environment).
    2.  Installerar beroenden från `requirements.txt`.
    3.  Aktiverar I2C på Raspberry Pi (om möjligt, annars instruera användaren).
    4.  Sätter upp `systemd`-service för autostart vid boot.
- **Dokumentation:** README ska innehålla en tydlig "Steg-för-steg" för en ren Raspberry Pi OS-installation.

## 6. Logikregler
- **Anti-Vattenslag:** Starta aldrig pump mot stängd ventil. Öppna ventil -> Vänta 5s -> Starta pump.
- **Vinterläge:** 1 nov - 31 mars = Ingen bevattning.
- **Väder:** OpenMeteo (Håkanryd, Bromölla).

## 7. Kodningsstil
- **Språk:** Svenska för logik/kommentarer. Engelska för kodstruktur.
- **Logging:** Använd `logging`-modulen (roterande loggfiler).
- **Refactoring:** Behåll befintlig filstruktur där det går. Gör inga onödiga omskrivningar.
- 
