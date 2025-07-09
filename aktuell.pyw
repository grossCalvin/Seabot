import os
import sys
import tkinter as tk
from tkinter import messagebox
import subprocess
import requests

GEGNER_DIR = "ressources/gegner"
GEGNER_DIR_M = "ressources/monsters"
GEGNER_PREVIEW = "ressources/preview"
CURRENT_VERSION = "2.5"

def check_for_update_and_restart():
    try:
        version_url = "https://raw.githubusercontent.com/grossCalvin/Seabot/refs/heads/main/version.txt"
        response = requests.get(version_url, timeout=5)
        if response.status_code == 200:
            remote_version = response.text.strip()
            if remote_version != CURRENT_VERSION:
                print(f"⬆️ Neue Version {remote_version} verfügbar (aktuell: {CURRENT_VERSION})")
                messagebox.showinfo("Update verfügbar", f"Version {remote_version} ist verfügbar.\nDas Programm wird jetzt aktualisiert.")
                updated = update_script_from_github()
                return updated
    except Exception as e:
        print(f"❌ Fehler bei Updateprüfung: {e}")
    return False

def check_requirements_and_restart():
    try:
        url = "https://raw.githubusercontent.com/grossCalvin/Seabot/refs/heads/main/requirements.txt"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            required_packages = [line.strip() for line in response.text.splitlines() if line.strip() and not line.startswith("#")]

            import_name_map = {
                "opencv-python": "cv2",
                "pillow": "PIL",
                "pyautogui": "pyautogui",
                "pytesseract": "pytesseract",
                "numpy": "numpy",
                "matplotlib": "matplotlib",
                "requests": "requests"
            }

            missing = []
            for pkg in required_packages:
                import_name = import_name_map.get(pkg, pkg)
                try:
                    __import__(import_name)
                except ImportError:
                    missing.append(pkg)

            if missing:
                print(f"🔧 Installiere fehlende Pakete: {missing}")
                subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
                return True
        else:
            print("⚠️ Konnte requirements.txt nicht abrufen.")
    except Exception as e:
        print(f"❌ Fehler bei der Paketprüfung: {e}")
    return False

