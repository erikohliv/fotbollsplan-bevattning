# Gmail SMTP-konfiguration för Bevattningssystemet

## 🔐 Gmail App-lösenord (2-stegsverifiering)

För att systemet ska kunna skicka e-postnotifieringar via Gmail behöver du skapa ett **App-lösenord**.

### Steg 1: Aktivera 2-stegsverifiering

1. Gå till din Google-konto: https://myaccount.google.com/
2. Klicka på **Säkerhet** i vänstermenyn
3. Under "Logga in på Google", klicka på **Tvåstegsverifiering**
4. Följ instruktionerna för att aktivera 2-stegsverifiering (om inte redan aktivt)

### Steg 2: Skapa App-lösenord

1. När 2-stegsverifiering är aktivt, gå tillbaka till **Säkerhet**
2. Under "Logga in på Google", klicka på **Applösenord** (längst ner)
   - Om du inte ser "Applösenord", säkerställ att 2-stegsverifiering är aktiverat
3. Välj app: **Mail**
4. Välj enhet: **Annan (anpassat namn)**
5. Skriv: `Fotbollsplan Bevattning`
6. Klicka **Generera**

### Steg 3: Kopiera lösenordet

Google visar ett **16-siffrig lösenord** i formatet: `xxxx xxxx xxxx xxxx`

**VIKTIGT:** 
- Kopiera detta lösenord **NU** - det visas bara en gång!
- Ta bort mellanslag när du klistrar in det i systemet
- Exempel: `abcd efgh ijkl mnop` → `abcdefghijklmnop`

### Steg 4: Konfigurera systemet

#### Automatisk installation (setup.sh):
När du kör `setup.sh` kommer du bli tillfrågad:
```
SMTP User (Gmail address): erik.ohliv@gmail.com
SMTP Password (App-lösenord från Google): abcdefghijklmnop
```

#### Manuell konfiguration (api_.env):
Redigera `api_.env` och uppdatera följande rader:
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=erik.ohliv@gmail.com
SMTP_PASS=abcdefghijklmnop    # 16-siffrig App-lösenord UTAN mellanslag
SMTP_FROM=erik.ohliv@gmail.com
SMTP_TO=erik.ohliv@gmail.com
SMTP_TIMEOUT=10
```

### Steg 5: Testa konfigurationen

Kör email-testet för att verifiera:
```bash
cd /home/kamp/fotbollsplan-bevattning
source .venv/bin/activate
python3 email_test.py --send-alarm-test
```

**Förväntat resultat:**
```
✓ SMTP-konfiguration laddad
✓ TLS aktiverat
✓ Inloggning lyckades
✓ E-post skickat till erik.ohliv@gmail.com
```

### Kontrollera din inkorg

Efter testet, kolla:
1. **Inbox** - testet ska skicka två mail:
   - "Test från Fotbollsplan Bevattning"
   - "🚨 KRITISKT LARM: System Health Alert"
2. **Spam-mapp** - Gmail kan ibland filtrera automatiska mail

---

## 🔧 Felsökning

### Problem: "535 Authentication failed"

**Orsak:** Fel App-lösenord eller 2-stegsverifiering inte aktiverat

**Lösning:**
1. Verifiera att 2-stegsverifiering är aktivt
2. Skapa nytt App-lösenord
3. Kopiera utan mellanslag

### Problem: "Connection timeout"

**Orsak:** Brandvägg eller nätverksproblem

**Lösning:**
```bash
# Testa anslutning till Gmail SMTP
telnet smtp.gmail.com 587
```

Om detta fungerar ska du se:
```
220 smtp.gmail.com ESMTP
```

### Problem: Mail hamnar i spam

**Lösning:**
1. Markera mailet som "Inte spam" i Gmail
2. Lägg till avsändaren i kontakter
3. Efter några meddelanden lär Gmail sig att lita på avsändaren

---

## 📧 Vilka notifieringar skickas?

Systemet skickar e-post när:

### Kritiska larm:
- ⚠️ **Motorskydd utlöst** (DI10) - Pumpen är överhettad/överbelastad
- ⚠️ **Nödstopp aktiverat** (DI3) - Systemet har stoppats manuellt
- ⚠️ **Tryckvakt alarm** (DI5) - Tryckfall detekterat (läckage?)
- ⚠️ **Flödesvakt alarm** (DI7) - Inget flöde trots pump igång
- ⚠️ **Säkring 24VDC utlöst** (DI11) - Strömförsörjning till PLC/sensorer
- ⚠️ **Säkring 24VAC utlöst** (DI12) - Strömförsörjning till ventiler
- ⚠️ **API otillgänglig** - Systemhälsan har försämrats

### Informationsmeddelanden:
- ℹ️ **Bevattning påbörjad** - System startar bevattningssekvens
- ℹ️ **Bevattning avslutad** - System avslutat normalt
- ℹ️ **Vinterläge aktivt** - Ingen bevattning mellan 1 nov - 31 mars

---

## 🔒 Säkerhet

### App-lösenord är säkrare än ditt vanliga lösenord

- ✅ Kan inte användas för att logga in på ditt Google-konto
- ✅ Kan återkallas när som helst utan att påverka ditt huvudlösenord
- ✅ Begränsat till enbart SMTP-åtkomst

### Återkalla App-lösenord

Om du tror att lösenordet har komprometterats:
1. Gå till https://myaccount.google.com/apppasswords
2. Klicka på **Återkalla** bredvid "Fotbollsplan Bevattning"
3. Skapa ett nytt och uppdatera `api_.env`

---

## 📚 Relaterad dokumentation

- [README.md](README.md) - Systemöversikt
- [INSTALLATION.md](INSTALLATION.md) - Fullständig installationsguide
- [INSTALL_SYSTEM2.md](INSTALL_SYSTEM2.md) - System 2.0 detaljer

---

## 💡 Tips

### Testa regelbundet
Kör email-testet en gång i månaden för att säkerställa att notifieringar fungerar:
```bash
python3 email_test.py
```

### Övervaka larm-historik
Systemet loggar alla e-postutskick:
```bash
sudo journalctl -u bevattning-controller | grep "E-post"
```

### Använd mobilnotiser
För snabbare varningar, lägg till en e-post-till-SMS-tjänst som mottagare:
- Gmail → Filtrera → Vidarebefordra till SMS-gateway
- Eller använd tjänster som IFTTT
