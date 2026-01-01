# Visuell Jämförelse: Zon 5 vs Zon 7 Tryckförhållanden

## Rörledningsdimensioner och Tryckprofil

```
PUMP STATION → → → → → → → → → → → → → → → → → → → → ZONES
E.M.S. DX 12-40T
Max: 11.6 bar                                                    

    ║                                                             
    ║ PEM 90                                                      
    ║ Tryck: ~11 bar                                              
    ║                                                             
    ▼                                                             
┌───────────────┐                                                
│  Punkt 2      │                                                
│  T-förgrening │                                                
└───────┬───────┘                                                
        │                                                        
        ├─────────────────────────────────────┐                 
        │ PEM 75                               │ PEM 75         
        │ Låg friktion                         │ Låg friktion   
        │ Tryck: ~10.5 bar                     │ Tryck: ~10.5 bar
        ▼                                      ▼                 
   ┌─────────┐                            ┌─────────┐           
   │ Punkt 6 │                            │ Punkt 14│           
   │ Höger   │                            │ Vänster │           
   └────┬────┘                            └────┬────┘           
        │                                      │                
        │                                      ├────────────────┐
        │                                      │ PEM 75         │ PEM 50
        │                                      │ Låg friktion   │ HÖG FRIKTION
        │                                      │ ~10.5 bar      │ Tryckfall: -2 bar
        ▼                                      ▼                ▼
    ┌───────┐                             ┌───────┐        ┌───────┐
    │ ZON 5 │                             │ ZON 6 │        │ ZON 7 │
    │Ventil │                             │Ventil │        │Ventil │
    └───┬───┘                             └───┬───┘        └───┬───┘
        │                                     │                │
    ╔═══▼═══╗                             ╔═══▼═══╗        ╔═══▼═══╗
    ║>10 BAR║ ⚠️ VARNING                  ║>10 BAR║        ║ 8-9   ║ ✅ BRA
    ║  HÖGT ║ Risk för skador             ║  HÖGT ║        ║ BAR   ║ Säkert tryck
    ╚═══════╝                             ╚═══════╝        ╚═══════╝
    PEM 75                                PEM 75           PEM 50
    ø 75mm                                ø 75mm           ø 50mm
    ID ~67.5mm                            ID ~67.5mm       ID ~45mm
```

## Tvärsnittsarea Jämförelse

```
PEM 75 (Zon 5):                    PEM 50 (Zon 7):
┌─────────────────────┐            ┌────────────┐
│                     │            │            │
│      ø 75 mm        │            │  ø 50 mm   │
│                     │            │            │
│  A = 0.00442 m²     │            │ A = 0.00196│
│                     │            │    m²      │
│   Stor tvärsn.      │            │            │
│   Låg hastighet     │            │ Liten      │
│   Låg friktion      │            │ tvärsn.    │
└─────────────────────┘            │ Hög hastigh│
                                   │ Hög frikti │
        STOR AREA                  └────────────┘
        ↓                               LITEN AREA
    Vatten flödar långsammare           ↓
    Minimal friktion                Vatten flödar snabbare
    Tryck bibehålls (>10 bar)       Mycket friktion
                                    Tryck dämpas (8-9 bar)
```

## Flödesprofil vid 100 l/min

```
Parameter               ZON 5 (PEM 75)    ZON 7 (PEM 50)
─────────────────────────────────────────────────────────
Diameter (ID)           67.5 mm           45 mm
Tvärsnittsarea          4420 mm²          1960 mm²
Flödeshastighet         0.38 m/s          0.85 m/s
Friktion                LÅG               HÖG
Tryckfall per 10m       ~0.1 bar          ~0.5 bar
Slutligt tryck          10.5 bar          8.5 bar
Status                  ⚠️ VARNING        ✅ ACCEPTABELT
```

## Tryckgraf: Pump till Zon

```
Tryck
(bar)
12 │                                                     
11 │●                                                    
10 │ ●─────────────────────────────●─────────────●      
 9 │                                            │  ●     
 8 │                                            │   ●    
 7 │                                            │    ●─● ZON 7
 6 │                                            │      (PEM 50)
 5 │                                         ZON 5      
 4 │                                         (PEM 75)   
 3 │                                                     
 2 │                                                     
 1 │                                                     
 0 └─────────────────────────────────────────────────────>
   Pump  PEM90  Punkt2  PEM75   Punkt   PEM75/50  Zon
                                6/14                     

Förklaring:
● = Tryck vid varje punkt i systemet
─ = Tryck bibehålls (låg friktion i PEM 75)
│ = Tryckfall (hög friktion i PEM 50)
```

## Fysisk Förklaring

### Varför Mindre Rör = Lägre Tryck?

**1. Samma vattenflöde måste genom mindre öppning:**
```
100 liter/min → PEM 75 (stor)  = Lugnt flöde, låg hastighet
100 liter/min → PEM 50 (liten) = Snabbt flöde, hög hastighet
```

**2. Högre hastighet = Mer friktion mot rörväggar:**
```
Vattenpartiklar
   ↓↓↓↓↓↓↓↓↓       PEM 75: Gott om plats, lite friktion
   ║      ║        
   ║  →→  ║        
   ║      ║        
   ↓↓↓↓↓↓↓↓↓        

   ↓↓↓↓↓           PEM 50: Trångt, mycket friktion
   ║→→→→║          Vattenpartiklar trycks mot väggarna
   ↓↓↓↓↓           Energi omvandlas till friktion/värme
```

**3. Friktion "äter upp" tryckenergi:**
```
Pumptryck (11 bar) - Friktion (2 bar) = Zontryck (9 bar) ✅
Pumptryck (11 bar) - Friktion (0.5 bar) = Zontryck (10.5 bar) ⚠️
```

## Sammanfattning med Symboler

```
╔══════════════════════════════════════════════════════════╗
║  ZON 5: PEM 75 → Stor diameter → Låg friktion → 🔴 HÖGT ║
║                                                  TRYCK   ║
║  ZON 7: PEM 50 → Liten diameter → Hög friktion → 🟢 BRA ║
║                                                   TRYCK  ║
╚══════════════════════════════════════════════════════════╝
```

---

**Slutsats**: Zon 7's "äldre" PEM 50-ledning är faktiskt **perfekt dimensionerad** för att skydda utrustningen från pumpens höga tryck. Den fungerar som en naturlig tryckdämpare utan extra kostnad eller underhåll.

📖 Se [PIPE_NETWORK_DOCUMENTATION.md](PIPE_NETWORK_DOCUMENTATION.md) för matematiska beräkningar och detaljerad teknisk analys.