def update_script_from_github():
    try:
        script_url = "https://raw.githubusercontent.com/grossCalvin/Seabot/refs/heads/main/aktuell.pyw"
        local_path = os.path.abspath(sys.argv[0])

        response = requests.get(script_url, timeout=5)
        if response.status_code == 200:
            with open(local_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(response.text)
            print("✅ Skript erfolgreich aktualisiert.")
            return True
        else:
            print(f"⚠️ Fehler beim Abrufen: Status {response.status_code}")
    except Exception as e:
        print(f"❌ Fehler beim Skript-Update: {e}")
    return False

def restart_script():
    print("🔄 Starte Skript neu...")
    python = sys.executable
    script_path = os.path.abspath(sys.argv[0])
    subprocess.Popen([python, script_path], close_fds=True)
    sys.exit(0)

if check_requirements_and_restart():
    restart_script()
if check_for_update_and_restart():
    restart_script()

import pyautogui
import pytesseract
import time
import math
import platform
import re
import cv2
import numpy as np
from collections import namedtuple
from datetime import datetime
import tkinter.font as tkFont
from tkinter import ttk
from PIL import Image, ImageTk, ImageGrab, ImageEnhance, ImageOps
from pyautogui import locateOnScreen, ImageNotFoundException
    

# Pfad für Tesseract je nach Betriebssystem
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Pfad zu Tesseract auf Windows
elif platform.system() == "Linux":
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'  # Standardpfad für Tesseract auf Linux
else:
    raise EnvironmentError("Unbekanntes Betriebssystem. Bitte Tesseract manuell konfigurieren.")


class BotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Seabot (Version: {CURRENT_VERSION})")
        if platform.system() == "Linux":
            self.root.geometry("530x320")
        else:
            self.root.geometry("470x320")
        self.running = False
        
        self.zugriff = True 
        self.zugriff_counter = 0
        self.bm_versuche = 0
        self.captchafail = False

        # Hier wäre der Default font anzugeben:
        #default_font = tkFont.nametofont("TkDefaultFont")
        #default_font.configure(family="Arial", size=9)


        # Mapping als Konstante:
        self.starting_point_map = {
        "TopLeft": 1,
        "TopRight": 2,
        "BottomRight": 3,
        "BottomLeft": 4
        }

        self.aktueller_startpunkt = None

        # Gegnerauswahl oben
        self.selection_frame = tk.Frame(root)
        self.selection_frame.pack(pady=10)

        # --- Erste Zeile ---
        # Gegnerauswahl
        tk.Label(self.selection_frame, text="Gegnerauswahl:").grid(row=0, column=0, padx=5, sticky="w")

        self.opponent_var = tk.StringVar()
        self.opponent_selector = ttk.Combobox(
            self.selection_frame, textvariable=self.opponent_var, state="readonly", width=20
        )
        self.opponent_selector.grid(row=0, column=1, padx=5, sticky="w")
        self.opponent_selector.bind("<<ComboboxSelected>>", self.change_image)

        # Chesthunt
        self.chesthunt_var = tk.BooleanVar(value=False)
        self.chesthunt_checkbox = tk.Checkbutton(
            self.selection_frame, text="Chesthunt", variable=self.chesthunt_var, command=self.toggle_chesthunt
        )
        self.chesthunt_checkbox.grid(row=0, column=2, padx=5, sticky="w")

        # Dwarfhunt
        self.dwarfhunt_var = tk.BooleanVar(value=False)
        self.dwarfhunt_checkbox = tk.Checkbutton(
            self.selection_frame, text="Dwarfhunt", variable=self.dwarfhunt_var, command=self.toggle_dwarfhunt
        )
        self.dwarfhunt_checkbox.grid(row=0, column=3, padx=5, pady=0, sticky="w")

        # --- Zweite Zeile ---
        # Daily-Quest Selector
        tk.Label(self.selection_frame, text="Daily-Level:").grid(row=1, column=0, padx=5, sticky="w")

        self.dailylevel_var = tk.StringVar(value="None")
        self.dailylevel_selector = ttk.Combobox(
            self.selection_frame,
            textvariable=self.dailylevel_var,
            state="disabled",
            values=["None", "5", "12"],
            width=5
        )
        self.dailylevel_selector.grid(row=1, column=1, padx=5, sticky="w")

        # Daily Quest
        self.dailyquest_var = tk.BooleanVar(value=False)
        self.dailyquest_checkbox = tk.Checkbutton(
            self.selection_frame, text="Daily Quest", variable=self.dailyquest_var
        )
        self.dailyquest_checkbox.grid(row=1, column=2, padx=5, sticky="w")
        self.dailyquest_checkbox.config(state="disabled")

        # Bonus-Map
        self.bm_var = tk.BooleanVar(value=False)
        self.bm_checkbox = tk.Checkbutton(
            self.selection_frame, text="Bonus-Map", variable=self.bm_var, command=self.toggle_bm
        )
        self.bm_checkbox.grid(row=1, column=3, padx=5, sticky="w")


        # Gegnerbild in der Mitte
        self.image_frame = tk.Frame(root)
        self.image_frame.pack(pady=10)

        self.image_label = tk.Label(self.image_frame)
        self.image_label.pack()

        # Status-Label direkt unter dem Bild
        self.status_var = tk.StringVar(value="Debugging: ")
        self.status_label = tk.Label(self.image_frame, textvariable=self.status_var, font=("Arial", 10))
        self.status_label.pack(pady=3)
        self.status_var.set("Debugging: Erwarte Anweisung!")

        # Chestcounter unter Debugging
        self.chestcounter = 0  # Integer-Variable für den Zähler
        self.chestcounter_label = tk.Label(
            self.image_frame,
            text=f"Chests collected / NPCs killed: {self.chestcounter}",
            font=("Arial", 10)
        )
        self.chestcounter_label.pack(pady=1)

        # Captchacounter unter Chestcounter
        self.captchacounter = 0  # Integer-Variable für den Zähler
        self.captchacounter_label = tk.Label(
            self.image_frame,
            text=f"Captchas ausgelöst: {self.captchacounter}",
            font=("Arial", 10)
        )
        self.captchacounter_label.pack(pady=3)

        # Button-Leiste unten
        button_frame = tk.Frame(root)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

        # Grid-Konfiguration: 3 Spalten – links (leer), mitte (Buttons), rechts (Settings)
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=0)
        button_frame.columnconfigure(2, weight=1)

        # Zentrierte Button-Gruppe in Spalte 1
        center_buttons = tk.Frame(button_frame)
        center_buttons.grid(row=0, column=1)

        tk.Button(center_buttons, text="Start", width=10, command=self.start_bot).pack(side=tk.LEFT, padx=5)
        tk.Button(center_buttons, text="Stop", width=10, command=self.stop_bot).pack(side=tk.LEFT, padx=5)
        tk.Button(center_buttons, text="Beenden", width=10, command=self.quit_app).pack(side=tk.LEFT, padx=5)

        # Settings-Button ganz rechts (Spalte 2)
        settings_button = tk.Button(button_frame, text="⚙", command=self.open_settings, width=3)
        settings_button.grid(row=0, column=2, sticky="e", padx=10)

        # Info-Button ganz links (Spalte 2)
        info_button = tk.Button(button_frame, text="ℹ", command=self.open_info, width=3)
        info_button.grid(row=0, column=0, sticky="w", padx=10)
 

        # Gegnerliste laden
        self.load_opponent_list()

        # Einstellungen in dem Settings Tab
        self.restart = tk.BooleanVar(value=True)
        self.schwarzpulver = tk.BooleanVar(value=False)
        self.panzerplatten = tk.BooleanVar(value=False)
        self.aggressiveattack = tk.BooleanVar(value=False)
        self.aggressiverepair = tk.BooleanVar(value=False)
        self.rockets = tk.BooleanVar(value=False)
        self.balistics = tk.BooleanVar(value=False)
        self.starting_point_var = tk.StringVar(value="TopLeft")
        self.repair_percentage = tk.IntVar(value=30)
        self.unlimitedbm = tk.BooleanVar(value=False)

    def open_info(self):
        info_window = tk.Toplevel(self.root)
        info_window.title("Information")
        info_window.geometry("320x280")
        info_window.resizable(False, False)
        info_window.attributes("-topmost", True)
        info_window.grab_set()
        info_window.focus_set()

        tk.Label(info_window, text="Tested Maps:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(15, 5))

        items = ["2", "5", "7", "11", "12"]
        bullet_items = [f"• {item}" for item in items]

        frame = tk.Frame(info_window)
        frame.pack(anchor="w", padx=10)

        # 2 Zeilen, 2 Spalten
        for i, text in enumerate(bullet_items):
            row = i // 3
            col = i % 3
            tk.Label(frame, text=text, justify="left").grid(row=row, column=col, sticky="w", padx=10)

        textblock = (
            "This bot has been tested on the maps listed above. "
            "Functionality on other maps cannot be guaranteed. "
            "Use the bot at your own risk."
        )
        
        textblock2 = (
            "Please start the Bonus-Map Bot from Tortuga Map. "
            "When the function ''unlimited Bonus-Maps'' is active the bot will go trough ALL available pearls or bonus map parts. "
        )

        tk.Label(info_window, text=textblock, wraplength=300, justify="left").pack(anchor="w", padx=10, pady=(10, 10))
        
        tk.Label(info_window, text="Bonus-Map Bot:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(0, 0))
        
        tk.Label(info_window, text=textblock2, wraplength=300, justify="left").pack(anchor="w", padx=10, pady=(0, 0))

        tk.Button(info_window, text="Close", command=info_window.destroy).pack(pady=5)

        # Optional: Fenster zentrieren über dem Hauptfenster
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        info_window.geometry(f"+{x + 50}+{y + 50}")

    def open_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Einstellungen")
        settings_window.geometry("250x480")
        settings_window.resizable(False, False)
        
        settings_window.attributes("-topmost", True)
        settings_window.update()
        
        settings_window.grab_set()
        settings_window.focus_set()


        # Optional: Fenster zentrieren über dem Hauptfenster
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        settings_window.geometry(f"+{x + 50}+{y + 50}")
        
        # Titel Startingpoint
        tk.Label(settings_window, text="Startingpoint:").pack(anchor="w", padx=12, pady=(10, 2))

        # Combobox
        starting_point_combobox = ttk.Combobox(
            settings_window,
            textvariable=self.starting_point_var,
            values=["TopLeft", "TopRight", "BottomRight", "BottomLeft"],
            state="readonly"
        )
        starting_point_combobox.pack(anchor="w", padx=15, pady=(0, 10))

        tk.Checkbutton(settings_window, text="Restart game when Captcha fails", variable=self.restart).pack(anchor="w", padx=10, pady=2)

        
        # Separator
        ttk.Separator(settings_window, orient="horizontal").pack(fill="x", padx=10, pady=(5, 5))

        # Titel Ship Settings
        tk.Label(settings_window, text="Ship Settings:").pack(anchor="w", padx=12, pady=(10, 2))


        # Fünf eigenständige Checkboxen mit individuellen Variablen s.h. init für Checkboxcreation
        tk.Checkbutton(settings_window, text="Schwarzpulver", variable=self.schwarzpulver).pack(anchor="w", padx=10, pady=2)
        tk.Checkbutton(settings_window, text="Panzerplatten", variable=self.panzerplatten).pack(anchor="w", padx=10, pady=2)
        tk.Checkbutton(settings_window, text="aggressive Attack", variable=self.aggressiveattack).pack(anchor="w", padx=10, pady=2)
        tk.Checkbutton(settings_window, text="Repair while shooting", variable=self.aggressiverepair).pack(anchor="w", padx=10, pady=2)
        self.rockets_check = tk.Checkbutton(
            settings_window, text="Rockets", variable=self.rockets, command=self.toggle_rocket_balistics
        )
        self.rockets_check.pack(anchor="w", padx=10, pady=2)

        self.balistics_check = tk.Checkbutton(
            settings_window, text="Balistic Rockets", variable=self.balistics, command=self.toggle_rocket_balistics
        )
        self.balistics_check.pack(anchor="w", padx=10, pady=2)

        # Separator für visuelle Trennung
        ttk.Separator(settings_window, orient="horizontal").pack(fill="x", padx=10, pady=(10, 5))

        # Repair Percentage Titel
        tk.Label(settings_window, text="Repair Percentage (on BM):").pack(anchor="w", padx=12, pady=(5, 2))

        # Repair Percentage Scale (Slider von 10 bis 90), Standardwert: 25%
        tk.Scale(
            settings_window,
            from_=10,
            to=80,
            orient="horizontal",
            variable=self.repair_percentage,
            length=150,
            resolution=1
        ).pack(anchor="w", padx=12, pady=(0, 10))

        tk.Checkbutton(settings_window, text="unlimited Bonus-Maps", variable=self.unlimitedbm).pack(anchor="w", padx=10, pady=2)

        tk.Button(settings_window, text="Close", command=settings_window.destroy).pack(pady=5)
        self.toggle_rocket_balistics()

    def toggle_rocket_balistics(self):
        if self.rockets.get():
            self.balistics_check.config(state="disabled")
        else:
            self.balistics_check.config(state="normal")

        if self.balistics.get():
            self.rockets_check.config(state="disabled")
        else:
            self.rockets_check.config(state="normal")

    def toggle_bm(self):
        if self.bm_var.get():
            # BM aktiviert: Gegnerauswahl auf BM-Werte setzen
            self.opponent_selector['values'] = ("Magician", "Port Royal")
            self.opponent_var.set("Magician")  # Standardwert setzen
            self.dwarfhunt_checkbox.config(state="disabled")
            self.chesthunt_checkbox.config(state="disabled")

            # BM Bild laden
            bmbutton = os.path.join(GEGNER_PREVIEW, "Magician.png")
            self.load_image_by_path(bmbutton)
        else:
            # BM deaktiviert: Gegnerauswahl auf Standardwerte zurücksetzen
            self.load_opponent_list()  # Hier die Standardwerte einsetzen
            self.opponent_var.set("Baron")
            self.dwarfhunt_checkbox.config(state="normal")
            self.chesthunt_checkbox.config(state="normal")
            self.load_image("Baron")


    def toggle_chesthunt(self):
        if self.chesthunt_var.get():
            # Chesthunt aktiviert: Gegnerauswahl deaktivieren, Gegner auf "Chest" setzen
            self.opponent_selector.config(state="disabled")
            self.opponent_var.set("Chest")
            self.dwarfhunt_checkbox.config(state="disabled")
            self.bm_checkbox.config(state="disabled")
            # Chest Bild laden
            chest_bild = os.path.join(GEGNER_PREVIEW, "Chest.png")
            self.load_image_by_path(chest_bild)
        else:
            # Chesthunt deaktiviert: Gegnerauswahl aktivieren
            self.opponent_selector.config(state="readonly")
            self.dwarfhunt_checkbox.config(state="normal")
            self.bm_checkbox.config(state="normal")
            self.opponent_var.set("Baron")
            self.load_image("Baron")
        
    def toggle_dwarfhunt(self):
        if self.dwarfhunt_var.get():
            # Dwarfhunt aktiviert: Gegnerauswahl deaktivieren, Gegner auf "Dwarf" setzen
            self.opponent_selector.config(state="disabled")
            self.opponent_var.set("Dwarf + Bloody Junior")
            self.chesthunt_checkbox.config(state="disabled")
            self.bm_checkbox.config(state="disabled")
            # Dwarf Bild laden
            dwarf_bild = os.path.join(GEGNER_PREVIEW, "DwarfBloody.png")
            self.load_image_by_path(dwarf_bild)
        else:
            # Dwarfhunt deaktiviert: Gegnerauswahl aktivieren
            self.opponent_selector.config(state="readonly")
            self.chesthunt_checkbox.config(state="normal")
            self.bm_checkbox.config(state="normal")
            self.opponent_var.set("Baron")
            self.load_image("Baron")

    def load_image_by_path(self, pfad):
        try:
            image = Image.open(pfad)
            image = image.resize((100, 100), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(image)
            self.image_label.config(image=self.photo)
        except Exception as e:
            print(f"Fehler beim Laden von {pfad}: {e}")

    def sammel_truhe(self, bildpfad=None, position=None, return_to=None):
        if not self.running:  
            print("Suche abgebrochen.")
            return
        pyautogui.press("a")
        pyautogui.press("d")
        time.sleep(0.1)
        ziel_x = position.left + position.width // 2
        ziel_y = position.top + position.height // 2
        pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
        pyautogui.click()
        time.sleep(0.2)
        pyautogui.click()
        time.sleep(0.2)
        pyautogui.press("space")
        print(f"Chest-Klick in der Mitte bei ({ziel_x}, {ziel_y})")
        time.sleep(5.5)
        self.chestcounter += 1
        self.chestcounter_label.config(text=f"Chests collected: {self.chestcounter}")
        print("Chest wurde eingesammelt, aber ist da noch eine?")
        position = None
        gefunden = False
        bildpfade = [
            os.path.join(GEGNER_PREVIEW, "Chest2.png"),
            os.path.join(GEGNER_PREVIEW, "Chest3.png"),
            os.path.join(GEGNER_PREVIEW, "Chest4.png"),
            os.path.join(GEGNER_PREVIEW, "Chest5.png")
        ]
        for pfad in bildpfade:
            try:
                position = locateOnScreen(pfad, confidence=0.82)
                if position:
                    print(f"Chest bei ({position}) mit der Datei ({pfad}) ")
                    self.status_var.set("Debugging: Chest gefunden, fahre los...")
                    gefunden = True
                    self.sammel_truhe(position=position, return_to=return_to)
            except Exception as e:
                continue
                self.captcha_check()
        if not gefunden:
            print("Keine Chest mehr gefunden. Zurück zur ursprünglichen Koordinate...")
            if callable(return_to):
                return_to()

                

    def fahre_zum_gegner(self, bildpfad=None, position=None, return_to=None):
        if not self.running:  
            print("Suche abgebrochen.")
            return
            
        if position:
            print("Gefunden bei:", position)
            # Anti center jiggle
            pyautogui.press("a")
            pyautogui.press("d")
            time.sleep(0.1)
            try:
                cposition = locateOnScreen(bildpfad, confidence=0.82)
                if cposition:
                    gegner_x = cposition.left + cposition.width // 2
                    gegner_y = cposition.top + cposition.height // 2 - 30
                    pyautogui.moveTo(gegner_x, gegner_y, duration=0.1)
                    pyautogui.click()                
            except:
                gegner_x = position.left + position.width // 2
                gegner_y = position.top + position.height // 2 - 30
                pyautogui.moveTo(gegner_x, gegner_y, duration=0.1)
                pyautogui.click()
            
        print("Gegner wurde markiert.")
        # 2sec click 240 Pixel entfernt vom Gegner auf der Linie zum Spieler
        player_x = 960
        player_y = 530
        richtung_x = gegner_x - player_x
        richtung_y = gegner_y - player_y
        länge = math.sqrt(richtung_x**2 + richtung_y**2)
        norm_x = richtung_x / länge
        norm_y = richtung_y / länge
        klick_x = gegner_x - norm_x * 240
        klick_y = gegner_y - norm_y * 240
        gegner = self.opponent_var.get()
        if "(M)" in gegner:
            klick_x = gegner_x - norm_x * 120
            klick_y = gegner_y - norm_y * 120
                
        pyautogui.moveTo(klick_x, klick_y, duration=0.2)
        pyautogui.keyDown('ctrl')
        pyautogui.click()
        pyautogui.keyUp('ctrl')
        if self.aggressiveattack.get():
            pyautogui.press("e")
            self.raketen()
            time.sleep(1)
            pyautogui.press("e")
            time.sleep(1)
            pyautogui.press("e")
            self.raketen()
            time.sleep(1)
            pyautogui.press("e")
            time.sleep(1)
        else:
            time.sleep(4)
        print("225 Pixel von Gegner entfernt geklickt.")
        Rect = namedtuple("Rect", "left top width height")
        ausnahme = False
        try:
            schussBereit = locateOnScreen("ressources/schussBereit.png", confidence=0.80)
        except:
            schussBereit = Rect(left=685, top=1011, width=40, height=40)
            ausnahme = True
            print("Das Schuss Symbol wurde nicht gefunden ich nehme manuelle Daten zur Hand.")
            pass
        if schussBereit or ausnahme:
            ziel_x = schussBereit.left + schussBereit.width // 2
            ziel_y = schussBereit.top + schussBereit.height // 2
            r, g, b = pyautogui.pixel(int(ziel_x), int(ziel_y))
            brightness = 0.299 * r + 0.587 * g + 0.114 * b
            reichweite = 255
            if "(M)" in gegner:
                reichweite = 110
            versuch = 8
            while brightness > 45 and versuch > 0:
                if self.aggressiveattack.get():
                    pyautogui.press("e")
                print("Erhöhe Reichweite bis maximale Distanz erreicht.")
                klick_x = gegner_x - norm_x * reichweite
                klick_y = gegner_y - norm_y * reichweite
                pyautogui.moveTo(klick_x, klick_y, duration=0.1)
                pyautogui.keyDown('ctrl')
                pyautogui.click()
                pyautogui.keyUp('ctrl')
                time.sleep(0.4)                
                r, g, b = pyautogui.pixel(int(ziel_x), int(ziel_y))
                brightness = 0.299 * r + 0.587 * g + 0.114 * b
                versuch -= 1
                print(f"{versuch}")
                if not self.running:  
                    print("Suche abgebrochen.")
                    return
                if brightness > 45:
                    reichweite += 15
            versuch2 = 4       
            while brightness < 45 and versuch2 > 0:
                print("Gegner zu weit weg!")
                reichweite -= 20
                klick_x = gegner_x - norm_x * reichweite
                klick_y = gegner_y - norm_y * reichweite
                pyautogui.moveTo(klick_x, klick_y, duration=0.1)
                pyautogui.keyDown('ctrl')
                pyautogui.click()
                pyautogui.keyUp('ctrl')
                time.sleep(0.4)
                versuch2 -= 1
                print(f"{versuch2}")
                if self.aggressiveattack.get():
                    pyautogui.press("e")
                r, g, b = pyautogui.pixel(int(ziel_x), int(ziel_y))
                brightness = 0.299 * r + 0.587 * g + 0.114 * b
                #klick safety
                if klick_x < 100 or klick_x > 1650 or klick_y < 100 or klick_y > 880:
                    print("Maus außerhalb des Bereiches breche ab.")
                    break
                
            print("Reichweite müsste so passen.")
            pyautogui.press("e")
                
            if self.aggressiverepair.get():
                r, g, b = pyautogui.pixel(int(804), int(1027))
                brightness = 0.299 * r + 0.587 * g + 0.114 * b
                if brightness >= 70:
                    pyautogui.press("r")
                    print("Starte reparatur...")
                    
            check = 0
            check_failed = False
            while self.running:
                self.root.update()
                if not self.running:  
                    print("Angriff abgebrochen.")
                    return
                
                r, g, b = pyautogui.pixel(int(ziel_x), int(ziel_y))
                brightness = 0.299 * r + 0.587 * g + 0.114 * b

                if brightness <= 45:
                    break

                print("Erwarte Tötung...")
                if self.aggressiverepair.get():
                    r, g, b = pyautogui.pixel(int(804), int(1027))
                    brightness = 0.299 * r + 0.587 * g + 0.114 * b
                    if brightness >= 70:
                        pyautogui.press("r")
                    
                self.raketen()
                time.sleep(1)
                self.captcha_check()
                check += 1            
                if check >= 10:
                    while True:
                        r, g, b = pyautogui.pixel(int(681), int(1052))
                        brightness = 0.299 * r + 0.587 * g + 0.114 * b
                        time.sleep(0.5)
                        r, g, b = pyautogui.pixel(int(681), int(1052))
                        brightness2 = 0.299 * r + 0.587 * g + 0.114 * b

                        if brightness <= 10 or brightness2 <= 10:
                            print("NPC noch unter Beschuss.")
                            check = 0
                            break
                        else:
                            check_failed = True
                            break

                if check_failed:
                    break

            print("Gegner wurde getötet.")
            r, g, b = pyautogui.pixel(int(804), int(1027))
            brightness = 0.299 * r + 0.587 * g + 0.114 * b
            if brightness >= 70:
                pyautogui.press("r")
                print("Starte reparatur...")
            
            try:
                dead_pfad = os.path.join("ressources", "dead.png")
                position = locateOnScreen(dead_pfad, confidence=0.92)
                if position:
                    print("Sie sind gestorben.")
                    self.status_var.set("Debugging: Sie sind gestorben.")
                    ziel_x = position.left + position.width // 2
                    ziel_y = position.top + position.height // 2
                    pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
                    pyautogui.click()
                    time.sleep(2)
                    self.repair()
                    self.fahre_zur_koordinate1()
                    return
            except:
                pass
            self.chestcounter += 1
            self.chestcounter_label.config(text=f"NPCs killed: {self.chestcounter}")
            if callable(return_to):
                return_to()
        return

    def death_check_bm(self):
        try:
            dead_pfad = os.path.join("ressources", "dead.png")
            position = locateOnScreen(dead_pfad, confidence=0.92)
            if position:
                print("Sie sind gestorben.")
                self.status_var.set("Debugging: Sie sind gestorben.")
                ziel_x = position.left + position.width // 2
                ziel_y = position.top + position.height // 2
                pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
                pyautogui.click()
                time.sleep(2)
                self.repair()
                
                hp_percent = self.check_hp() 
                while hp_percent < 50:
                    self.repair()
                    hp_percent = self.check_hp()
                    time.sleep(5)
                    
                self.run_bm_logic()
                return
        except:
                pass

    def dwarfhunt(self, return_to=None):
        if not self.running:  
            print("Suche abgebrochen.")
            return
        
        left, top, right, bottom = 1740, 93, 1875, 227
        screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
        target_rgb = (244, 183, 0)
        width, height = screenshot.size
        gefunden = False

            
        for x in range(width):
            for y in range(height):
                if screenshot.getpixel((x, y)) == target_rgb:
                    # Umrechnen auf globale Koordinaten
                    screen_x = left + x
                    screen_y = top + y
                    print(f"Bloody Junior gefunden bei: {screen_x}, {screen_y}")
                    gefunden = True
                    break
            if gefunden:
                break

        print(f"Der Zugriffsstatus: {self.zugriff}")
        if not self.zugriff:
            self.zugriff_counter += 1
            print(f"Der Zugriffscounter: {self.zugriff_counter}")
            if self.zugriff_counter >= 8:
                self.zugriff = True
                self.zugriff_counter = 0
                    
        if self.zugriff:
            pyautogui.moveTo(screen_x, screen_y, duration=0.2)
            pyautogui.mouseDown(button='left')
            time.sleep(0.5)
            pyautogui.mouseUp(button='left')
            time.sleep(0.1)
            ziel_x = 960
            ziel_y = 540
            pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
            pyautogui.keyDown('ctrl')
            pyautogui.click()
            pyautogui.keyUp('ctrl')
            time.sleep(0.1)
            ziel_x = 975
            ziel_y = 555
            pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
            pyautogui.keyDown('ctrl')
            pyautogui.click()
            pyautogui.keyUp('ctrl')
        
        versuch = 45
        gefunden = False

        while versuch > 0 and not gefunden and self.running and self.zugriff:
            self.root.update()
            if not self.running:  
                print("Fahrt zu Bloody abgebrochen.")
                return
            
            try:
                print(f"Versuch {45 - versuch + 1} von 45")  # Debugging-Ausgabe
                bloody_pfad = os.path.join("ressources", "gegner", "Bloody Junior.png")
                position = locateOnScreen(bloody_pfad, confidence=0.60)

                if position:
                    print("Bloody Junior entdeckt.")
                    self.status_var.set("Debugging: Kämpfe gegen Bloody Junior...")
                    gefunden = True
                    self.fahre_zum_gegner(position=position, return_to=return_to)
                    return

            except Exception as e:
                print(f"Fehler bei Versuch {45 - versuch + 1}: {e}")  # Debugging-Ausgabe
                versuch -= 1
                if versuch == 40:
                    pyautogui.moveTo(1257, 530, duration=0.2)
                    pyautogui.keyDown('ctrl')
                    pyautogui.click()
                    pyautogui.keyUp('ctrl')
                    time.sleep(3)
                if versuch == 43:
                    pyautogui.moveTo(633, 530, duration=0.2)
                    pyautogui.keyDown('ctrl')
                    pyautogui.click()
                    pyautogui.keyUp('ctrl')
                    time.sleep(3)
                time.sleep(1)
                self.captcha_check()
                if versuch == 0:
                    print("Maximale Anzahl an Versuchen erreicht und Bloody nicht gefunden.")
                    self.zugriff = False
                    break          
             
        print("Mache mit Dwarfs weiter...")
        self.captcha_check()

        try:
            dwarf_pfad = os.path.join("ressources", "gegner", "Dwarf.png")
            position = locateOnScreen(dwarf_pfad, confidence=0.60)
            if position:
                print("Dwarf entdeckt.")
                self.status_var.set("Debugging: Kämpfe gegen Dwarf...")
                self.fahre_zum_gegner(position=position, return_to=return_to)
                return
        except:
            pass

        try:
            koordinaten_pfad = os.path.join("ressources", "kords1bj.png")
            position = locateOnScreen(koordinaten_pfad, confidence=0.90)
            if position:
                print("Koordinaten 1 (11/AI) erreicht.")
                self.status_var.set("Debugging: Koordinaten erreicht, fahre zu Kord 2.")
                self.fahre_zur_koordinate2()
                return
        except:
            pass

        try:
            koordinaten_pfad = os.path.join("ressources", "kords2bj.png")
            position = locateOnScreen(koordinaten_pfad, confidence=0.90)
            if position:
                print("Koordinaten 2 (42/AJ) erreicht.")
                self.status_var.set("Debugging: Koordinaten erreicht, fahre zu Kord 3.")
                self.fahre_zur_koordinate3()
                return
        except:
            pass

        try:
            koordinaten_pfad = os.path.join("ressources", "kords3bj.png")
            position = locateOnScreen(koordinaten_pfad, confidence=0.90)
            if position:
                print("Koordinaten 3 (42/BY) erreicht.")
                self.status_var.set("Debugging: Koordinaten erreicht, fahre zu Kord 4.")
                self.fahre_zur_koordinate4()
                return
        except:
            pass

        try:
            koordinaten_pfad = os.path.join("ressources", "kords4bj.png")
            position = locateOnScreen(koordinaten_pfad, confidence=0.90)
            if position:
                print("Koordinaten 4 (13/BS) erreicht.")
                self.status_var.set("Debugging: Koordinaten erreicht, fahre zu Kord 1.")
                self.fahre_zur_koordinate1()
                return
        except:
            pass

        try:
            dead_pfad = os.path.join("ressources", "dead.png")
            position = locateOnScreen(dead_pfad, confidence=0.92)
            if position:
                print("Sie sind gestorben.")
                self.status_var.set("Debugging: Sie sind gestorben.")
                ziel_x = position.left + position.width // 2
                ziel_y = position.top + position.height // 2
                pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
                pyautogui.click()
                time.sleep(2)
                self.repair()
                self.fahre_zur_koordinate1()
                return
        except:
            pass
            
        # Falls keiner gefunden wurde – erneut versuchen
        print("Dwarf nicht gefunden, versuche es erneut...")
        if not self.zugriff:
            self.fahre_zur_koordinate1()
        self.root.after(1000, lambda: self.dwarfhunt(return_to=return_to))

      

    def suche_bis_gefunden(self, bildpfad, return_to=None):
        if not self.running:  
            print("Suche abgebrochen.")
            return
        self.status_var.set("Debugging: Begebe mich auf die Suche")
        
        bildpfade = [bildpfad]  # Standardfall: nur ein Bild

        # Falls Chesthunt aktiv ist, beide Varianten prüfen
        if self.chesthunt_var.get():
            bildpfade = [
                os.path.join(GEGNER_PREVIEW, "Chest2.png"),
                os.path.join(GEGNER_PREVIEW, "Chest3.png"),
                os.path.join(GEGNER_PREVIEW, "Chest4.png"),
                os.path.join(GEGNER_PREVIEW, "Chest5.png")
            ]

        

        ##############################################################
        ### Hier muss if abfrage für Gegnerauswahl wenn Checkboxen ###
        ##############################################################


        # Versuche beide Bilder der Reihe nach zu finden
        for pfad in bildpfade:
            try:
                position = locateOnScreen(pfad, confidence=0.82)
                if position:
                    print(f"Gegner bei ({position}) mit der Datei ({pfad}) ")
                    self.status_var.set("Debugging: Gegner gefunden, fahre los...")
                    if self.chesthunt_var.get():
                        print("Suche bis gefunden in Chesthunt also Sammeln mit Truhensammler.")
                        self.sammel_truhe(position=position, return_to=return_to)
                        return
                    self.fahre_zum_gegner(bildpfad=bildpfad, position=position, return_to=return_to)
                    return  # Suche erfolgreich, abbrechen
            except ImageNotFoundException:
                continue  # Einfach nächsten Versuch machen
            except Exception as e:
                print(f"Anderer Fehler beim Bildvergleich: {e}")
                self.status_var.set("Debugging: Fehler beim Bildvergleich")
                return
        self.captcha_check()
        
        methodenname = return_to.__name__
        if methodenname == ("fahre_zur_koordinate1"):
            try:
                koordinaten_pfad = os.path.join("ressources", "kords1.png")
                position = locateOnScreen(koordinaten_pfad, confidence=0.90)
                if position:
                    print("Koordinaten 1 (11/AG) erreicht.")
                    self.status_var.set("Debugging: Koordinaten erreicht, fahre zu Kord 2.")
                    self.fahre_zur_koordinate2()
                    return
            except:
                pass
            
        if methodenname == ("fahre_zur_koordinate2"):
            try:
                koordinaten_pfad = os.path.join("ressources", "kords2.png")
                position = locateOnScreen(koordinaten_pfad, confidence=0.95)
                if position:
                    print("Koordinaten 2 (42/AJ) erreicht.")
                    self.status_var.set("Debugging: Koordinaten erreicht, fahre zu Kord 3.")
                    self.fahre_zur_koordinate3()
                    return
            except:
                pass
            
        if methodenname == ("fahre_zur_koordinate3"):
            try:
                koordinaten_pfad = os.path.join("ressources", "kords3.png")
                position = locateOnScreen(koordinaten_pfad, confidence=0.95)
                if position:
                    print("Koordinaten 3 (42/BY) erreicht.")
                    self.status_var.set("Debugging: Koordinaten erreicht, fahre zu Kord 4.")
                    self.fahre_zur_koordinate4()
                    return
            except:
                pass

        if methodenname == ("fahre_zur_koordinate4"):
            try:
                koordinaten_pfad = os.path.join("ressources", "kords4.png")
                position = locateOnScreen(koordinaten_pfad, confidence=0.95)
                if position:
                    print("Koordinaten 4 (13/BS) erreicht.")
                    self.status_var.set("Debugging: Koordinaten erreicht, fahre zu Kord 1.")
                    self.fahre_zur_koordinate1()
                    return
            except:
                pass

        try:
            dead_pfad = os.path.join("ressources", "dead.png")
            position = locateOnScreen(dead_pfad, confidence=0.92)
            if position:
                print("Sie sind gestorben.")
                self.status_var.set("Debugging: Sie sind gestorben.")
                ziel_x = position.left + position.width // 2
                ziel_y = position.top + position.height // 2
                pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
                pyautogui.click()
                time.sleep(2)
                self.repair()
                self.fahre_zur_koordinate1()
                return
        except:
            pass
            
        print("Noch nicht gefunden, versuche es erneut...")
        if self.captchafail:
            self.captchafail = False
            self.fahre_zur_koordinate1()
        else:
            self.root.after(1000, lambda: self.suche_bis_gefunden(bildpfad, return_to=return_to))


    def repair(self):
        r, g, b = pyautogui.pixel(int(804), int(1027))
        brightness = 0.299 * r + 0.587 * g + 0.114 * b
        if brightness >= 70:
            pyautogui.press("r")
        
    def preprocess_image(self, image):
        print("Start der Bildvorverarbeitung...")
        
        # Gamma-Korrektur
        #image = image.point(lambda p: 255 if p > 130 else 0)
        #print("Gamma-Korrektur angewendet.")
        
        # Kontrast erhöhen
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(15)
        print("Kontrast wurde erhöht.")

        image = ImageOps.expand(image, border=10, fill=255)
        print("Rand wurde ergänzt.")
                
        # Skalieren
        image = image.resize((image.width * 2, image.height * 2), Image.BILINEAR)
        print("Bild wurde skaliert.")

        # Graustufen
        image = image.convert('L')
        print("Bild in Graustufen konvertiert.")
        
        return image

    def wobinich(self):
        screenshot_path = os.path.join("ressources", "wobinich.png")
        screenshot_region = (1743, 66, 132, 15)
        screenshot = pyautogui.screenshot(region=screenshot_region)
        screenshot.save(screenshot_path)
        
        text = pytesseract.image_to_string(screenshot, config='--psm 7 --oem 3')
        locationkords = text.strip()
        print(locationkords)
        match = re.search(r'X.*?(\d{2}).*?Y.*?([A-Za-z]{2})', locationkords)

        if match:
            # Extrahiere die Koordinaten
            x_coord = match.group(1)
            y_coord = match.group(2)

            # Erstelle die Variable location im gewünschten Format
            location = f"X:{x_coord} Y:{y_coord}"
        else:
            location = "Keine Koordinaten gefunden"

        print(f"Ich bin hier: {location}")
        return location


    def captcha_check(self):
        try:
            position = locateOnScreen("ressources/captcha.png", confidence=0.90)
            if position:
                print("Captcha wurde ausgelöst.")
                self.status_var.set("Debugging: Captcha wurde ausgelöst.")
                self.captchacounter += 1
                self.captchacounter_label.config(text=f"Captchas ausgelöst: {self.captchacounter}")

                # Konvertiere die NumPy-Typen in native Python-Typen
                position = (int(position.left), int(position.top), int(position.width), int(position.height))
                print(f"Position des Captchas: {position}")

                # Berechne die Position für den Screenshot
                screenshot_position = (position[0] + position[2] + 20, position[1] + 20)
                print(f"Position für den Screenshot: {screenshot_position}")

                screenshot_region = (screenshot_position[0], screenshot_position[1], 88, 33)
                print(f"Region für den Screenshot: {screenshot_region}")

                # Erstelle den "test"-Ordner, falls er nicht existiert
                if not os.path.exists("captcha"):
                    os.makedirs("captcha")
                    print('Ordner "test" wurde erstellt.')

                # Feste Dateinamen für die Screenshots
                screenshot_path = os.path.join("captcha", "captcha_screenshot.png")
                processed_image_path = os.path.join("captcha", "captcha_screenshot_processed.png")

                # Mache den Screenshot und speichere ihn
                screenshot = pyautogui.screenshot(region=screenshot_region)
                screenshot.save(screenshot_path)
                print(f"Screenshot erfolgreich gespeichert.")

                # Vorverarbeite das Bild
                processed_image = self.preprocess_image(screenshot)
                processed_image.save(processed_image_path)
                print("Vorverarbeitung abgeschlossen.")

                # Verwende pytesseract, um den Text aus dem vorverarbeiteten Bild zu extrahieren
                text = pytesseract.image_to_string(processed_image, config='--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789')
                captcha_text = text.strip()
                print(f"Erkanntes Captcha: {captcha_text}")
                if len(captcha_text) == 4 and captcha_text.isdigit():
                    print("Der Text ist eine gültige 4-stellige Zahl:", captcha_text)
                else:
                    print("Der Text ist keine gültige 4-stellige Zahl.")
                    pyautogui.hotkey('alt', 'f4')
                    print("Aus Sicherheitsgründen wird das Spiel geschlossen und der Bot beendet.")
                    print("Beendet am:", datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
                    if self.restart.get():
                        print("Versuche das Spiel neuzustarten.")
                        if platform.system() == "Linux":
                            print("Platform Linux erkannt. Gamestart nicht möglich.")
                            self.running = False
                            return         
                        else:
                            os.startfile(r'C:\Games\Gamepatron\Battle of Sea\Game\launcher.exe')                        
                        print("Warte 3 Sekunden bis das Spiel da ist.")
                        time.sleep(3)
                        pyautogui.keyDown('enter')
                        time.sleep(0.2) 
                        pyautogui.keyUp('enter')
                        time.sleep(2)
                        r, g, b = pyautogui.pixel(int(1235), int(1014))
                        brightness = 0.299 * r + 0.587 * g + 0.114 * b
                        while brightness < 55:
                            time.sleep(1)
                            r, g, b = pyautogui.pixel(int(1235), int(1014))
                            brightness = 0.299 * r + 0.587 * g + 0.114 * b
                        
                        self.captchafail = True
                        self.schwarz_platten_check()
                        return
                    else:
                        self.running = False
                        return                   
                    

                # Berechne die Position für den Klick
                click_x = screenshot_region[0] - 135  # 135 Pixel nach links
                click_y = screenshot_region[1] + screenshot_region[3] + 25  # 25 Pixel unter dem Screenshot
                print(f"Klickposition: ({click_x}, {click_y})")

                # Führe den Klick aus
                pyautogui.click(click_x, click_y)
                print("Klick wurde ausgeführt.")

                # Gib den erkannten Captcha-Text ein
                pyautogui.write(captcha_text)
                pyautogui.press("enter")
                print(f"Captcha-Text '{captcha_text}' wurde eingegeben.")
                
        except:
            pass


    def fahre_zur_koordinate1(self, beschuss=None):
        if not self.running:  
            print("Suche abgebrochen.")
            return
    ###Mechanismus zur Koordinateneingabe 1
        try:
            koordinaten_pfad = os.path.join("ressources", "kordsystem.png")
            position = locateOnScreen(koordinaten_pfad, confidence=0.8)
            if position:
                print("Kordsystem gefunden.")
                self.status_var.set("Debugging: Gehe nach X:11 Y:AG")
                ziel_x = position.left + position.width // 2
                ziel_y = position.top + position.height // 2
                pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
                pyautogui.click()
                time.sleep(0.1)
                pyautogui.press("1")
                time.sleep(0.1)
                pyautogui.press("1")
                time.sleep(0.1)
                pyautogui.press("tab")
                time.sleep(0.2)
                pyautogui.press("a")
                time.sleep(0.1)
                pyautogui.press("g")
                time.sleep(0.2)
                pyautogui.press("enter")
                print("Eingaben getätigt.")
                pyautogui.press("space")
                time.sleep(1.5)
                if self.bm_var.get() and beschuss == True:
                    print("Erweiterte Wartezeit aufgrund von Beschuss.")
                    time.sleep(8)
                    beschuss = False
        except:
            print("Koordinateneingabe nicht gefunden: kein VIP Mitglied.")
            print("Versuche ohne Koordinateneingabe zu bewegen.")
            self.status_var.set("Debugging: Versuche ohne Koordinateneingabe zu bewegen.")
            ziel_x = 1763
            ziel_y = 109
            pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
            pyautogui.mouseDown(button='left')
            time.sleep(0.5)
            pyautogui.mouseUp(button='left')
            ziel_x = 1000
            ziel_y = 481
            pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
            pyautogui.keyDown('ctrl')        
            pyautogui.mouseDown(button='left')
            time.sleep(0.1)
            pyautogui.mouseUp(button='left')
            pyautogui.keyUp('ctrl')
            pyautogui.press("space")
            time.sleep(1.5)
            if self.bm_var.get() and beschuss == True:
                print("Erweiterte Wartezeit aufgrund von Beschuss.")
                time.sleep(8)
                beschuss = False
            pass

        if not self.bm_var.get() and not self.dwarfhunt_var.get():           
            print("Koordinate 1 11/AG aufgenommen, starte wieder die Suche.")
            gegner = self.opponent_var.get()
            bildpfad = os.path.join(GEGNER_DIR, gegner + ".png")
            self.suche_bis_gefunden(bildpfad, return_to=self.fahre_zur_koordinate1)

        if self.dwarfhunt_var.get():
            self.captcha_check()
            r, g, b = pyautogui.pixel(int(804), int(1027))
            brightness = 0.299 * r + 0.587 * g + 0.114 * b
            if brightness >= 70:
                pyautogui.press("r")
            self.dwarfhunt(return_to=self.fahre_zur_koordinate1)

        if self.bm_var.get():
            self.captcha_check()
            self.death_check_bm()
            time.sleep(5)
            pyautogui.press("r")
            time.sleep(5)
            r, g, b = pyautogui.pixel(int(804), int(1027))
            brightness = 0.299 * r + 0.587 * g + 0.114 * b
            if brightness >= 70:
                pyautogui.press("r")
            while self.running:
                self.root.update()
                if not self.running:  
                    print("Reparatur abgebrochen.")
                    return
                self.captcha_check()
                self.death_check_bm()
                hp = self.check_hp()
                if hp > 85:
                    self.aktueller_startpunkt = 3
                    self.bmbot()
                    return
                time.sleep(3)
                hp2 = self.check_hp()
                print(f"Ist {hp} größer als {hp2}?")
                if hp > hp2:
                    print("Unter beschuss während dem reparieren.")
                    beschuss = True
                    self.fahre_zur_koordinate2(beschuss)

    def fahre_zur_koordinate2(self, beschuss=None):
        if not self.running:  
            print("Suche abgebrochen.")
            return
        ###Mechanismus zur Koordinateneingabe 2
        try:
            koordinaten_pfad = os.path.join("ressources", "kordsystem.png")
            position = locateOnScreen(koordinaten_pfad, confidence=0.8)
            if position:
                print("Kordsystem gefunden.")
                self.status_var.set("Debugging: Gehe nach X:42 Y:AJ")
                ziel_x = position.left + position.width // 2
                ziel_y = position.top + position.height // 2
                pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
                pyautogui.click()
                time.sleep(0.1)
                pyautogui.press("4")
                time.sleep(0.1)
                pyautogui.press("2")
                time.sleep(0.1)
                pyautogui.press("tab")
                time.sleep(0.2)
                pyautogui.press("a")
                time.sleep(0.1)
                pyautogui.press("j")
                time.sleep(0.2)
                pyautogui.press("enter")
                print("Eingaben getätigt.")
                pyautogui.press("space")
                time.sleep(1.5)
                if self.bm_var.get() and beschuss == True:
                    print("Erweiterte Wartezeit aufgrund von Beschuss.")
                    time.sleep(8)
                    beschuss = False
        except:
            print("Koordinateneingabe nicht gefunden: kein VIP Mitglied.")
            print("Versuche ohne Koordinateneingabe zu bewegen.")
            self.status_var.set("Debugging: Versuche ohne Koordinateneingabe zu bewegen.")
            ziel_x = 1855
            ziel_y = 109
            pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
            pyautogui.mouseDown(button='left')
            time.sleep(0.5)
            pyautogui.mouseUp(button='left')
            ziel_x = 1178
            ziel_y = 670
            pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
            pyautogui.keyDown('ctrl')        
            pyautogui.mouseDown(button='left')
            time.sleep(0.1)
            pyautogui.mouseUp(button='left')
            pyautogui.keyUp('ctrl')
            pyautogui.press("space")
            time.sleep(1.5)
            if self.bm_var.get() and beschuss == True:
                print("Erweiterte Wartezeit aufgrund von Beschuss.")
                time.sleep(8)
                beschuss = False
            pass

        if not self.bm_var.get() and not self.dwarfhunt_var.get():            
            print("Koordinate 2 42/AJ aufgenommen, starte wieder die Suche.")
            gegner = self.opponent_var.get()
            bildpfad = os.path.join(GEGNER_DIR, gegner + ".png")
            self.suche_bis_gefunden(bildpfad, return_to=self.fahre_zur_koordinate2)

        if self.dwarfhunt_var.get():
            self.captcha_check()
            pyautogui.press("r")
            self.dwarfhunt(return_to=self.fahre_zur_koordinate2)

        if self.bm_var.get():
            self.captcha_check()
            self.death_check_bm()
            time.sleep(5)
            pyautogui.press("r")
            time.sleep(5)
            r, g, b = pyautogui.pixel(int(804), int(1027))
            brightness = 0.299 * r + 0.587 * g + 0.114 * b
            if brightness >= 70:
                pyautogui.press("r")
            while self.running:
                self.root.update()
                if not self.running:  
                    print("Reparatur abgebrochen.")
                    return
                self.captcha_check()
                self.death_check_bm()
                hp = self.check_hp()
                if hp > 85:
                    self.aktueller_startpunkt = 4
                    self.bmbot()
                    return
                time.sleep(3)
                hp2 = self.check_hp()
                print(f"Ist {hp} größer als {hp2}?")
                if hp > hp2:
                    print("Unter beschuss während dem reparieren.")
                    beschuss = True
                    self.fahre_zur_koordinate3(beschuss)

    def fahre_zur_koordinate3(self, beschuss=None):
        if not self.running:  
            print("Suche abgebrochen.")
            return
    ###Mechanismus zur Koordinateneingabe 3
        try:
            koordinaten_pfad = os.path.join("ressources", "kordsystem.png")
            position = locateOnScreen(koordinaten_pfad, confidence=0.8)
            if position:
                print("Kordsystem gefunden.")
                self.status_var.set("Debugging: Gehe nach X:42 Y:BY")
                ziel_x = position.left + position.width // 2
                ziel_y = position.top + position.height // 2
                pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
                pyautogui.click()
                time.sleep(0.1)
                pyautogui.press("4")
                time.sleep(0.1)
                pyautogui.press("2")
                time.sleep(0.1)
                pyautogui.press("tab")
                time.sleep(0.2)
                pyautogui.press("b")
                time.sleep(0.1)
                pyautogui.press("y")
                time.sleep(0.2)
                pyautogui.press("enter")
                print("Eingaben getätigt.")
                pyautogui.press("space")
                time.sleep(1.5)
                if self.bm_var.get() and beschuss == True:
                    print("Erweiterte Wartezeit aufgrund von Beschuss.")
                    time.sleep(8)
                    beschuss = False
        except:
            print("Koordinateneingabe nicht gefunden: kein VIP Mitglied.")
            print("Versuche ohne Koordinateneingabe zu bewegen.")
            self.status_var.set("Debugging: Versuche ohne Koordinateneingabe zu bewegen.")
            ziel_x = 1855
            ziel_y = 208
            pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
            pyautogui.mouseDown(button='left')
            time.sleep(0.5)
            pyautogui.mouseUp(button='left')
            ziel_x = 1175
            ziel_y = 629
            pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
            pyautogui.keyDown('ctrl')        
            pyautogui.mouseDown(button='left')
            time.sleep(0.1)
            pyautogui.mouseUp(button='left')
            pyautogui.keyUp('ctrl')
            pyautogui.press("space")
            time.sleep(1.5)
            if self.bm_var.get() and beschuss == True:
                print("Erweiterte Wartezeit aufgrund von Beschuss.")
                time.sleep(8)
                beschuss = False
            pass
        
        if not self.bm_var.get() and not self.dwarfhunt_var.get():            
            print("Koordinate 3 42/BY aufgenommen, starte wieder die Suche.")
            gegner = self.opponent_var.get()
            bildpfad = os.path.join(GEGNER_DIR, gegner + ".png")
            self.suche_bis_gefunden(bildpfad, return_to=self.fahre_zur_koordinate3)

        if self.dwarfhunt_var.get():
            self.captcha_check()
            pyautogui.press("r")
            self.dwarfhunt(return_to=self.fahre_zur_koordinate3)

        if self.bm_var.get():
            self.captcha_check()
            self.death_check_bm()
            time.sleep(5)
            pyautogui.press("r")
            time.sleep(5)
            r, g, b = pyautogui.pixel(int(804), int(1027))
            brightness = 0.299 * r + 0.587 * g + 0.114 * b
            if brightness >= 70:
                pyautogui.press("r")
            while self.running:
                self.root.update()
                if not self.running:  
                    print("Reparatur abgebrochen.")
                self.captcha_check()
                self.death_check_bm()
                hp = self.check_hp()
                if hp > 85:
                    self.aktueller_startpunkt = 1
                    self.bmbot()
                    return
                time.sleep(3)
                hp2 = self.check_hp()
                print(f"Ist {hp} größer als {hp2}?")
                if hp > hp2:
                    print("Unter beschuss während dem reparieren.")
                    beschuss = True
                    self.fahre_zur_koordinate4(beschuss)

    def fahre_zur_koordinate4(self, beschuss=None):
        if not self.running:  
            print("Suche abgebrochen.")
            return
    ###Mechanismus zur Koordinateneingabe 4
        try:
            koordinaten_pfad = os.path.join("ressources", "kordsystem.png")
            position = locateOnScreen(koordinaten_pfad, confidence=0.8)
            if position:
                print("Kordsystem gefunden.")
                self.status_var.set("Debugging: Gehe nach X:13 Y:BS")
                ziel_x = position.left + position.width // 2
                ziel_y = position.top + position.height // 2
                pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
                pyautogui.click()
                time.sleep(0.1)
                pyautogui.press("1")
                time.sleep(0.1)
                pyautogui.press("3")
                time.sleep(0.1)
                pyautogui.press("tab")
                time.sleep(0.2)
                pyautogui.press("b")
                time.sleep(0.1)
                pyautogui.press("s")
                time.sleep(0.2)
                pyautogui.press("enter")
                print("Eingaben getätigt.")
                pyautogui.press("space")
                time.sleep(1.5)
                if self.bm_var.get() and beschuss == True:
                    print("Erweiterte Wartezeit aufgrund von Beschuss.")
                    time.sleep(8)
                    beschuss = False
        except:
            print("Koordinateneingabe nicht gefunden: kein VIP Mitglied.")
            print("Versuche ohne Koordinateneingabe zu bewegen.")
            self.status_var.set("Debugging: Versuche ohne Koordinateneingabe zu bewegen.")
            ziel_x = 1763
            ziel_y = 208
            pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
            pyautogui.mouseDown(button='left')
            time.sleep(0.5)
            pyautogui.mouseUp(button='left')
            ziel_y = 380
            ziel_x = 1174
            pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
            pyautogui.keyDown('ctrl')        
            pyautogui.mouseDown(button='left')
            time.sleep(0.1)
            pyautogui.mouseUp(button='left')
            pyautogui.keyUp('ctrl')
            ziel_y = 356
            pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
            pyautogui.keyDown('ctrl')        
            pyautogui.mouseDown(button='left')
            time.sleep(0.1)
            pyautogui.mouseUp(button='left')
            pyautogui.keyUp('ctrl')
            pyautogui.press("space")
            time.sleep(1.5)
            if self.bm_var.get() and beschuss == True:
                print("Erweiterte Wartezeit aufgrund von Beschuss.")
                time.sleep(8)
                beschuss = False
            pass
                    
        if not self.bm_var.get() and not self.dwarfhunt_var.get(): 
            print("Koordinate 4 13/BS aufgenommen, starte wieder die Suche.")
            gegner = self.opponent_var.get()
            bildpfad = os.path.join(GEGNER_DIR, gegner + ".png")
            self.suche_bis_gefunden(bildpfad, return_to=self.fahre_zur_koordinate4)

        if self.dwarfhunt_var.get():
            self.captcha_check()
            pyautogui.press("r")
            self.dwarfhunt(return_to=self.fahre_zur_koordinate4)

        if self.bm_var.get():
            self.captcha_check()
            self.death_check_bm()
            time.sleep(5)
            pyautogui.press("r")
            time.sleep(5)
            r, g, b = pyautogui.pixel(int(804), int(1027))
            brightness = 0.299 * r + 0.587 * g + 0.114 * b
            if brightness >= 70:
                pyautogui.press("r")
            while self.running:
                self.root.update()
                if not self.running:  
                    print("Reparatur abgebrochen.")
                self.captcha_check()
                self.death_check_bm()
                hp = self.check_hp()
                if hp > 85:
                    self.aktueller_startpunkt = 2
                    self.bmbot()
                    return
                time.sleep(3)
                hp2 = self.check_hp()
                print(f"Ist {hp} größer als {hp2}?")
                if hp > hp2:
                    print("Unter beschuss während dem reparieren.")
                    beschuss = True
                    self.fahre_zur_koordinate1(beschuss)
                    

        
###########################################################################################################       
        
    def bmbot(self):
        if not self.running:  
            print("Suche abgebrochen.")
            return
        self.captcha_check()
        self.death_check_bm()
        left, top, right, bottom = 1740, 93, 1875, 227
        screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
        target_rgb = (244, 0, 0)
        width, height = screenshot.size

        for x in range(width):
            for y in range(height):
                if screenshot.getpixel((x, y)) == target_rgb:
                    # Umrechnen auf globale Koordinaten
                    screen_x = left + x
                    screen_y = top + y
                    print(f"Gegner gefunden bei: {screen_x}, {screen_y}")
                    gefunden = True
                    self.bmbot_gegner_gefunden(screen_x, screen_y, gefunden)
                    return
        print("Kein roter Pixel gefunden. Sind wir auf der BM?")
        try:
            mapcheck = locateOnScreen("ressources/bmmap.png", confidence=0.80)
            if mapcheck:
                print("Wir sind auf einer Bonus Karte, starte Bonus-Map Bot.")
                self.status_var.set("Debugging: Bonus-Map Bot gestartet...")
                time.sleep(0.5)
                self.bmbot()
                return
        except:
            if not self.unlimitedbm.get():
                print("Wir sind nicht auf einer Bonus Karte.")
                self.status_var.set("Debugging: Wir sind nicht auf einer Bonus Karte. Beende das Spiel.")
                pyautogui.hotkey('alt', 'f4')
                print("BM-Bot hat die Bonus-Map abgeschlossen. Das Spiel wurde geschlossen.")
                return
            else:
                print("BM-Bot hat die Bonus-Map abgeschlossen. Starte die nächste Bonus-Map.")
                self.run_bm_logic()
                
            

    def bmbot_gegner_gefunden(self, x, y, gefunden):
        if not self.running:  
            print("Suche abgebrochen.")
            return
        self.captcha_check()
        self.death_check_bm()
        pyautogui.moveTo(x, y, duration=0.2)
        pyautogui.mouseDown(button='left')
        time.sleep(0.5)
        pyautogui.mouseUp(button='left')
        time.sleep(0.1)
        x = 960
        y = 540
        pyautogui.moveTo(x, y, duration=0.2)
        pyautogui.click()
        time.sleep(0.1)
        x = 975
        y = 555
        pyautogui.moveTo(x, y, duration=0.2)
        pyautogui.click()
        time.sleep(0.1)
        pyautogui.press("space")
        self.status_var.set("Debugging: Greife die NPCs an.")
        r, g, b = pyautogui.pixel(int(704), int(1028))
        brightness = 0.299 * r + 0.587 * g + 0.114 * b                     
        while brightness < 45:                        
            self.root.update()
            if not self.running:  
                print("Fahrt zum Gegner abgebrochen.")
                return
            r, g, b = pyautogui.pixel(int(704), int(1028))
            brightness = 0.299 * r + 0.587 * g + 0.114 * b
            self.captcha_check()
            self.death_check_bm()
            print(f"Aktuelle Helligkeit: {brightness:.2f}")
            
            if brightness > 45:
                print("Ziel erreicht. Starte schießen.")                    
                break          
            pyautogui.scroll(-1)
            time.sleep(0.5)
                
        while gefunden:
            gefunden = False
            x = 957
            y = 526
            pyautogui.moveTo(x, y, duration=0.1)
            pyautogui.click()
            pyautogui.press("e")
            
            check = 0
            check_failed = False
            while self.running:
                self.root.update()
                if not self.running:  
                    print("Angriff abgebrochen.")
                    return
                self.captcha_check()
                self.death_check_bm()                
                r, g, b = pyautogui.pixel(int(704), int(1028))
                brightness = 0.299 * r + 0.587 * g + 0.114 * b

                if brightness <= 45:
                    break

                print("Erwarte Tötung...")
                self.raketen()
                hp = self.check_hp()
                if hp < self.repair_percentage.get():
                    print("HP zu niedrig gehe reparieren.")
                    if self.aktueller_startpunkt is None:
                        sp_name = self.starting_point_var.get()
                        self.aktueller_startpunkt = self.starting_point_map.get(sp_name, 1)

                    # Dynamischer Methodenaufruf
                    method_name = f"fahre_zur_koordinate{self.aktueller_startpunkt}"
                    method = getattr(self, method_name, None)

                    if callable(method):
                        method()
                        return
                    else:
                        print(f"Fehler: Methode {method_name} existiert nicht.")
                        return
                                      
                time.sleep(1)
                
                check += 1            
                if check >= 10:
                    while True:
                        r, g, b = pyautogui.pixel(int(681), int(1052))
                        brightness = 0.299 * r + 0.587 * g + 0.114 * b
                        time.sleep(0.5)
                        r, g, b = pyautogui.pixel(int(681), int(1052))
                        brightness2 = 0.299 * r + 0.587 * g + 0.114 * b

                        if brightness <= 10 or brightness2 <= 10:
                            print("NPC noch unter Beschuss.")
                            check = 0
                            break
                        else:
                            check_failed = True
                            break

                if check_failed:
                    print(".!. Check failed untersuche bmt bot gefunden vor Gegner wurde getötet .!.")
                    break

            print("Gegner wurde getötet.")
            hp = self.check_hp()
            print("Suche 6x neben mir nach Gegner.")
            versuche = 6
            while versuche > 0:
                r, g, b = pyautogui.pixel(704, 1028)
                brightness = 0.299 * r + 0.587 * g + 0.114 * b
                print(f"Aktuelle Helligkeit: {brightness:.2f}")
                
                if brightness > 45:
                    print("Ziel erreicht. Starte schießen.")
                    gefunden = True
                    break
                
                pyautogui.scroll(-1)
                time.sleep(0.5)
                versuche -= 1
                                 
        
        print("Welle muesste durch sein erwarte neue Welle.")
        time.sleep(4)
        self.bmbot()
        return

    def check_hp(self):
        y = 938  
        x_start = 678
        x_end = 938
        for x in range(x_start, x_end + 1):
            r, g, b = pyautogui.pixel(x, y)
            brightness = 0.299 * r + 0.587 * g + 0.114 * b

            if brightness < 80:
                # Hier endet der grüne Bereich
                filled = x - x_start
                total = x_end - x_start
                hp_percent = int((filled / total) * 100)
                print(f"HP geschätzt: {hp_percent}%")
                return hp_percent
        print("HP geschätzt: 100%")
        return 100
    

    def raketen(self):        
        if self.rockets.get():
            r, g, b = pyautogui.pixel(int(905), int(1012))
            brightness = 0.299 * r + 0.587 * g + 0.114 * b
            r, g, b = pyautogui.pixel(int(925), int(1012))
            if brightness < 40 and (r, g, b) == (198, 0, 0):
                print("Nicht Schussbereit und deaktiviert.")
                pyautogui.press("4")
            if brightness < 40 and not (r, g, b) == (198, 0, 0):
                print("Raketen werden Nachgeladen oder Ziel außer Reichweite.")           
            if brightness > 40 and (r, g, b) == (198, 0, 0):
                print("Schussbereit und deaktiviert.")
                pyautogui.press("4")
                time.sleep(0.2)
                pyautogui.press("4")
            if brightness > 40 and not (r, g, b) == (198, 0, 0):
                print("Schussbereit und Gegner in Reichweite.")
                pyautogui.press("4")

        if self.balistics.get():
            r, g, b = pyautogui.pixel(int(970), int(1018))
            brightness = 0.299 * r + 0.587 * g + 0.114 * b
            r, g, b = pyautogui.pixel(int(977), int(1010))
            if brightness < 40 and (r, g, b) == (248, 0, 0):
                print("Nicht Schussbereit und deaktiviert.")
                pyautogui.press("5")
            if brightness < 40 and not (r, g, b) == (248, 0, 0):
                print("Balistics werden Nachgeladen oder Ziel außer Reichweite.")           
            if brightness > 40 and (r, g, b) == (248, 0, 0):
                print("Schussbereit und deaktiviert.")
                pyautogui.press("5")
                time.sleep(0.2)
                pyautogui.press("5")
            if brightness > 40 and not (r, g, b) == (248, 0, 0):
                print("Schussbereit und Gegner in Reichweite.")
                pyautogui.press("5")

    def schwarz_platten_check(self):
        try:
            if self.schwarzpulver.get():
                print("Schwarzpulver soll aktiviert sein!")
                schwarzAus_pfad = os.path.join("ressources", "schwarzAus.png")
                position = locateOnScreen(schwarzAus_pfad, confidence=0.95)
                if position:
                    ziel_x = position.left + position.width // 2
                    ziel_y = position.top + position.height // 2
                    r, g, b = pyautogui.pixel(int(ziel_x), int(ziel_y))
                    brightness = 0.299 * r + 0.587 * g + 0.114 * b
                    if brightness < 70:
                        print("Schwarzpulver ist deaktiviert, ich aktiviere es!")
                        self.status_var.set("Debugging: Aktiviere Schwarzpulver...")
                        pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
                        pyautogui.click()           
            else:
                print("Schwarzpulver soll deaktiviert sein!")
                schwarzAn_pfad = os.path.join("ressources", "schwarzAn.png")
                position = locateOnScreen(schwarzAn_pfad, confidence=0.95)
                if position:
                    ziel_x = position.left + position.width // 2
                    ziel_y = position.top + position.height // 2
                    r, g, b = pyautogui.pixel(int(ziel_x), int(ziel_y))
                    brightness = 0.299 * r + 0.587 * g + 0.114 * b
                    if brightness > 70:
                        print("Schwarzpulver ist aktiviert, ich deaktiviere es!")
                        self.status_var.set("Debugging: Deaktiviere Schwarzpulver...")
                        pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
                        pyautogui.click()
        except:
            print("Schwarzpulver wurde nicht gefunden. Abbruch!")
            self.status_var.set("Fehler: Bild des Schwarzpulvers nicht gefunden.")
            return
        
        try:
            if self.panzerplatten.get():
                print("Panzerplatten sollen aktiviert sein!")
                panzerAus_pfad = os.path.join("ressources", "panzerAus.png")
                position = locateOnScreen(panzerAus_pfad, confidence=0.95)
                if position:
                    ziel_x = position.left + position.width // 2
                    ziel_y = position.top + position.height // 2
                    r, g, b = pyautogui.pixel(int(ziel_x), int(ziel_y))
                    brightness = 0.299 * r + 0.587 * g + 0.114 * b                
                    if brightness < 65:
                        print("Panzerplatten sind deaktiviert sein, ich aktiviere sie!")
                        self.status_var.set("Debugging: Deaktiviere Panzerplatten...")
                        pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
                        pyautogui.click()                    
            else:
                print("Panzerplatten sollen deaktiviert sein!")
                panzerAn_pfad = os.path.join("ressources", "panzerAn.png")
                position = locateOnScreen(panzerAn_pfad, confidence=0.95)
                if position:
                    ziel_x = position.left + position.width // 2
                    ziel_y = position.top + position.height // 2
                    r, g, b = pyautogui.pixel(int(ziel_x), int(ziel_y))
                    brightness = 0.299 * r + 0.587 * g + 0.114 * b                
                    if brightness > 65:
                        print("Panzerplatten sind aktiviert, ich deaktiviere sie!")
                        self.status_var.set("Debugging: Aktiviere Panzerplatten...")
                        pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
                        pyautogui.click()
        except:
            print("Panzerplatten wurden nicht gefunden. Abbruch!")
            self.status_var.set("Fehler: Bild der Panzerplatten nicht gefunden.")
            return


                           
###########################################################################################################

    
            
    def run_bot_logic(self):
        self.status_var.set("Debugging: wird gestartet")
        print("Bot gestartet")
        
        gegner = self.opponent_var.get()
        bildpfad = os.path.join(GEGNER_DIR, gegner + ".png")


        ### Testbereich ###

        # Schwarzpulver und Panzerplattencheck
        self.schwarz_platten_check()

        # Mapping von Auswahl zu passender Methode
        sp_name = self.starting_point_var.get()
        sp_nummer = self.starting_point_map.get(sp_name, 1)  #w Fallback: 1

        # Dynamischer Methodenaufruf
        method_name = f"fahre_zur_koordinate{sp_nummer}"
        method = getattr(self, method_name, None)

        if callable(method):
            method()
        else:
            print(f"Fehler: Methode {method_name} existiert nicht.")        
        return

    def run_chesthunt_logic(self):
        self.status_var.set("Debugging: wird gestartet (Chesthunt)")
        print("Bot gestartet (Chesthunt)")

        gegner = self.opponent_var.get()
        bildpfad = os.path.join(GEGNER_DIR, gegner + ".png")

        # Schwarzpulver und Panzerplattencheck
        self.schwarz_platten_check()
        
        # Mapping von Auswahl zu passender Methode
        sp_name = self.starting_point_var.get()
        sp_nummer = self.starting_point_map.get(sp_name, 1)  # Fallback: 1

        # Dynamischer Methodenaufruf
        method_name = f"fahre_zur_koordinate{sp_nummer}"
        method = getattr(self, method_name, None)

        if callable(method):
            method()
        else:
            print(f"Fehler: Methode {method_name} existiert nicht.")
        return

    def run_dwarfhunt_logic(self):
        self.status_var.set("Debugging: Dwarfhunt wird gestartet")
        print("Dwarfhunt gestartet")
        
        gegner = self.opponent_var.get()
        bildpfad = os.path.join(GEGNER_DIR, gegner + ".png")

        # Schwarzpulver und Panzerplattencheck
        self.schwarz_platten_check()

        # Mapping von Auswahl zu passender Methode
        sp_name = self.starting_point_var.get()
        sp_nummer = self.starting_point_map.get(sp_name, 1)  # Fallback: 1

        # Dynamischer Methodenaufruf
        method_name = f"fahre_zur_koordinate{sp_nummer}"
        method = getattr(self, method_name, None)

        if callable(method):
            method()
        else:
            print(f"Fehler: Methode {method_name} existiert nicht.")        
        return

    def run_bm_logic(self):
        self.status_var.set("Debugging: Bonus-Map Bot wird gestartet")
        print("Bonus-Map Bot gestartet")


        # Schwarzpulver und Panzerplattencheck
        self.schwarz_platten_check()

        print("Sind wir auf einer Bonus Karte?")
        try:
            mapcheck = locateOnScreen("ressources/bmmap.png", confidence=0.80)
            if mapcheck:
                print("Wir sind auf einer Bonus Karte, starte Bonus-Map Bot.")
                self.status_var.set("Debugging: Bonus-Map Bot gestartet...")
                time.sleep(0.5)
                self.bmbot()
                return
        except:
            current_value = self.opponent_var.get()
            print(f"Wir sind nicht auf einer BM. Versuche {current_value} Bonus-Map beizutreten.")
            try:
                bmbutton = locateOnScreen("ressources/bmbutton.png", confidence=0.90)
                ziel_x = bmbutton.left + bmbutton.width // 2
                ziel_y = bmbutton.top + bmbutton.height // 2
                pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
                pyautogui.click() 
                ziel_x = 1486
                ziel_y = 161
                pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
                pyautogui.mouseDown(button='left')
                ziel_y = 925
                pyautogui.moveTo(ziel_x, ziel_y, duration=0.5)
                pyautogui.mouseUp(button='left')

                if current_value == "Magician":
                    ziel_x = 1320
                    ziel_y = 600
                    r, g, b = pyautogui.pixel(int(ziel_x), int(ziel_y))
                    brightness = 0.299 * r + 0.587 * g + 0.114 * b
                    pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
                    if brightness < 30:
                        pyautogui.click()
                        kaufbest = locateOnScreen("ressources/kaufbest.png", confidence=0.95)
                        ziel_x = kaufbest.left + kaufbest.width // 2
                        ziel_y = kaufbest.top + kaufbest.height // 2 + 20
                        pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
                        pyautogui.click()
                        print("Zugang zu Magician erworben.")
                        ziel_x = ziel_x + 100
                        pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
                        pyautogui.click()
                        time.sleep(0.5)
                        ziel_x = 1320
                        ziel_y = 600
                        r, g, b = pyautogui.pixel(int(ziel_x), int(ziel_y))
                        brightness = 0.299 * r + 0.587 * g + 0.114 * b
                        pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
                    if brightness > 30:
                        pyautogui.click()
                        print(f"Trete Bonus-Map {current_value} bei.")
                        time.sleep(17)
                        self.bmbot()
                    else:
                        print("Scheinbar nicht genug Perlen, beende das Spiel.")
                        pyautogui.hotkey('alt', 'f4')
                        return
                if current_value == "Port Royal":
                    ziel_x = 1313
                    ziel_y = 390
                    r, g, b = pyautogui.pixel(int(ziel_x), int(ziel_y))
                    brightness = 0.299 * r + 0.587 * g + 0.114 * b
                    pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
                    if brightness < 30:
                        pyautogui.click()
                        kaufbest = locateOnScreen("ressources/kaufbest.png", confidence=0.95)
                        ziel_x = kaufbest.left + kaufbest.width // 2
                        ziel_y = kaufbest.top + kaufbest.height // 2 + 20
                        pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
                        pyautogui.click()
                        print("Zugang zu Port Royal erworben.")
                        ziel_x = ziel_x + 100
                        pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
                        pyautogui.click()
                        time.sleep(0.5)
                        ziel_x = 1313
                        ziel_y = 390
                        r, g, b = pyautogui.pixel(int(ziel_x), int(ziel_y))
                        brightness = 0.299 * r + 0.587 * g + 0.114 * b
                        pyautogui.moveTo(ziel_x, ziel_y, duration=0.2)
                    if brightness > 30:
                        pyautogui.click()
                        print(f"Trete Bonus-Map {current_value} bei.")
                        time.sleep(17)
                        self.bmbot()
                    else:
                        print("Scheinbar nicht genug Kartenteile, beende das Spiel.")
                        pyautogui.hotkey('alt', 'f4')
                        return

                    
                return
            except:
                print("Fehler bei bmbutton suche.")
                return
            print("Fehler bei bmmap suche.")                
            return
        

            
    def load_opponent_list(self):
        if not os.path.exists(GEGNER_DIR):
            print(f"Ordner {GEGNER_DIR} nicht gefunden.")
            return

        png_files = [f[:-4] for f in os.listdir(GEGNER_DIR) if f.lower().endswith(".png")]
        self.opponent_selector["values"] = png_files

        if png_files:
            self.opponent_selector.current(0)
            # Verzögertes Laden nach dem Aufbau des GUI
            self.root.after(100, lambda: self.load_image(png_files[0]))


    def load_image(self, name):
        path = os.path.join(GEGNER_PREVIEW, name + ".png")
        try:
            image = Image.open(path)
            image = image.resize((100, 100), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(image)  # dauerhaft in self speichern!
            self.image_label.config(image=self.photo)
        except Exception as e:
            print(f"Fehler beim Laden von {path}: {e}")


    def change_image(self, event):
        name = self.opponent_var.get()
        self.load_image(name)

    def start_bot(self):
        self.status_var.set("Debugging: Bot startet in 3...")
        self.root.after(1000, lambda: self.status_var.set("Debugging: Bot startet in 2..."))
        self.root.after(2000, lambda: self.status_var.set("Debugging: Bot startet in 1..."))
        self.running = True
        if self.chesthunt_var.get():
            self.root.after(3000, self.run_chesthunt_logic)

        if self.dwarfhunt_var.get():
            self.root.after(3000, self.run_dwarfhunt_logic)

        if self.bm_var.get():
            self.root.after(3000, self.run_bm_logic)

        if not self.chesthunt_var.get() and not self.dwarfhunt_var.get() and not self.bm_var.get():
            self.root.after(3000, self.run_bot_logic)
            
        print("Bot gestartet")


    def stop_bot(self):
        self.running = False
        self.status_var.set("Debugging: Wird gestoppt.")
        print("Bot gestoppt")

    def quit_app(self):
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    root.attributes("-topmost", True)
    root.resizable(False, False)
    app = BotGUI(root)
    root.mainloop()
