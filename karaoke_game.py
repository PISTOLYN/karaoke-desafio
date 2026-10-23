import pygame
import asyncio
import edge_tts
import threading
import sys
import json
import os
import time
from tkinter import Tk, filedialog

# --- CONFIGURACIÓN INICIAL ---
pygame.init()
pygame.mixer.init()

BLANCO = (255, 255, 255)
NEGRO = (0, 0, 0)
ROJO = (255, 0, 0)
AZUL = (0, 0, 255)
VERDE = (0, 255, 0)
AMARILLO = (255, 255, 0)

ANCHO, ALTO = 1280, 720
pantalla = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Karaoke Desafío Musical")

# Fuentes
fuente_titulo = pygame.font.SysFont("Arial", 50, bold=True)
fuente_boton = pygame.font.SysFont("Arial", 24, bold=True)
fuente_texto = pygame.font.SysFont("Arial", 30, bold=True)
fuente_pequena = pygame.font.SysFont("Arial", 18, bold=True)
fuente_puntaje = pygame.font.SysFont("Arial", 55, bold=True) # Tamaño ajustado para que quepa bien

config = {
    "modo_pulsadores": False,
    "puntaje_azul": 0,
    "puntaje_rojo": 0,
    "numero_cancion": 1,
    "tiempo_actual": 0,
    "ruta_mp3": "",
    "tecla_play": pygame.K_SPACE,
    "texto_alexa": "Alexa, di la canción número 1",
    "editando": False,
    "texto_edicion": "",
    "fondo_actual": "assets/fondo_juego.png",
    "logo_karaoke": "assets/logo_karaoke.png",
    "logo_desafios": "assets/logo_desafios.png",
    "menu_puntaje": None, 
    "valor_puntaje": 0
}

# --- SISTEMA DE VOZ ALEXA (Edge TTS) ---
def hablar_alexa(texto):
    async def generar_audio():
        voz = "es-ES-ElviraNeural"
        comunicacion = edge_tts.Communicate(texto, voz)
        await comunicacion.save("alexa_temp.mp3")
    asyncio.run(generar_audio())
    try:
        pygame.mixer.music.load("alexa_temp.mp3")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    except Exception as e:
        print(f"Error al reproducir la voz: {e}")

def activar_alexa():
    config["tiempo_actual"] = 15
    ruta_texto = "textos_alexa/alexa.txt"
    if os.path.exists(ruta_texto):
        with open(ruta_texto, "r", encoding="utf-8") as f:
            config["texto_alexa"] = f.read().strip()
    hilo = threading.Thread(target=hablar_alexa, args=(config["texto_alexa"],))
    hilo.start()

# --- FUNCIONES DE AUDIO MP3 ---
def cargar_mp3_desde_carpeta():
    ruta_pista = "pistas/pista.mp3"
    if os.path.exists(ruta_pista):
        config["ruta_mp3"] = ruta_pista
        guardar_config()
        return True
    return False

def reproducir_reiniciar_musica():
    if not config["ruta_mp3"] or not os.path.exists(config["ruta_mp3"]):
        if not cargar_mp3_desde_carpeta():
            print("No hay pista MP3 en la carpeta 'pistas'.")
            return
    pygame.mixer.music.stop()
    pygame.mixer.music.load(config["ruta_mp3"])
    pygame.mixer.music.play()

# --- CLASE BOTÓN ---
class Boton:
    def __init__(self, x, y, w, h, texto, color, accion):
        self.rect = pygame.Rect(x, y, w, h)
        self.texto = texto
        self.color = color
        self.accion = accion
    def dibujar(self, superficie):
        pygame.draw.rect(superficie, self.color, self.rect, border_radius=10)
        pygame.draw.rect(superficie, BLANCO, self.rect, 3, border_radius=10)
        texto_render = fuente_boton.render(self.texto, True, BLANCO)
        texto_rect = texto_render.get_rect(center=self.rect.center)
        superficie.blit(texto_render, texto_rect)
    def click(self, pos):
        if self.rect.collidepoint(pos):
            self.accion()

