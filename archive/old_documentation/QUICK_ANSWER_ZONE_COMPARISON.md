# Snabbsvar: Zon 7 vs Zon 5 - Dimension och Tryck

## Fråga
Vilken dimension har matningen till Zon 7 jämfört med Zon 5, och varför spelar det roll för trycket?

## Kortfattat Svar

### Dimensioner
| Zon | Matningsrör | Ytterdiameter | Innerdiameter | Tryck |
|-----|-------------|---------------|---------------|--------|
| **Zon 5** | PEM 75 | 75 mm | ~67.5 mm | >10 bar (HÖGT) |
| **Zon 7** | PEM 50 | 50 mm | ~45 mm | 8-9 bar (SÄKERT) |

### Varför Spelar Det Roll?

**Enkel Förklaring:**
- **Mindre rör = Mer friktion = Lägre tryck**
- Zon 7 har **PEM 50** (mindre) → Högre friktion → Tryck dämpas naturligt
- Zon 5 har **PEM 75** (större) → Låg friktion → För högt tryck från pump

**Teknisk Förklaring:**
1. **Hydraulisk friktion**: Tryckförlust ∝ 1/D (omvänt proportionell mot diameter)
2. **Flödeshastighet**: v = Q/A, där A = π(D/2)²
   - PEM 50: A ≈ 0.00196 m²
   - PEM 75: A ≈ 0.00442 m²
   - Samma flöde Q → PEM 50 har >2× högre hastighet → Kraftigt ökat tryckfall

3. **Pumpens karakteristik**: 
   - Vid lågt flöde (en zon aktiv) genererar pumpen >10 bar statiskt tryck
   - PEM 50 absorberar ~2 bar genom friktion
   - PEM 75 passerar genom nästan allt tryck

### Praktisk Betydelse

**Zon 5 (PEM 75 - För stort rör):**
- ⚠️ PROBLEM: >10 bar tryck
- Risk för ventilskador
- Högre slitage på sprinklers
- Bör övervakas noga

**Zon 7 (PEM 50 - Perfekt dimension):**
- ✅ BRA: 8-9 bar tryck
- Naturlig tryckdämpning
- Skyddar utrustningen
- Ingen extra dämpare behövs
- Den "äldre" PEM 50-ledningen är faktiskt en **fördel**

## Konklusion

**Zon 7's mindre dimension (PEM 50) är en säkerhetsfunktion som skyddar systemet från pumpens höga tryck.**

Mindre rördiameter → Högre hydraulisk friktion → Tryckdämpning → Säker drift

---

📖 **Fullständig teknisk dokumentation:** [PIPE_NETWORK_DOCUMENTATION.md](PIPE_NETWORK_DOCUMENTATION.md)

📋 **Systemkonfiguration:** [irrigation_config.json](irrigation_config.json)

📘 **Huvuddokumentation:** [README.md](README.md)

*Uppdaterad: 2025-12-21*
