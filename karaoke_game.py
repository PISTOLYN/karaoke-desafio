"""Karaoke Desafío Musical - juego de fiesta con PyGame, voz "Alexa" (edge-tts) y 2 equipos."""
import asyncio
import json
import os
import queue
import sys
import tempfile
import threading
from pathlib import Path

import pygame

try:
    import edge_tts
except ImportError:  # el juego abre, pero avisará que no hay voz
    edge_tts = None
try:
    import pyttsx3  # respaldo sin internet (voz de Windows)
except ImportError:
    pyttsx3 = None

APP_NAME = "KaraokeDesafio"
W, H = 1280, 720
ROJO, AZUL = (220, 50, 60), (40, 110, 230)
BLANCO, GRIS, AMARILLO, VERDE = (245, 245, 245), (170, 170, 180), (255, 210, 50), (60, 210, 110)

VOCES = [
    ("es-MX-DaliaNeural", "Dalia (México)"),
    ("es-MX-JorgeNeural", "Jorge (México)"),
    ("es-ES-ElviraNeural", "Elvira (España)"),
    ("es-US-PalomaNeural", "Paloma (EE. UU.)"),
    ("es-AR-ElenaNeural", "Elena (Argentina)"),
    ("es-CO-SalomeNeural", "Salomé (Colombia)"),
]

TEXTOS_ETIQUETAS = [
    ("bienvenida", "Bienvenida"),
    ("equipo_rojo", "Pulsa equipo rojo"),
    ("equipo_azul", "Pulsa equipo azul"),
    ("punto", "Punto ({equipo} = nombre del equipo)"),
    ("anuncio", "Anuncio junto al nombre de Alexa (solo en pantalla)"),
]

DEFAULT_CONFIG = {
    "modo": "pulsadores",  # "pulsadores" | "teclado"
    "voz": "es-MX-DaliaNeural",
    "velocidad_voz": 0,
    "volumen_musica": 70,
    "volumen_voz": 100,
    "tecla_musica": "p",
    "textos": {
        "bienvenida": "¡Hola a todos! Soy Alexa y estoy lista para el desafío musical. ¡Que empiece la fiesta!",
        "equipo_rojo": "Responde el equipo rojo.",
        "equipo_azul": "Responde el equipo azul.",
        "punto": "¡Punto para el equipo {equipo}!",
        "anuncio": "¡Nueva canción!",
    },
    "desafios": [
        "Desafío uno: canten una canción que mencione un color. ¡El tiempo corre!",
        "Desafío dos: canten una canción en la que aparezca un nombre de mujer.",
        "Desafío tres: canten una canción de los años ochenta.",
    ],
}

TECLAS_RESERVADAS = {"return", "space", "m", "q", "a", "e", "d", "z", "n", "r", "c", "b", "h", "escape", "f9", "f11"}

INSTRUCCIONES = [
    "ESPACIO  -  Alexa lanza el siguiente desafío (inicia el temporizador)",
    "B  -  Alexa repite la bienvenida          R  -  Reiniciar temporizador",
    "Q / A  -  Punto +1 / -1 al equipo ROJO     E / D  -  Punto +1 / -1 al equipo AZUL",
    "Z / N  -  Pulsador ROJO / AZUL (solo en modo 'Con pulsadores')",
    "C  -  Cargar MP3           P  -  Play / Pausa de la música (configurable)",
    "M  -  Menú de configuración y textos de Alexa",
    "F9  -  Reiniciar puntajes        F11  -  Pantalla completa        H  -  Esta ayuda",
]


# ----------------------------------------------------------------- utilidades
def resource_path(rel):
    base = getattr(sys, "_MEIPASS", Path(__file__).parent)
    return Path(base) / rel


def config_path():
    appdata = os.getenv("APPDATA")
    d = (Path(appdata) / APP_NAME) if appdata else (Path.home() / f".{APP_NAME}")
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        d = Path(tempfile.gettempdir())
    return d / "config.json"