def accion_cancion():
    config["numero_cancion"] += 1

def guardar_config():
    with open("config.json", "w") as f:
        json.dump(config, f)

def cargar_config():
    global config
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            config.update(json.load(f))

def pantalla_instrucciones():
    cargando = True
    try:
        fondo = pygame.image.load("assets/fondo_instrucciones.jpg")
        fondo = pygame.transform.scale(fondo, (ANCHO, ALTO))
    except:
        fondo = None
    while cargando:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_RETURN:
                    cargando = False
        if fondo:
            pantalla.blit(fondo, (0, 0))
        else:
            pantalla.fill(NEGRO)
        texto = fuente_titulo.render("PRESIONA ENTER PARA COMENZAR", True, AMARILLO)
        pantalla.blit(texto, (ANCHO//2 - texto.get_width()//2, ALTO//2))
        pygame.display.flip()
        pygame.time.Clock().tick(60)

def juego():
    cargando = True
    reloj = pygame.time.Clock()
    
    boton_alexa = Boton(250, 50, 120, 50, "Alexa", AZUL, activar_alexa)
    boton_cancion = Boton(650, 50, 100, 50, "Siguiente", AZUL, accion_cancion)
    
    editando_texto_alexa = False

    while cargando:
        dt = reloj.tick(60) / 1000.0
        
        try:
            fondo_juego = pygame.image.load(config["fondo_actual"])
            fondo_juego = pygame.transform.scale(fondo_juego, (ANCHO, ALTO))
        except:
            fondo_juego = None

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                guardar_config()
                pygame.quit()
                sys.exit()
                
            if evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 1 and config["modo_pulsadores"]:
                    boton_alexa.click(evento.pos)
                    boton_cancion.click(evento.pos)
                    
            if evento.type == pygame.KEYDOWN:
                if config["menu_puntaje"] is not None:
                    if evento.key == pygame.K_UP:
                        config["valor_puntaje"] = min(10, config["valor_puntaje"] + 1)
                    elif evento.key == pygame.K_DOWN:
                        config["valor_puntaje"] = max(0, config["valor_puntaje"] - 1)
                    elif evento.key == pygame.K_RETURN:
                        if config["menu_puntaje"] == 'azul':
                            config["puntaje_azul"] += config["valor_puntaje"]
                        elif config["menu_puntaje"] == 'rojo':
                            config["puntaje_rojo"] += config["valor_puntaje"]
                        config["menu_puntaje"] = None
                        config["valor_puntaje"] = 0
                        guardar_config()
                    elif evento.key == pygame.K_ESCAPE:
                        config["menu_puntaje"] = None
                    continue

                if evento.key == pygame.K_m and not editando_texto_alexa:
                    config["editando"] = not config["editando"]
                
                if config["editando"]:
                    if evento.key == pygame.K_1 and not editando_texto_alexa:
                        config["modo_pulsadores"] = not config["modo_pulsadores"]
                    elif evento.key == pygame.K_2 and not editando_texto_alexa:
                        root = Tk(); root.withdraw()
                        archivo = filedialog.askopenfilename(title="Seleccionar pista MP3", filetypes=[("MP3", "*.mp3")])
                        if archivo: config["ruta_mp3"] = archivo; guardar_config()
                    elif evento.key == pygame.K_3 and not editando_texto_alexa:
                        config["tecla_play"] = evento.key if evento.key != pygame.K_3 else pygame.K_SPACE
                    elif evento.key == pygame.K_4 and not editando_texto_alexa:
                        editando_texto_alexa = True
                        config["texto_edicion"] = config["texto_alexa"]
                    elif evento.key == pygame.K_5 and not editando_texto_alexa:
                        root = Tk(); root.withdraw()
                        archivo = filedialog.askopenfilename(title="Seleccionar Fondo", filetypes=[("Imágenes", "*.png *.jpg *.jpeg")])
                        if archivo: config["fondo_actual"] = archivo; guardar_config()
                    elif evento.key == pygame.K_6 and not editando_texto_alexa:
                        root = Tk(); root.withdraw()
                        archivo = filedialog.askopenfilename(title="Logo Karaoke", filetypes=[("Imágenes", "*.png *.jpg *.jpeg")])
                        if archivo: config["logo_karaoke"] = archivo; guardar_config()
                    elif evento.key == pygame.K_7 and not editando_texto_alexa:
                        root = Tk(); root.withdraw()
                        archivo = filedialog.askopenfilename(title="Logo Desafíos", filetypes=[("Imágenes", "*.png *.jpg *.jpeg")])
                        if archivo: config["logo_desafios"] = archivo; guardar_config()
                    elif editando_texto_alexa:
                        if evento.key == pygame.K_RETURN:
                            config["texto_alexa"] = config["texto_edicion"]
                            editando_texto_alexa = False
                            guardar_config()
                        elif evento.key == pygame.K_ESCAPE:
                            editando_texto_alexa = False
                        elif evento.key == pygame.K_BACKSPACE:
                            config["texto_edicion"] = config["texto_edicion"][:-1]
                        else:
                            if evento.unicode.isprintable() and len(config["texto_edicion"]) < 60:
                                config["texto_edicion"] += evento.unicode
                    elif evento.key == pygame.K_ESCAPE:
                        config["editando"] = False
                else:
                    if evento.key == config["tecla_play"]:
                        reproducir_reiniciar_musica()
                    if evento.key == pygame.K_a:
                        activar_alexa()
                    elif evento.key == pygame.K_s:
                        accion_cancion()
                    elif evento.key == pygame.K_q: 
                        config["menu_puntaje"] = 'rojo'
                        config["valor_puntaje"] = 0
                    elif evento.key == pygame.K_e: 
                        config["menu_puntaje"] = 'azul'
                        config["valor_puntaje"] = 0

        if config["tiempo_actual"] > 0:
            config["tiempo_actual"] -= dt
            if config["tiempo_actual"] < 0:
                config["tiempo_actual"] = 0

        if fondo_juego:
            pantalla.blit(fondo_juego, (0, 0))
        else:
            pantalla.fill(NEGRO)

        try:
            logo_k = pygame.image.load(config["logo_karaoke"])
            logo_k = pygame.transform.scale(logo_k, (200, 80))
            pantalla.blit(logo_k, (20, 20))
            logo_d = pygame.image.load(config["logo_desafios"])
            logo_d = pygame.transform.scale(logo_d, (150, 150))
            pantalla.blit(logo_d, (1110, 20))
        except: pass

        if config["modo_pulsadores"]:
            boton_alexa.dibujar(pantalla)
            boton_cancion.dibujar(pantalla)

        # --- POSICIONES CORREGIDAS ---
        
        # Puntaje Equipo Rojo (Caja Izquierda)
        texto_rojo = fuente_puntaje.render(str(config["puntaje_rojo"]), True, BLANCO)
        # Calculamos el centro de la caja negra izquierda y lo dibujamos ahí
        rect_rojo = texto_rojo.get_rect(center=(180, 190)) 
        pantalla.blit(texto_rojo, rect_rojo)

        # Puntaje Equipo Azul (Caja Derecha)
        texto_azul = fuente_puntaje.render(str(config["puntaje_azul"]), True, BLANCO)
        # Calculamos el centro de la caja negra derecha
        rect_azul = texto_azul.get_rect(center=(1175, 190))
        pantalla.blit(texto_azul, rect_azul)

        # Número de Canción (Junto a Alexa)
        texto_num = fuente_titulo.render(str(config["numero_cancion"]), True, BLANCO)
        # Lo movemos un poco a la derecha y arriba para que no choque con la esfera
        pantalla.blit(texto_num, (500, 50))

        # Tiempo (Debajo del reloj 0:05)
        if config["tiempo_actual"] > 0:
            texto_tiempo = fuente_texto.render(f"TIEMPO: {int(config['tiempo_actual'])}s", True, ROJO)
            # Lo posicionamos justo debajo del reloj azul
            pantalla.blit(texto_tiempo, (360, 155))

        # --- DIBUJAR MENÚ DE PUNTAJE ---
        if config["menu_puntaje"] is not None:
            pygame.draw.rect(pantalla, (0, 0, 0), (400, 200, 480, 300))
            pygame.draw.rect(pantalla, AMARILLO, (400, 200, 480, 300), 5)
            titulo_p = f"PUNTAJE EQUIPO {config['menu_puntaje'].upper()}"
            txt_p = fuente_boton.render(titulo_p, True, BLANCO)
            pantalla.blit(txt_p, (480, 220))
            num_p = fuente_puntaje.render(str(config["valor_puntaje"]), True, AMARILLO)
            pantalla.blit(num_p, (600, 280))
            txt_ins = fuente_pequena.render("Usa FLECHAS Arriba/Abajo y ENTER para confirmar", True, VERDE)
            pantalla.blit(txt_ins, (430, 450))

        # --- DIBUJAR MENÚ DE CONFIGURACIÓN ---
        if config["editando"]:
            pygame.draw.rect(pantalla, (30, 30, 30), (150, 100, 980, 500))
            pygame.draw.rect(pantalla, BLANCO, (150, 100, 980, 500), 3)
            txt_menu = fuente_boton.render("--- MENÚ DE CONFIGURACIÓN (ESC para cerrar) ---", True, AMARILLO)
            pantalla.blit(txt_menu, (200, 120))
            
            modo_txt = "PULSADORES" if config["modo_pulsadores"] else "SIN PULSADORES"
            txt_modo = fuente_boton.render(f"[1] Modo: {modo_txt}", True, BLANCO)
            pantalla.blit(txt_modo, (200, 180))
            txt_mp3 = fuente_boton.render(f"[2] Cargar MP3 Manual (Actual: ...{config['ruta_mp3'][-20:]})", True, BLANCO)
            pantalla.blit(txt_mp3, (200, 230))
            tecla_nombre = pygame.key.name(config["tecla_play"])
            txt_tecla = fuente_boton.render(f"[3] Tecla Play: '{tecla_nombre.upper()}'", True, BLANCO)
            pantalla.blit(txt_tecla, (200, 280))
            txt_alexa_edit = fuente_boton.render(f"[4] Editar texto de Alexa (Actual: \"{config['texto_alexa']}\")", True, BLANCO)
            pantalla.blit(txt_alexa_edit, (200, 330))
            txt_fondo = fuente_boton.render(f"[5] Cambiar Fondo (Actual: ...{config['fondo_actual'][-20:]})", True, BLANCO)
            pantalla.blit(txt_fondo, (200, 380))
            txt_logo1 = fuente_boton.render(f"[6] Cambiar Logo Karaoke (Actual: ...{config['logo_karaoke'][-20:]})", True, BLANCO)
            pantalla.blit(txt_logo1, (200, 430))
            txt_logo2 = fuente_boton.render(f"[7] Cambiar Logo Desafíos (Actual: ...{config['logo_desafios'][-20:]})", True, BLANCO)
            pantalla.blit(txt_logo2, (200, 480))
            
            txt_ayuda = fuente_pequena.render("Atajos: A=Alexa, S=Siguiente, Q=Rojo, E=Azul, Tecla Asignada=Play", True, VERDE)
            pantalla.blit(txt_ayuda, (200, 550))

            if editando_texto_alexa:
                pygame.draw.rect(pantalla, (0, 0, 100), (200, 580, 880, 60))
                pygame.draw.rect(pantalla, AMARILLO, (200, 580, 880, 60), 2)
                texto_visual = config["texto_edicion"] + "|"
                txt_actual = fuente_boton.render(texto_visual, True, AMARILLO)
                pantalla.blit(txt_actual, (220, 590))

        pygame.display.flip()

if __name__ == "__main__":
    cargar_config()
    if not os.path.exists("pistas"): os.makedirs("pistas")
    if not os.path.exists("textos_alexa"): os.makedirs("textos_alexa")
    
    pantalla_instrucciones()
    juego()
