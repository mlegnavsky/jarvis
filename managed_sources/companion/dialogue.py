"""Bounded Czech follow-up policy, independent of HA/OpenAI."""
import re
import unicodedata

def normalized(text):
 return ' '.join(re.findall(r'\w+', ''.join(c for c in unicodedata.normalize('NFKD',text.casefold()) if not unicodedata.combining(c))))

def is_stop(text):
 return normalized(text) in {'konec','dekuji konec','diky konec','uz koncime','to je vse','to je vsechno','to je vsechno dekuji','ukonci rozhovor','prestan poslouchat','dobrou noc'}

def recent_session(sessions,device,now):
 if not device or device not in sessions:return None
 conversation,at=sessions[device]
 return conversation if 0<=now-at<=900 else None

def should_continue(text,response,turns,elapsed):
 if is_stop(text) or not normalized(text) or not response.strip():return False
 if normalized(text)==normalized(response):return False
 return turns<32 and elapsed<1200

COMPANION_INSTRUCTIONS='''
Režim domácího společníka Jarvis:
Veď přirozený český rozhovor i o tématech mimo domácnost. Nejsi pouze ovladač zařízení.
Navazuj na dosavadní kontext a zájmena; při nejasnosti se krátce doptej.
Odpověď nemusí být jediná věta ani končit otázkou. Mluv zpravidla ve dvou až čtyřech větách, podrobněji podle přání člověka.
Nenabízej při každé odpovědi seznam příkazů a neopakuj stále nabídku pomoci. Ovládání domu používej pouze pro požadovanou akci.
Respektuj ukončení rozhovoru. Neprohlašuj, že sdílíš historii či paměť s ChatGPT, ani že slyšíš během přehrávání hlasu.
Zachovej existující omezení oprávnění a pravidla pro potvrzování zásahů do domácnosti.
'''
