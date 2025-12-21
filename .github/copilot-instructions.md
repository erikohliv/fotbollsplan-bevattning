# GitHub Copilot Instructions för Fotbollsplan-bevattning

## Projektöversikt
Detta är ett automatiserat bevattningssystem för fotbollsplan som kombinerar:
- **PLC (Structured Text)**: Säkerhetskritisk realtidslogik för ventil- och pumpstyrning
- **Python Controller**: Väderdata från SMHI och markfukt, skriver till PLC via Modbus
- **FastAPI Backend**: REST API och webb-UI för styrning och övervakning
- **Hårdvara**: UNIPI 1.1 med Modbus, Raspberry Pi 4, Siemens LOGO, VFD-pump

## Kodningskonventioner

### Python
- Använd svensk kommentaring för domänspecifik logik (ventiler, zoner, bevattning)
- Engelska för generisk/teknisk kod när det är lämpligt
- Följ PEP 8 för kodstil
- Använd type hints där det är möjligt
- Använd `logging` för all loggning, inte `print()`
- Hårdkoda inte Modbus-adresser - använd definierade konstanter (MW_*)

### Modbus-kommunikation
- Alla Modbus-registeradresser ska definieras som konstanter med prefix `MW_`
- Använd `pymodbus` biblioteket för Modbus TCP-kommunikation
- Hantera både gamla och nya versioner av pymodbus:
  ```python
  try:
      from pymodbus.client import ModbusTcpClient
  except Exception:
      from pymodbus.client.sync import ModbusTcpClient
  ```
- Lägg alltid till felhantering för Modbus-operationer
- Logga alla Modbus-läs/skriv-operationer på DEBUG-nivå

### FastAPI
- Alla endpoints kräver API-nyckel via `X-API-Key` header
- Använd Pydantic models för request/response bodies
- Returnera tydliga felmeddelanden med lämpliga HTTP-statuskoder
- Dokumentera endpoints med docstrings

### Säkerhet
- **KRITISKT**: Hårdkoda aldrig API-nycklar eller credentials
- Använd miljövariabler via `.env` filer (se `api_.env.example`)
- Validera all input innan Modbus-skrivningar
- Implementera rate limiting för externa API-anrop
- Var försiktig med pumpstyrning - använd alltid anti-vattenslag-logik

## Viktig Domänlogik

### Anti-vattenslag
Ventiler måste alltid öppnas **före** pumpstart och stängas **efter** pumpstopp:
1. Öppna ventil
2. Vänta `OpenDelay` sekunder (default 5s)
3. Starta pump
4. Kör bevattning
5. Stoppa pump
6. Vänta `CloseDelay` sekunder (default 10s)
7. Stäng ventil

### Zonbyten
Vid byte mellan zoner:
1. Stoppa pump
2. `CloseDelay` - vänta innan ventil stängs
3. Stäng gamla ventiler
4. `PauseDelay` - paus mellan zoner (default 10s)
5. Öppna nya ventiler
6. `OpenDelay` - vänta innan pump startar
7. Starta pump

### Modbus-register (se README.md för fullständig lista)
Viktiga register:
- **MW10**: Remote_Command (50=auto start)
- **MW20-21**: Set_Tid_Center/Horn (bevattningstider)
- **MW30-32**: Markfukt, Regn 24h, Temperatur
- **MW50-53**: Status (zon, pump, steg, vald zon)
- **MW60-64**: Manual mode, start, zon-val, körtid
- **MW70-73**: Heartbeat, EventMask, BlockReason

## Bygg och Test

### Setup miljö
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r api_requirements.txt
```

### Kör FastAPI lokalt
```bash
cd /home/runner/work/fotbollsplan-bevattning/fotbollsplan-bevattning
source .venv/bin/activate
uvicorn api_main:app --host 0.0.0.0 --port 8000
```

### Testa API
```bash
curl -H "X-API-Key: <nyckel>" http://localhost:8000/status
```

### Python Controller
```bash
# En körning
python3 bevattning_controller.py --auto-start

# Loop-läge
python3 bevattning_controller.py --loop --interval 60 --auto-start
```

## Beroenden
- **FastAPI**: REST API framework
- **pymodbus**: Modbus TCP-kommunikation
- **python-dotenv**: Miljövariabelhantering
- **pydantic**: Datavalidering
- **requests**: HTTP-anrop till SMHI/väder-API
- **uvicorn**: ASGI-server för FastAPI

**Lägg inte till nya beroenden** utan att först diskutera nödvändigheten.

## Vanliga Uppgifter

### Lägg till nytt Modbus-register
1. Definiera konstant i både `api_main.py` och `bevattning_controller.py`
2. Uppdatera README.md med registerbeskrivning
3. Lägg till läs/skriv-logik där det behövs
4. Testa mot PLC eller Modbus-simulator

### Lägg till ny API-endpoint
1. Skapa Pydantic model om request body behövs
2. Lägg till endpoint-funktion med `require_key` dependency
3. Implementera Modbus-kommunikation med felhantering
4. Testa med curl-kommandon
5. Uppdatera README.md med exempel

### Ändra bevattningslogik
**VAR FÖRSIKTIG**: Ändringar i bevattningslogik kan påverka hårdvara och vattenslag.
1. Diskutera förändringen först
2. Implementera i Python controller eller FastAPI efter behov
3. Verifiera att anti-vattenslag-logik bibehålls
4. Testa grundligt innan deployment på Raspberry Pi

## Filer och Struktur
- `api_main.py`: FastAPI backend
- `bevattning_controller.py`: Python SMHI-controller
- `api_requirements.txt`: Python-beroenden
- `api_.env.example`: Exempel på miljövariabler
- `Fotbollsplan_Master_Version12.st`: PLC-program (Structured Text)
- `systemd_bevattning-api.service`: systemd service-fil
- `README.md`: Huvuddokumentation

## Begränsningar och Överväganden
- Koden körs på Raspberry Pi 4 med begränsad CPU/minne
- PLC körs med 100ms task-cykel - håll Modbus-skrivningar rimliga
- Systemet styr fysisk pump och ventiler - säkerhet först
- Nätverkskommunikation kan vara instabil - implementera timeouts och retries
- Väder-API kan vara nere - ha fallback-värden

## Språkanvändning
- **Svenska**: Domänspecifika termer (bevattning, zoner, ventiler, pump)
- **Svenska**: Kommentarer som förklarar bevattningslogik
- **Engelska**: Tekniska begrepp (Modbus, API, endpoints)
- **Engelska**: Variabelnamn i kod (följer Python-konventioner)
- **Blandning är OK**: README och denna fil blandar språk naturligt

## Support och Dokumentation
- Huvuddokumentation: `README.md`
- Modbus-mappning: `unipi-11-modbus-map.xlsx`
- PLC-logik: `Fotbollsplan_Master_Version12.st`
- Exempel: Se cURL-kommandon i README.md