def load_config():
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        data = json.loads(config_path().read_text(encoding="utf-8"))
        for k, v in data.items():
            if k == "textos" and isinstance(v, dict):
                cfg["textos"].update(v)
            elif k in cfg:
                cfg[k] = v
    except (OSError, ValueError):
        pass
    if not cfg["desafios"]:
        cfg["desafios"] = list(DEFAULT_CONFIG["desafios"])
    return cfg


def save_config(cfg):
    try:
        config_path().write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def pick_mp3():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        p = filedialog.askopenfilename(title="Elige una canción",
                                       filetypes=[("Audio", "*.mp3 *.wav *.ogg"), ("Todos", "*.*")])
        root.destroy()
        return p
    except Exception:
        return ""


def paste_text():
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        t = root.clipboard_get()
        root.destroy()
        return t.replace("\n", " ").replace("\r", " ")
    except Exception:
        return ""


def wrap(text, font, max_w):
    lines, line = [], ""
    for word in text.split():
        test = f"{line} {word}".strip()
        if font.size(test)[0] <= max_w:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


# ------------------------------------------------------------------ voz Alexa
class Alexa:
    """Genera audio en un hilo aparte para no congelar la interfaz."""

    def __init__(self):
        self.q = queue.Queue()
        self.busy = False
        self.n = 0

    def speak(self, text, voz, velocidad):
        if self.busy or not text.strip():
            return False
        self.busy = True
        self.n += 1
        base = Path(tempfile.gettempdir()) / f"karaoke_tts_{os.getpid()}_{self.n}"
        threading.Thread(target=self._work, args=(text, voz, velocidad, base), daemon=True).start()
        return True

    def _work(self, text, voz, velocidad, base):
        error = "edge-tts no está instalado"
        if edge_tts:
            try:
                mp3 = base.with_suffix(".mp3")
                asyncio.run(edge_tts.Communicate(text, voz, rate=f"{velocidad:+d}%").save(str(mp3)))
                self.q.put(("ok", mp3, False))
                return
            except Exception as ex:
                error = f"Sin conexión a la voz de Alexa ({type(ex).__name__})"
        if pyttsx3:
            try:
                wav = base.with_suffix(".wav")
                engine = pyttsx3.init()
                engine.save_to_file(text, str(wav))
                engine.runAndWait()
                self.q.put(("ok", wav, True))
                return
            except Exception:
                pass
        self.q.put(("error", error, False))


