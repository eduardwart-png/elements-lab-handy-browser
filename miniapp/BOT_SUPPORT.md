# Kontakt über den Bot: so funktioniert es

Interessenten schreiben dem Bot (Befehl /kontakt oder Link unten). Jede Person bekommt in eurer internen Team-Gruppe ein eigenes Thema. Was ihr dort schreibt, schickt der Bot an die Person zurück. Einfache Fragen (Mindestbestellwert, Versand, Lieferzeit, Rabatt, Sammelbestellung, Preisliste) beantwortet der Bot sofort mit den Werten aus den Shop-Konditionen. Alles andere (zum Beispiel Qualität, Zahlung, Herkunft) beantwortet ihr selbst. Der Bot sagt der Person nur: „Wir melden uns, sobald wir können.“ Eine feste Antwortzeit verspricht er nicht.

## 1. Team-Gruppe anlegen (einmalig, Eddy)
1. In Telegram eine neue Gruppe anlegen, Name zum Beispiel „Elements Kontakt (intern)“.
2. Gruppeninfo → Bearbeiten → **Themen** einschalten.
3. Den Shop-Bot zur Gruppe hinzufügen und zum **Admin** machen, mit dem Recht **Themen verwalten**.
4. René zur Gruppe hinzufügen. Sonst niemanden: Jede Nachricht, die ein Mitglied in ein Thema schreibt, geht an den Interessenten.

## 2. Gruppe mit dem Bot verbinden
Der Bot braucht die Nummer der Gruppe (sie beginnt mit -100). Ihr seht sie, wenn ihr die Gruppe in Telegram Web öffnet: Sie steht hinten in der Adresszeile. Diese Nummer kommt als Eintrag `ELEMENTS_TEAM_CHAT_ID` in die Einstellungsdatei des Shops, in der auch der Bot-Zugang steht; danach den Shop-Dienst einmal neu starten. Am einfachsten: Hermes darum bitten und die Nummer nennen. Ohne diesen Eintrag ist der Kontakt aus; der Bot antwortet dann „Kontakt ist gerade nicht verfügbar, bitte schreibe später“.

Optional für Beitrittsanfragen zur Kunden-Gruppe: zusätzlich `ELEMENTS_GROUP_CHAT_ID` (Nummer der Kunden-Gruppe, Bot dort Admin mit „Nutzer hinzufügen“). Dann begrüßt der Bot neue Anfragende, fragt „Händler oder Endkunde?“ und nimmt die Anfrage an.

## 3. Befehle für das Team
- Im Thema einfach antworten: Text, Foto oder Datei gehen an die Person.
- `/sperren` – Person wird still ignoriert. `/entsperren` hebt das auf.
- `/schliessen` – Thema schließen; schreibt die Person wieder, öffnet es sich von selbst.
- `/offen` (überall in der Gruppe) – Liste der unbeantworteten Anfragen, älteste zuerst.
- Erinnerung: Der Bot erinnert **nicht** von sich aus. Wer sie möchte, trägt `ELEMENTS_SUPPORT_DIGEST=1` ein; dann kommt höchstens einmal am Tag eine Liste der Anfragen, die länger als 24 Stunden warten. Jederzeit mit `/offen` abrufbar.

Schutz: höchstens 20 Nachrichten pro Stunde und Person, keine Texte über 4000 Zeichen, keine Dateien über 20 MB.

## 4. Angehefteter Beitrag für den Kanal
> **Fragen an Elements Labs?**
> Schreib uns direkt über den Bot: Wir melden uns, sobald wir können. Antworten zu Mindestbestellwert, Versand, Lieferzeit und Rabatt bekommst du sofort.
>
> Knopf: **Frage zu Qualität / Kontakt** → `https://t.me/ElementsLabs_Shop_bot?start=kontakt`

Einladungslinks je Quelle (zum Beispiel Kanal, Instagram) mit Zähler legt Hermes mit `tools/invite_links.py` an.
