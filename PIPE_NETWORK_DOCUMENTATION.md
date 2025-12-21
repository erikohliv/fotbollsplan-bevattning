# Rörledningsnät och Zonspecifikationer

## Sammanfattning: Zon 7 vs Zon 5 - Dimension och Tryck

### Zon 5 (Hörn Nederst Höger)
- **Matningsrör**: PEM 75 (75 mm innerdiameter)
- **Tryck**: >10 bar (VARNING: HÖGT TRYCK)
- **Beskrivning**: Direkt matning från PEM 75-huvudledning
- **Status**: Kräver tryckdämpning för att skydda komponenter

### Zon 7 (Hörn Nederst Vänster)
- **Matningsrör**: PEM 50 (50 mm innerdiameter)
- **Tryck**: ~8-9 bar (ACCEPTABELT)
- **Beskrivning**: Matning via äldre PEM 50-ledning från Punkt 14
- **Status**: Naturlig tryckdämpning via rörfriktion

## Varför Spelar Dimensionen Roll för Trycket?

### 1. Hydraulisk Friktion och Tryckfall

Tryckförlusten i ett rör beror på flera faktorer enligt Darcy-Weisbach ekvationen:

```
ΔP = f × (L/D) × (ρv²/2)

där:
ΔP = tryckförlust (Pa)
f  = friktionsfaktor (dimensionslös)
L  = rörledningens längd (m)
D  = rörledningens innerdiameter (m)
ρ  = vattnets densitet (kg/m³)
v  = flödeshastighet (m/s)
```

**Viktigt**: Tryckförlusten är omvänt proportionell mot diametern (D). Ett mindre rör ger **högre friktion** och därmed **större tryckfall**.

### 2. Praktisk Jämförelse: PEM 75 vs PEM 50

#### PEM 75 (Zon 5):
- **Stor diameter** = Låg friktion
- **Högt flöde** med minimal tryckförlust
- **Resultat**: Nästan fullt pumptryck (>10 bar) når sprinklarna
- **Problem**: För högt tryck kan skada ventiler och sprinklers

#### PEM 50 (Zon 7):
- **Mindre diameter** = Högre friktion  
- **Samma flöde** genom smalare ledning ökar hastigheten
- **Resultat**: Trycket reduceras naturligt med ~2 bar (från 10-11 bar till 8-9 bar)
- **Fördel**: Skyddar utrustningen, tryck inom acceptabla gränser

### 3. Flödeshastighet och Reynolds-tal

För att förstå skillnaden fullt ut:

```
v = Q / A

där:
v = flödeshastighet (m/s)
Q = volymflöde (m³/s)
A = tvärsnittsarea = π(D/2)² (m²)
```

**PEM 75**: A = π × (0.075/2)² ≈ 0.00442 m²
**PEM 50**: A = π × (0.050/2)² ≈ 0.00196 m²

Med samma flöde Q blir hastigheten i PEM 50 **mer än dubbelt så hög**, vilket ger kraftigt ökat tryckfall.

### 4. Systemdesign och Pumpens Prestanda

Pumpen (E.M.S. DX 12-40T) har följande egenskaper:
- **Max tryckhöjd**: 116 m (≈11.6 bar)
- **Max flöde**: 250 l/min

Vid **lågt flöde** (t.ex. när endast en zon är aktiv):
- Pumpen arbetar högt upp på sin kurva
- **Statiskt tryck** kan överstiga 10 bar
- Detta är farligt för magnetventiler och sprinklers som vanligtvis är dimensionerade för max 8-10 bar

**Lösning för Zon 7**: Den äldre PEM 50-ledningen fungerar som en **naturlig tryckregulator**:
- Friktionsförlusten absorberar överskottstrycket
- Resultatet är ett säkert arbetstryck på 8-9 bar
- Ingen extra tryckdämpare behövs

## Rörledningstopologi

