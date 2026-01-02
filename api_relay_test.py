#!/usr/bin/env python3
"""
API Relätest - Kör igenom reläer via API med nedräkning
"""
import requests
import time
import sys

API_URL = "http://127.0.0.1:8000"
API_KEY = "kamp"

def test_sequence():
    print("\n" + "="*60)
    print("🔧 RELÄTEST VIA API - Sekvenstest")
    print("="*60)
    print("\nDetta kommer att aktivera alla reläer i sekvens:")
    print("  • Relä 1-7 (Zoner) - 3 sek vardera")
    print("  • Relä 8 (Pump) - 3 sek")
    print("\n⚠️  LYSSNA efter klick-ljud från reläerna!")
    print("="*60)
    
    # Klartecken
    input("\n👉 Tryck ENTER för att ge KLARTECKEN och starta nedräkning...")
    
    # Nedräkning 20 sekunder
    print("\n🕐 NEDRÄKNING STARTAR:\n")
    for i in range(20, 0, -1):
        print(f"    ⏱  {i:2d} sekunder kvar...  ", end='\r')
        sys.stdout.flush()
        time.sleep(1)
    
    print("\n\n" + "="*60)
    print("🚀 SEKVENS STARTAR NU!")
    print("="*60 + "\n")
    time.sleep(0.5)
    
    headers = {"X-API-Key": API_KEY}
    
    # Test zoner 1-7
    for zone in range(1, 8):
        print(f"⚡ ZON {zone} → Aktiverar relä {zone}...")
        try:
            response = requests.post(
                f"{API_URL}/command/manual",
                json={"zone": zone, "duration": 3, "user": "api-relay-test"},
                headers=headers,
                timeout=5
            )
            if response.status_code == 200:
                print(f"   ✅ Aktiverad - LYSSNA PÅ KLICK!")
            else:
                print(f"   ❌ Fel: Status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Fel: {e}")
        
        time.sleep(3.5)
        
        # Stoppa
        try:
            requests.post(f"{API_URL}/command/stop", 
                         json={"user": "api-relay-test"}, 
                         headers=headers, timeout=5)
        except:
            pass
        
        time.sleep(0.5)
        print()
    
    # Test pump (relä 8)
    print(f"⚡ PUMP → Aktiverar relä 8...")
    try:
        response = requests.post(
            f"{API_URL}/command/manual",
            json={"zone": 1, "duration": 3, "user": "api-relay-test"},
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            print(f"   ✅ Pump aktiverad - LYSSNA PÅ KLICK!")
        else:
            print(f"   ❌ Fel: Status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Fel: {e}")
    
    time.sleep(4)
    
    # Säkerställ att allt är av
    try:
        requests.post(f"{API_URL}/command/stop", 
                     json={"user": "api-relay-test"}, 
                     headers=headers, timeout=5)
        print("   🛑 Stoppad")
    except:
        pass
    
    print("\n" + "="*60)
    print("✅ SEKVENS KLAR!")
    print("="*60)
    print("\nResultat:")
    print("  Hörde du klick från alla 8 reläer?")
    print("  • Relä 1-7: Zonventiler")
    print("  • Relä 8: Pump")
    print("\n")

if __name__ == "__main__":
    try:
        test_sequence()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test AVBRUTET!")
        try:
            requests.post(f"{API_URL}/command/stop", 
                         json={"user": "api-relay-test"}, 
                         headers={"X-API-Key": API_KEY}, timeout=5)
            print("🛑 Alla reläer stoppade")
        except:
            pass
        sys.exit(0)