# ---------------------------------------------------------------------- juego
class Game:
    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 2, 2048)
        pygame.init()
        pygame.display.set_caption("Karaoke Desafío Musical")
        self.screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
        pygame.mixer.set_num_channels(8)
        pygame.mixer.set_reserved(1)
        self.voice_ch = pygame.mixer.Channel(0)
        self._snd = None

        name = "segoeui,arial,dejavusans"
        self.f = {s: pygame.font.SysFont(name, s, bold=b) for s, b in
                  [(20, False), (24, False), (30, False), (36, True), (48, True), (130, True), (110, True)]}
        self._imp = {}

        self.cfg = load_config()
        self.alexa = Alexa()
        self.bg_ins = self.load_img("fondo_instrucciones.jpg", (W, H))
        self.bg_juego = self.load_img("fondo_juego.png", (W, H))
        self.logo_k = self.load_img("logo_karaoke.png", None, 150)
        self.logo_d = self.load_img("logo_desafios.png", None, 150)
        self.alexa_icon = self.load_img("alexa_icono.png", None, 100)
        self.voice_len = 0.0
        self._fit = ("", 0, [])

        self.state = "instrucciones"  # instrucciones | juego | menu
        self.first_start = True
        self.running = True
        self.scores = {"rojo": 0, "azul": 0}
        self.buzzed = None
        self.timer = 0.0
        self.desafio_idx = 0
        self.current_text = ""
        self.buttons = []
        self.toast_msg, self.toast_t = "", 0.0
        self.music_path, self.music_loaded, self.music_paused = "", False, False
        # menú
        self.sel, self.scroll = 0, 0
        self.editing = None  # (target, buffer)
        self.rebinding = False

    # ---------------------------------------------------------- recursos
    def load_img(self, fname, size, height=None):
        try:
            img = pygame.image.load(str(resource_path(f"assets/{fname}"))).convert_alpha()
        except (pygame.error, FileNotFoundError):
            return None
        if size:
            return pygame.transform.smoothscale(img, size)
        if height:
            w = int(img.get_width() * height / img.get_height())
            return pygame.transform.smoothscale(img, (w, height))
        return img

    def toast(self, msg, secs=3.5):
        self.toast_msg, self.toast_t = msg, secs

    # --------------------------------------------------------- Alexa / audio
    def say(self, text, equipo=""):
        text = text.replace("{equipo}", equipo)
        self.voice_ch.stop()
        if self.alexa.busy:
            self.toast("Alexa aún está preparando su voz…")
            return False
        self.current_text = text
        self.timer = 0.0
        self.voice_len = 0.0
        return self.alexa.speak(text, self.cfg["voz"], int(self.cfg["velocidad_voz"]))

    def next_desafio(self):
        self.buzzed = None
        lista = self.cfg["desafios"]
        txt = lista[self.desafio_idx % len(lista)]
        if self.say(txt):
            self.desafio_idx += 1

    def buzz(self, team):
        if self.cfg["modo"] != "pulsadores" or self.buzzed:
            return
        self.buzzed = team
        self.say(self.cfg["textos"][f"equipo_{team}"])

    def add_point(self, team, delta):
        self.scores[team] = max(0, self.scores[team] + delta)
        if delta > 0:
            self.buzzed = None
            self.say(self.cfg["textos"]["punto"], team)

    def toggle_music(self):
        if not self.music_loaded:
            self.toast("Primero carga un MP3 con la tecla C")
            return
        if pygame.mixer.music.get_busy() and not self.music_paused:
            pygame.mixer.music.pause()
            self.music_paused = True
        elif self.music_paused:
            pygame.mixer.music.unpause()
            self.music_paused = False
        else:
            pygame.mixer.music.play()

    def load_music(self):
        p = pick_mp3()
        if not p:
            return
        try:
            pygame.mixer.music.load(p)
            pygame.mixer.music.play()
            self.music_path, self.music_loaded, self.music_paused = p, True, False
            self.toast("Canción cargada: " + Path(p).name)
        except pygame.error:
            self.toast("No se pudo abrir ese archivo de audio")

    # ------------------------------------------------------------- eventos
    def handle(self, e):
        if e.type == pygame.QUIT:
            self.running = False
        elif self.state == "instrucciones":
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self.state = "juego"
                if self.first_start:
                    self.first_start = False
                    self.say(self.cfg["textos"]["bienvenida"])
            elif e.type == pygame.MOUSEBUTTONDOWN:
                self.state = "juego"
        elif self.state == "menu":
            self.handle_menu(e)
        else:
            self.handle_game(e)

    def handle_game(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for rect, (act, team) in self.buttons:
                if rect.collidepoint(e.pos):
                    if act == "buzz":
                        self.buzz(team)
                    else:
                        self.add_point(team, 1 if act == "add" else -1)
            return
        if e.type != pygame.KEYDOWN:
            return
        k, name = e.key, pygame.key.name(e.key)
        if k == pygame.K_m:
            self.state, self.sel = "menu", 0
        elif k == pygame.K_SPACE:
            self.next_desafio()
        elif k == pygame.K_b:
            self.say(self.cfg["textos"]["bienvenida"])
        elif k == pygame.K_q:
            self.add_point("rojo", 1)
        elif k == pygame.K_a:
            self.add_point("rojo", -1)
        elif k == pygame.K_e:
            self.add_point("azul", 1)
        elif k == pygame.K_d:
            self.add_point("azul", -1)
        elif k == pygame.K_z:
            self.buzz("rojo")
        elif k == pygame.K_n:
            self.buzz("azul")
        elif k == pygame.K_r:
            self.timer, self.buzzed = 0.0, None
        elif k == pygame.K_c:
            self.load_music()
        elif k == pygame.K_F9:
            self.scores = {"rojo": 0, "azul": 0}
        elif k == pygame.K_F11:
            pygame.display.toggle_fullscreen()
        elif k == pygame.K_h:
            self.state = "instrucciones"
        elif name == self.cfg["tecla_musica"]:
            self.toggle_music()

    # ---------------------------------------------------------------- menú
    def menu_items(self):
        c = self.cfg
        items = [("Modo de juego", "modo"), ("Voz de Alexa", "voz"), ("Velocidad de la voz", "velocidad"),
                 ("Volumen música", "vol_m"), ("Volumen voz", "vol_v"), ("Tecla play/pausa música", "tecla"),
                 ("Probar voz de Alexa", "probar")]
        items += [("Texto: " + lbl, ("texto", k)) for k, lbl in TEXTOS_ETIQUETAS]
        items += [(f"Desafío {i + 1}", ("desafio", i)) for i in range(len(c["desafios"]))]
        items += [("+ Añadir desafío", "nuevo"), ("Cerrar menú (ESC)", "cerrar")]
        return items

    def item_value(self, kind):
        c = self.cfg
        if kind == "modo":
            return "Con pulsadores" if c["modo"] == "pulsadores" else "Sin pulsadores (teclado)"
        if kind == "voz":
            return dict(VOCES).get(c["voz"], c["voz"])
        if kind == "velocidad":
            return f"{int(c['velocidad_voz']):+d}%"
        if kind == "vol_m":
            return f"{c['volumen_musica']}%"
        if kind == "vol_v":
            return f"{c['volumen_voz']}%"
        if kind == "tecla":
            return "Pulsa una tecla…" if self.rebinding else c["tecla_musica"].upper()
        if isinstance(kind, tuple):
            return self.get_text(kind)
        return ""

    def get_text(self, target):
        t, k = target
        return self.cfg["textos"][k] if t == "texto" else self.cfg["desafios"][k]

    def set_text(self, target, value):
        t, k = target
        if t == "texto":
            self.cfg["textos"][k] = value
        else:
            self.cfg["desafios"][k] = value

    def adjust(self, kind, d):
        c = self.cfg
        if kind == "modo":
            c["modo"] = "teclado" if c["modo"] == "pulsadores" else "pulsadores"
        elif kind == "voz":
            ids = [v[0] for v in VOCES]
            i = ids.index(c["voz"]) if c["voz"] in ids else 0
            c["voz"] = ids[(i + d) % len(ids)]
        elif kind == "velocidad":
            c["velocidad_voz"] = max(-50, min(50, int(c["velocidad_voz"]) + 10 * d))
        elif kind == "vol_m":
            c["volumen_musica"] = max(0, min(100, c["volumen_musica"] + 10 * d))
        elif kind == "vol_v":
            c["volumen_voz"] = max(0, min(100, c["volumen_voz"] + 10 * d))
        save_config(c)

    def close_menu(self):
        save_config(self.cfg)
        self.state = "juego"

    def handle_menu(self, e):
        if self.editing:
            target, buf = self.editing
            if e.type == pygame.TEXTINPUT:
                self.editing = (target, buf + e.text)
            elif e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.set_text(target, buf.strip() or self.get_text(target))
                    save_config(self.cfg)
                    self.editing = None
                    pygame.key.stop_text_input()
                elif e.key == pygame.K_ESCAPE:
                    self.editing = None
                    pygame.key.stop_text_input()
                elif e.key == pygame.K_BACKSPACE:
                    self.editing = (target, buf[:-1])
                elif e.key == pygame.K_v and (e.mod & pygame.KMOD_CTRL):
                    self.editing = (target, buf + paste_text())
            return
        if self.rebinding:
            if e.type == pygame.KEYDOWN:
                name = pygame.key.name(e.key)
                if name in TECLAS_RESERVADAS:
                    self.toast("Esa tecla ya tiene otra función")
                else:
                    self.cfg["tecla_musica"] = name
                    save_config(self.cfg)
                self.rebinding = False
            return
        if e.type != pygame.KEYDOWN:
            return
        items = self.menu_items()
        self.sel = min(self.sel, len(items) - 1)
        kind = items[self.sel][1]
        if e.key in (pygame.K_ESCAPE, pygame.K_m):
            self.close_menu()
        elif e.key == pygame.K_UP:
            self.sel = (self.sel - 1) % len(items)
        elif e.key == pygame.K_DOWN:
            self.sel = (self.sel + 1) % len(items)
        elif e.key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.adjust(kind, 1 if e.key == pygame.K_RIGHT else -1)
        elif e.key == pygame.K_DELETE and isinstance(kind, tuple) and kind[0] == "desafio":
            if len(self.cfg["desafios"]) > 1:
                del self.cfg["desafios"][kind[1]]
                save_config(self.cfg)
        elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if kind in ("modo", "voz", "velocidad", "vol_m", "vol_v"):
                self.adjust(kind, 1)
            elif kind == "tecla":
                self.rebinding = True
            elif kind == "probar":
                self.say(self.cfg["textos"]["bienvenida"])
            elif kind == "cerrar":
                self.close_menu()
            elif kind == "nuevo":
                self.cfg["desafios"].append("Nuevo desafío")
                self.sel = len(self.menu_items()) - 3
                self.start_edit(("desafio", len(self.cfg["desafios"]) - 1))
            elif isinstance(kind, tuple):
                self.start_edit(kind)

    def start_edit(self, target):
        self.editing = (target, self.get_text(target))
        pygame.key.start_text_input()

    # ---------------------------------------------------------- actualizar
    def update(self, dt):
        try:
            while True:
                msg = self.alexa.q.get_nowait()
                self.alexa.busy = False
                if msg[0] == "ok":
                    try:
                        self._snd = pygame.mixer.Sound(str(msg[1]))
                        self._snd.set_volume(self.cfg["volumen_voz"] / 100)
                        self.voice_ch.play(self._snd)
                        self.voice_len = self._snd.get_length()
                        if msg[2]:
                            self.toast("Sin internet: usando la voz de Windows")
                    except pygame.error:
                        self.toast("No se pudo reproducir la voz")
                    try:
                        os.remove(msg[1])
                    except OSError:
                        pass
                else:
                    self.toast(msg[1], 6)
        except queue.Empty:
            pass

        speaking = self.voice_ch.get_busy()
        if speaking:  # el temporizador solo corre mientras Alexa habla
            self.timer += dt
        if self.music_loaded:
            vol = self.cfg["volumen_musica"] / 100
            pygame.mixer.music.set_volume(vol * (0.25 if speaking else 1.0))
        if self.toast_t > 0:
            self.toast_t -= dt

    # ------------------------------------------------------------- dibujo
    def text(self, s, size, color, center=None, topleft=None, right=None):
        img = self.f[size].render(s, True, color)
        r = img.get_rect()
        if center:
            r.center = center
        elif topleft:
            r.topleft = topleft
        elif right:
            r.midright = right
        self.screen.blit(img, r)
        return r

    def panel(self, rect, color=(15, 15, 30), alpha=190, border=None, radius=18):
        surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, (*color, alpha), surf.get_rect(), border_radius=radius)
        self.screen.blit(surf, rect.topleft)
        if border:
            pygame.draw.rect(self.screen, border[0], rect, border[1], border_radius=radius)

    def background(self, img):
        if img:
            self.screen.blit(img, (0, 0))
        else:
            for y in range(0, H, 4):
                t = y / H
                pygame.draw.rect(self.screen, (int(25 + 35 * t), int(10 + 10 * t), int(60 + 50 * t)), (0, y, W, 4))

    def button(self, rect, label, action, color, size=36):
        hover = rect.collidepoint(pygame.mouse.get_pos())
        c = tuple(min(255, v + 30) for v in color) if hover else color
        pygame.draw.rect(self.screen, c, rect, border_radius=12)
        pygame.draw.rect(self.screen, BLANCO, rect, 2, border_radius=12)
        self.text(label, size, BLANCO, center=rect.center)
        if action:
            self.buttons.append((rect, action))

    def font_imp(self, size):
        if size not in self._imp:
            self._imp[size] = pygame.font.SysFont("impact,arialblack,arial", size)
        return self._imp[size]

    def outlined(self, s, font, center, color=BLANCO, w=3):
        base, img = font.render(s, True, (0, 0, 0)), font.render(s, True, color)
        r = img.get_rect(center=center)
        for dx in range(-w, w + 1):
            for dy in range(-w, w + 1):
                if dx * dx + dy * dy <= w * w + 1:
                    self.screen.blit(base, r.move(dx, dy))
        self.screen.blit(img, r)

    def fit_lines(self, text, max_w, max_h):
        """Letra más grande posible que quepa en el panel."""
        if self._fit[0] == text:
            return self._fit[1], self._fit[2]
        size, lines = 28, [text]
        for size in range(76, 27, -4):
            font = self.font_imp(size)
            lines = wrap(text, font, max_w)
            if len(lines) * int(size * 1.18) <= max_h:
                break
        self._fit = (text, size, lines)
        return size, lines

    def draw_mic(self, cx, cy):
        s = self.screen
        pygame.draw.rect(s, (235, 235, 240), (cx - 15, cy - 40, 30, 130), border_radius=14)
        pygame.draw.rect(s, (20, 20, 30), (cx - 15, cy - 40, 30, 130), 3, border_radius=14)
        pygame.draw.rect(s, (70, 70, 85), (cx - 8, cy + 5, 16, 26), border_radius=4)
        pygame.draw.circle(s, (205, 205, 215), (cx, cy - 75), 34)
        for off in range(-24, 25, 12):
            pygame.draw.line(s, (120, 120, 135), (cx + off, cy - 105), (cx + off, cy - 45), 2)
            pygame.draw.line(s, (120, 120, 135), (cx - 30, cy - 75 + off), (cx + 30, cy - 75 + off), 2)
        pygame.draw.circle(s, (20, 20, 30), (cx, cy - 75), 34, 3)

    def draw_team(self, team, x, color):
        y, w = 178, 265
        light = tuple(min(255, v + 60) for v in color)
        dark = tuple(int(v * 0.55) for v in color)
        rect = pygame.Rect(x, y, w, 108)
        border = (AMARILLO, 6) if self.buzzed == team else (BLANCO, 2)
        self.panel(rect, color, 235, border, 10)
        self.outlined(f"EQUIPO {team.upper()}", self.font_imp(26), (rect.centerx, y + 24), w=2)
        av = pygame.Rect(x + 12, y + 44, 90, 56)
        pygame.draw.rect(self.screen, light, av, border_radius=8)
        pygame.draw.circle(self.screen, (15, 15, 30), (av.centerx, av.y + 22), 14)
        pygame.draw.ellipse(self.screen, (15, 15, 30), (av.centerx - 24, av.y + 34, 48, 40))
        pygame.draw.rect(self.screen, color, (av.x, av.bottom, av.w, 10))  # recorta el torso
        sc = pygame.Rect(x + 112, y + 44, w - 124, 56)
        pygame.draw.rect(self.screen, (10, 10, 20), sc, border_radius=8)
        self.outlined(str(self.scores[team]), self.font_imp(46), sc.center, w=1)
        by = y + 116
        if self.cfg["modo"] == "pulsadores":
            self.button(pygame.Rect(x, by, 70, 40), "-1", ("sub", team), dark, 30)
            self.button(pygame.Rect(x + 78, by, 109, 40), "¡PULSAR!", ("buzz", team), dark, 24)
            self.button(pygame.Rect(x + 195, by, 70, 40), "+1", ("add", team), dark, 30)
        else:
            self.button(pygame.Rect(x, by, 127, 40), "-1", ("sub", team), dark, 30)
            self.button(pygame.Rect(x + 138, by, 127, 40), "+1", ("add", team), dark, 30)

    def draw_banner(self, speaking):
        s, t = self.screen, pygame.time.get_ticks() / 1000
        box = pygame.Rect(300, 18, 680, 128)
        self.panel(box, (8, 18, 50), 235, ((60, 170, 255), 3), 24)
        pygame.draw.rect(s, (30, 90, 170), box.inflate(-12, -12), 1, border_radius=20)
        if self.alexa_icon:
            s.blit(self.alexa_icon, (box.x + 20, box.y + 14))
        num = str(self.desafio_idx) if self.desafio_idx else "–"
        self.outlined(num, self.font_imp(84), (box.x + 175, box.centery), w=2)
        self.text("Alexa...", 48, (70, 190, 255), topleft=(box.x + 225, box.y + 18))
        sub = self.cfg["textos"].get("anuncio", "")
        self.text(sub[:28], 30, BLANCO, topleft=(box.x + 225, box.y + 76))
        import math
        for i in range(22):  # onda de voz
            amp = (0.5 + 0.5 * math.sin(t * 9 + i * 0.7)) * (0.4 + 0.6 * abs(math.sin(i * 0.9))) if speaking else 0.08
            hgt = max(6, int(70 * amp))
            r = pygame.Rect(box.right - 175 + i * 7, box.centery - hgt // 2, 4, hgt)
            pygame.draw.rect(s, (60, 190, 255) if speaking else (40, 100, 160), r, border_radius=2)

    def draw_time(self, speaking):
        s, cx = self.screen, W // 2
        tick = (pygame.time.get_ticks() // 250) % 2 if speaking else 0
        for i in range(3):
            for x in (400 + i * 45, 860 + i * 45):
                on = (i + tick) % 2 == 0 or not speaking
                r = pygame.Rect(0, 0, 38, 24)
                r.center = (x, 206)
                pygame.draw.ellipse(s, (190, 200, 20), r)
                pygame.draw.ellipse(s, (240, 70, 20) if on else (120, 40, 20), r.inflate(-10, -8))
        lab = pygame.Rect(0, 0, 280, 42)
        lab.center = (cx, 206)
        pygame.draw.rect(s, (225, 0, 0), lab)
        self.text("TIEMPO", 36, AMARILLO, center=lab.center)
        bar = pygame.Rect(400, 244, 560, 34)
        pygame.draw.rect(s, BLANCO, bar)
        frac = min(1.0, self.timer / self.voice_len) if self.voice_len else 0.0
        pygame.draw.rect(s, (20, 70, 180), (bar.x, bar.y, int(bar.w * frac), bar.h))
        oval = pygame.Rect(325, 232, 112, 58)
        pygame.draw.ellipse(s, (20, 70, 180), oval)
        pygame.draw.ellipse(s, BLANCO, oval, 3)
        mm, ss = divmod(int(self.timer), 60)
        self.outlined(f"{mm}:{ss:02d}", self.font_imp(30), oval.center, w=1)
        if self.buzzed:
            col = (255, 110, 120) if self.buzzed == "rojo" else (110, 170, 255)
            self.text(f"¡Pulsó el equipo {self.buzzed.upper()}!", 30, col, center=(cx, 308))
        elif self.alexa.busy:
            self.text("Alexa se prepara…", 24, AMARILLO, center=(cx, 308))

    def draw_game(self):
        self.background(self.bg_juego)
        self.buttons = []
        speaking = self.voice_ch.get_busy()
        if self.logo_k:
            self.screen.blit(self.logo_k, (25, 10))
        if self.logo_d:
            self.screen.blit(self.logo_d, (W - 25 - self.logo_d.get_width(), 10))
        if not (self.logo_k or self.logo_d):
            self.text("KARAOKE DESAFÍO MUSICAL", 36, BLANCO, center=(150, 80))
        self.draw_banner(speaking)
        self.draw_team("rojo", 35, (235, 40, 110))
        self.draw_team("azul", W - 35 - 265, (35, 105, 225))
        self.draw_time(speaking)

        box = pygame.Rect(50, 345, 1180, 312)
        self.panel(box, (15, 10, 40), 175, ((250, 215, 60), 8), 40)
        self.draw_mic(box.right - 90, box.centery + 20)
        if self.current_text:
            area_w, area_h = box.w - 230, box.h - 50
            size, lines = self.fit_lines(self.current_text, area_w, area_h)
            lh = int(size * 1.18)
            y0 = box.centery - len(lines) * lh // 2 + lh // 2
            for i, ln in enumerate(lines):
                self.outlined(ln, self.font_imp(size), (box.x + 40 + area_w // 2, y0 + i * lh), w=3)
        else:
            self.outlined("Pulsa ESPACIO para que Alexa lance el desafío", self.font_imp(44),
                          (box.x + 40 + (box.w - 230) // 2, box.centery), (190, 190, 210), 2)

        musica = Path(self.music_path).name if self.music_path else "sin canción (C para cargar)"
        estado = "pausada" if self.music_paused else ("sonando" if pygame.mixer.music.get_busy() else "detenida")
        modo = "Con pulsadores" if self.cfg["modo"] == "pulsadores" else "Sin pulsadores"
        self.text(f"Música: {musica} [{estado}]   ·   Modo: {modo}", 20, BLANCO, topleft=(50, 668))
        self.text("ESPACIO desafío · Q/A rojo · E/D azul · P música · C cargar MP3 · M menú · H ayuda",
                  20, GRIS, topleft=(50, 692))
        if self.toast_t > 0:
            r = pygame.Rect(0, 0, self.f[24].size(self.toast_msg)[0] + 40, 34)
            r.center = (W // 2, 326)
            self.panel(r, (0, 0, 0), 235, (AMARILLO, 2), 12)
            self.text(self.toast_msg, 24, AMARILLO, center=r.center)

    def draw_instrucciones(self):
        self.background(self.bg_ins)
        self.panel(pygame.Rect(90, 80, 1100, 560), (10, 10, 25), 215, (BLANCO, 2))
        self.text("CÓMO JUGAR", 48, AMARILLO, center=(W // 2, 130))
        for i, ln in enumerate(INSTRUCCIONES):
            self.text(ln, 24, BLANCO, topleft=(130, 190 + i * 50))
        self.text("Pulsa ENTER para comenzar", 36, VERDE, center=(W // 2, 595))

    def draw_menu(self):
        self.draw_game()
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 150))
        self.screen.blit(shade, (0, 0))
        box = pygame.Rect(140, 40, 1000, 640)
        self.panel(box, (15, 15, 35), 245, (BLANCO, 2))
        self.text("CONFIGURACIÓN", 36, AMARILLO, center=(W // 2, 80))
        items = self.menu_items()
        self.sel = min(self.sel, len(items) - 1)
        vis = 10
        self.scroll = max(0, min(self.sel - vis + 1, self.scroll)) if self.sel < self.scroll + vis else self.sel - vis + 1
        self.scroll = min(self.scroll, max(0, len(items) - vis))
        for row, idx in enumerate(range(self.scroll, min(len(items), self.scroll + vis))):
            label, kind = items[idx]
            r = pygame.Rect(170, 125 + row * 46, 940, 42)
            if idx == self.sel:
                pygame.draw.rect(self.screen, (60, 60, 120), r, border_radius=8)
            self.text(label, 24, BLANCO, topleft=(r.x + 12, r.y + 8))
            val = self.item_value(kind)
            if len(val) > 55:
                val = val[:52] + "…"
            self.text(val, 20, AMARILLO if idx == self.sel else GRIS, right=(r.right - 12, r.centery))
        if self.editing:
            ed = pygame.Rect(170, 595, 940, 70)
            self.panel(ed, (0, 0, 0), 255, (VERDE, 2), 10)
            buf = self.editing[1] + "|"
            lines = wrap(buf, self.f[20], ed.w - 24)[-2:]
            for i, ln in enumerate(lines):
                self.text(ln, 20, BLANCO, topleft=(ed.x + 12, ed.y + 8 + i * 28))
            self.text("ENTER guardar · ESC cancelar · Ctrl+V pegar", 20, GRIS, topleft=(170, 572))
        else:
            self.text("↑↓ mover · ←→ cambiar · ENTER editar · SUPR borrar desafío · ESC cerrar",
                      20, GRIS, center=(W // 2, 640))

    def draw(self):
        {"instrucciones": self.draw_instrucciones, "juego": self.draw_game, "menu": self.draw_menu}[self.state]()

    def run(self):
        clock = pygame.time.Clock()
        while self.running:
            dt = clock.tick(60) / 1000
            for e in pygame.event.get():
                self.handle(e)
            self.update(dt)
            self.draw()
            pygame.display.flip()
        save_config(self.cfg)
        pygame.quit()


if __name__ == "__main__":
    Game().run()