```
[Pump] ──PEM 90──> [Punkt 2 - T-förgrening]
                            │
                            ├──PEM 75──> [Punkt 6, 8, 10] (Zon 4, 5 - Höger sida)
                            │                └─> HÖGT TRYCK (>10 bar)
                            │
                            └──PEM 75──> [Punkt 14] (Vänster sida)
                                              │
                                              ├──PEM 75──> [Zon 6 - Hörn Övre Vänster]
                                              │                └─> HÖGT TRYCK (>10 bar)
                                              │
                                              └──PEM 50──> [Punkt 17/18 - Zon 7]
                                                               └─> ACCEPTABELT TRYCK (~8-9 bar)
```

## Konsekvenser för Drift och Underhåll

### Zon 5 (PEM 75 - Högt Tryck)
**Fördelar**:
- Maximalt flöde vid behov
- Kortare bevattningstid möjlig

**Nackdelar**:
- Risk för magnetventilsskador på lång sikt
- Högre slitage på sprinklers
- Möjlig vattenspray/dimbildning (för högt tryck)

**Åtgärder**:
- Överväg installation av tryckdämpare
- Kontrollera ventiler regelbundet
- Justera bevattningstider för att kompensera

### Zon 7 (PEM 50 - Naturlig Dämpning)
**Fördelar**:
- Tryck inom säkra gränser
- Längre livslängd på komponenter
- Ingen extra tryckdämpare behövs

**Nackdelar**:
- Något lägre kapacitet om framtida expansion krävs
- Kan vara känslig för ytterligare tryckfall vid läckage

**Åtgärder**:
- Behåll PEM 50 - fungerar som designad
- Ingen uppgradering nödvändig för Zon 7

## Mätdata och Verifikation

För att verifiera detta system har vi:

1. **Tryckgivare** (AI2 - Terminal X3):
   - Mäter pumptryck i realtid
   - Värde skalat 0-100% (motsvarar 0-11.6 bar)
   - Modbus-register: MW33

2. **Flödesvakt** (DI6 - Terminal X3):
   - Detekterar om vatten flödar
   - Status i Modbus-register: MW55

3. **Säkerhetskontroller i PLC**:
   - Blockering vid högt tryck utan flöde (>90%)
   - Varning vid lågt tryck med flöde (<20%)
   - Se `api_main.py` för full logik

## Rekommendationer

### Kortsiktigt:
1. **Övervaka** tryck i Zon 4, 5, 6 (PEM 75) - logga MW33 under drift
2. **Dokumentera** tryckskillnader mellan zoner
3. **Inspektera** ventiler på högtryckszoner regelbundet

### Långsiktigt:
1. **Överväg** tryckdämpare för Zon 4, 5, 6 om skador uppstår
2. **Behåll** PEM 50 för Zon 7 - perfekt som den är
3. **Utbild** operatörer om tryckskillnader mellan zoner

## Tekniska Specifikationer

### Rörmaterial: PEM (Polyeten Medium Density)
- **PEM 90**: 90 mm ytterdiameter, ~81 mm innerdiameter
- **PEM 75**: 75 mm ytterdiameter, ~67.5 mm innerdiameter  
- **PEM 50**: 50 mm ytterdiameter, ~45 mm innerdiameter

### Tryckklasser:
- PEM SDR11: Max 16 bar (vid 20°C)
- Arbetsgränser: 8-10 bar rekommenderas för magnetventiler
- Pumpen kan generera >11 bar vid lågt flöde

## Referenser

- `irrigation_config.json` - Fullständig systemkonfiguration
- `api_main.py` - Tryck/flödesskydd (MW33, MW55)
- `README.md` - Modbus-register och I/O-mappning
- Pump manual: E.M.S. DX 12-40T

## Slutsats

**Dimension spelar en avgörande roll för tryck i bevattningssystemet.**

- **PEM 75 (Zon 5)**: Stor diameter ger högt tryck (>10 bar) - kräver observation
- **PEM 50 (Zon 7)**: Mindre diameter ger naturlig tryckdämpning till säkra nivåer (~8-9 bar)

Den äldre PEM 50-ledningen till Zon 7 är inte en nackdel - den är en **fördel** som skyddar utrustningen från överdrivet pumptryck. Detta är ett perfekt exempel på hur hydraulisk friktion kan användas konstruktivt i systemdesign.

---

*Dokumentation uppdaterad: 2025-12-21*
