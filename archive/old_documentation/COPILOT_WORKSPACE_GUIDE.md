# GitHub Copilot Workspace Mode Guide

## 🎯 Varför Workspace Mode?

När du öppnar din projektmapp som en **workspace** i VS Code får Copilot bättre kontext och kan hjälpa dig mer effektivt.

## ✅ Så här aktiverar du Workspace Mode

### Alternativ 1: Öppna via VS Code
```
File → Open Folder → Välj: /home/kamp/fotbollsplan-bevattning
```

### Alternativ 2: Öppna via Terminal
```bash
code /home/kamp/fotbollsplan-bevattning
```

### Alternativ 3: Öppna från SSH
Om du är ansluten via SSH till Raspberry Pi:
```bash
# Från din lokala dator med VS Code Remote SSH:
# 1. Öppna VS Code
# 2. Ctrl+Shift+P → "Remote-SSH: Connect to Host"
# 3. Välj din Raspberry Pi
# 4. File → Open Folder → /home/kamp/fotbollsplan-bevattning
```

## 📊 Vad händer när Workspace är aktiverat?

### Med Workspace ✅
- Copilot ser alla filer i projektet
- Kan söka semantiskt i hela kodbasen
- Autocomplete fungerar mellan filer
- Bättre feldetektering (syntax errors, imports)
- Snabbare navigation mellan filer
- Kan visa filträd och dependencies

### Utan Workspace ⚠️
- Copilot ser bara öppna filer
- Måste använda terminal-kommandon för att läsa filer
- Långsammare filnavigation
- Mindre kontext för AI-förslag

## 🔍 Hur vet du att Workspace är aktivt?

Titta längst ner till vänster i VS Code:
- ✅ **Aktivt**: Visar "fotbollsplan-bevattning" eller mappsökväg
- ❌ **Inaktivt**: Visar bara enstaka filnamn

## 🤖 Så använder du @workspace

När workspace är öppnat kan du skriva:

```
@workspace Hitta alla funktioner som använder I2C
@workspace Vilka filer läser från sensorer?
@workspace Sök efter alla TODO-kommentarer
@workspace Förklara hur bevattningssekvensen fungerar
```

## 💡 Tips

### Spara som Workspace
För att spara inställningar:
```
File → Save Workspace As... → fotbollsplan-bevattning.code-workspace
```

### Multi-root Workspace
Om du har flera relaterade projekt:
```
File → Add Folder to Workspace...
```

### Automatisk öppning
Lägg till i din `.bashrc`:
```bash
alias bevattning='code /home/kamp/fotbollsplan-bevattning'
```

## 🚀 Rekommenderade VS Code Extensions för projektet

```bash
# Python
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance

# Git
code --install-extension eamodio.gitlens

# Markdown
code --install-extension yzhang.markdown-all-in-one

# Remote SSH
code --install-extension ms-vscode-remote.remote-ssh

# I2C/Hardware (syntax highlighting)
code --install-extension platformio.platformio-ide
```

## ⚙️ Workspace Settings

Skapa `.vscode/settings.json` i projektmappen:
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.analysis.extraPaths": [
    "${workspaceFolder}"
  ],
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true
  },
  "search.exclude": {
    "**/node_modules": true,
    "**/.venv": true,
    "**/archive": true
  }
}
```

## 🔗 Nuläge

Enligt dina terminal-output:
```
Cwd: /home/kamp/fotbollsplan-bevattning
```

Men workspace är **INTE öppnat** - därför behöver Copilot köra terminal-kommandon för att läsa filer.

**Lösning**: Kör `code /home/kamp/fotbollsplan-bevattning` så får Copilot full kontext!

---

**Senast uppdaterad**: 2026-01-02  
**Relaterade filer**: 
- [README.md](README.md) - Projekt overview
- [TODO_CHECKLIST.md](TODO_CHECKLIST.md) - Uppgiftslista
