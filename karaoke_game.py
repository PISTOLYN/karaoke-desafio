import pygame
import asyncio
import edge_tts
import threading
import sys
import json
import os
import random
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
GRIS = (50, 50, 50)

ANCHO, ALTO = 1280, 720
pantalla = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Karaoke Desafío Musical")

# Fuentes
fuente_titulo = pygame.font.SysFont("Arial", 40, bold=True)
fuente_boton = pygame.font.SysFont("Arial", 26, bold=True)
fuente_opcion = pygame.font.SysFont("Arial", 24, bold=True) # Texto amarillo
fuente_num_opcion = pygame.font.SysFont("Arial", 28, bold=True) # Números rojos
fuente_texto = pygame.font.SysFont("Arial", 30, bold=True)
fuente_pequena = pygame.font.SysFont("Arial", 20, bold=True)
fuente_puntaje = pygame.font.SysFont("Arial", 65, bold=True)
fuente_calificador = pygame.font.SysFont("Arial", 120, bold=True)

# Variables globales
config = {
    "puntaje_azul": 0,
    "puntaje_rojo": 0,
    "numero_cancion": 1,
    "tiempo_actual": 0,
    "tiempo_total": 15,
    "fondo_actual": "assets/fondo_juego.png",
    "frase_calificacion": "El jurado dice:",
    "editando_texto": False,
    "texto_edicion": "",
    "editando_puntaje": None, 
    "menu_activo": False,
    "calificando": False,
    "valor_calificacion": 0,
    "tiempo_animacion": 0
}

# --- SISTEMA DE VOZ ALEXA ---
def hablar_alexa(texto, es_calificacion=False):
    async def generar_audio():
        voz = "es-ES-ElviraNeural"
        comunicacion = edge_tts.Communicate(texto, voz)
        await comunicacion.save("alexa_temp.mp3")
    asyncio.run(generar_audio())
    try:
        pygame.mixer.music.load("alexa_temp.mp3")
        pygame.mixer.music.play()
        if not es_calificacion:
            config["tiempo_actual"] = config["tiempo_total"]
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    except Exception as e:
        print(f"Error de voz: {e}")

def activar_alexa():
    texto = f"Alexa, di la canción número {config['numero_cancion']}"
    threading.Thread(target=hablar_alexa, args=(texto,)).start()

def calificar_aleatorio():
    config["calificando"] = True
    config["tiempo_animacion"] = 3.0
    config["valor_calificacion"] = random.randint(0, 10)
    frase = f"{config['frase_calificacion']} {config['valor_calificacion']} puntos"
    threading.Thread(target=hablar_alexa, args=(frase, True)).start()

def guardar_config():
    with open("config.json", "w") as f:
        json.dump(config, f)

def cargar_config():
    global config
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            config.update(json.load(f))

# --- CLASE BOTÓN (Para el juego, no para el menú) ---
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

# --- BUCLE PRINCIPAL ---
def juego():
    cargando = True
    reloj = pygame.time.Clock()
    
    boton_alexa = Boton(500, 50, 120, 40, "Leer Alexa", AZUL, activar_alexa)
    boton_sig = Boton(630, 50, 100, 40, "Siguiente", AZUL, lambda: config.update({"numero_cancion": config["numero_cancion"] + 1}))

    while cargando:
        dt = reloj.tick(60) / 1000.0

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                guardar_config()
                pygame.quit()
                sys.exit()

            if evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 1 and not config["menu_activo"]:
                    boton_alexa.click(evento.pos)
                    boton_sig.click(evento.pos)

            if evento.type == pygame.KEYDOWN:
                if config["editando_puntaje"]:
                    if evento.key == pygame.K_RETURN:
                        try:
                            nuevo_valor = int(config["texto_edicion"])
                            config[f"puntaje_{config['editando_puntaje']}"] = nuevo_valor
                        except: pass
                        config["editando_puntaje"] = None
                    elif evento.key == pygame.K_BACKSPACE:
                        config["texto_edicion"] = config["texto_edicion"][:-1]
                    elif evento.unicode.isdigit():
                        config["texto_edicion"] += evento.unicode
                    continue

                if config["editando_texto"]:
                    if evento.key == pygame.K_RETURN:
                        config["frase_calificacion"] = config["texto_edicion"]
                        config["editando_texto"] = False
                    elif evento.key == pygame.K_BACKSPACE:
                        config["texto_edicion"] = config["texto_edicion"][:-1]
                    elif evento.unicode.isprintable():
                        config["texto_edicion"] += evento.unicode
                    continue

                # --- ABRIR/CERRAR MENÚ ---
                if evento.key == pygame.K_m:
                    config["menu_activo"] = not config["menu_activo"]
                
                if config["menu_activo"]:
                    if evento.key == pygame.K_1: # Skins / Cambiar fondo
                        root = Tk(); root.withdraw()
                        arch = filedialog.askopenfilename(title="Seleccionar Fondo", filetypes=[("Imágenes", "*.png *.jpg")])
                        if arch: config["fondo_actual"] = arch; guardar_config()
                    elif evento.key == pygame.K_3: # Sonidos (Próximamente)
                        pass
                    elif evento.key == pygame.K_4: # Editar preguntas / Frase
                        config["editando_texto"] = True
                        config["texto_edicion"] = config["frase_calificacion"]
                    elif evento.key == pygame.K_5: # Cerrar Menú
                        config["menu_activo"] = False
                    elif evento.key == pygame.K_6: # Apagar PC
                        pygame.quit()
                        sys.exit()
                    continue

                # --- CONTROLES DE JUEGO ---
                if evento.key == pygame.K_c: 
                    calificar_aleatorio()
                elif evento.key == pygame.K_q and config["calificando"]:
                    config["puntaje_rojo"] += config["valor_calificacion"]
                    config["calificando"] = False
                elif evento.key == pygame.K_e and config["calificando"]:
                    config["puntaje_azul"] += config["valor_calificacion"]
                    config["calificando"] = False
                
                if evento.key == pygame.K_F1:
                    config["editando_puntaje"] = "rojo"
                    config["texto_edicion"] = str(config["puntaje_rojo"])
                elif evento.key == pygame.K_F2:
                    config["editando_puntaje"] = "azul"
                    config["texto_edicion"] = str(config["puntaje_azul"])

        if config["tiempo_actual"] > 0:
            config["tiempo_actual"] -= dt
            if config["tiempo_actual"] < 0:
                config["tiempo_actual"] = 0
                
        if config["calificando"] and config["tiempo_animacion"] > 0:
            config["tiempo_animacion"] -= dt
            if int(config["tiempo_animacion"] * 10) % 2 == 0:
                config["valor_calificacion"] = random.randint(0, 10)

        # ==========================================
        # DIBUJADO DEL JUEGO
        # ==========================================
        try:
            fondo_juego = pygame.image.load(config["fondo_actual"])
            fondo_juego = pygame.transform.scale(fondo_juego, (ANCHO, ALTO))
            pantalla.blit(fondo_juego, (0, 0))
        except:
            pantalla.fill(NEGRO)

        if not config["menu_activo"]:
            boton_alexa.dibujar(pantalla)
            boton_sig.dibujar(pantalla)

        # Sintetizador
        if config["tiempo_actual"] > 0:
            for i in range(5):
                altura = random.randint(10, 40) if pygame.time.get_ticks() % 200 < 100 else 10
                pygame.draw.rect(pantalla, (0, 255, 255), (850 + i*15, 60, 10, altura))
                pygame.draw.rect(pantalla, (0, 255, 255), (850 + i*15, 60 - altura, 10, altura))

        # Marcadores
        color_rojo = AMARILLO if config["editando_puntaje"] == "rojo" else BLANCO
        color_azul = AMARILLO if config["editando_puntaje"] == "azul" else BLANCO
        
        txt_rojo = fuente_puntaje.render(str(config["puntaje_rojo"]), True, color_rojo)
        pantalla.blit(txt_rojo, txt_rojo.get_rect(center=(200, 200)))
        
        txt_azul = fuente_puntaje.render(str(config["puntaje_azul"]), True, color_azul)
        pantalla.blit(txt_azul, txt_azul.get_rect(center=(1180, 200)))

        # Número de canción
        txt_num = fuente_titulo.render(str(config["numero_cancion"]), True, BLANCO)
        pantalla.blit(txt_num, (430, 50))

        # Barra de tiempo
        if config["tiempo_actual"] > 0:
            porcentaje = config["tiempo_actual"] / config["tiempo_total"]
            ancho_barra = int(280 * porcentaje)
            pygame.draw.rect(pantalla, (20, 50, 100), (380, 160, 280, 15))
            pygame.draw.rect(pantalla, (50, 150, 255), (380, 160, ancho_barra, 15))

        # Calificador
        if config["calificando"]:
            pygame.draw.rect(pantalla, (0, 0, 0), (400, 250, 480, 250), border_radius=20)
            pygame.draw.rect(pantalla, AMARILLO, (400, 250, 480, 250), 5, border_radius=20)
            
            txt_frase = fuente_boton.render(config["frase_calificacion"], True, BLANCO)
            pantalla.blit(txt_frase, (480, 280))
            
            txt_val = fuente_calificador.render(str(config["valor_calificacion"]), True, AMARILLO)
            pantalla.blit(txt_val, (600, 330))
            
            txt_ins = fuente_pequena.render("Presiona Q (Rojo) o E (Azul) para asignar", True, VERDE)
            pantalla.blit(txt_ins, (450, 460))

        # ==========================================
        # DIBUJADO DEL MENÚ TIPO "100 MEXICANOS"
        # ==========================================
        if config["menu_activo"]:
            # Fondo oscuro semitransparente
            s = pygame.Surface((ANCHO, ALTO))
            s.set_alpha(200)
            s.fill((0, 0, 0))
            pantalla.blit(s, (0, 0))

            # Panel principal
            panel_rect = pygame.Rect(240, 50, 800, 620)
            pygame.draw.rect(pantalla, (10, 30, 60), panel_rect, border_radius=20)
            pygame.draw.rect(pantalla, AMARILLO, panel_rect, 4, border_radius=20)

            # Título
            txt_titulo = fuente_titulo.render("MENU DE CONFIGURACION DE KARAOKE", True, BLANCO)
            pantalla.blit(txt_titulo, txt_titulo.get_rect(center=(ANCHO//2, 90)))

            # Opciones del menú
            opciones = [
                ("1", "SKINS / CAMBIAR FONDO"),
                ("2", "CONFIGURAR TECLADO (PRÓXIMAMENTE)"),
                ("3", "SONIDOS (PRÓXIMAMENTE)"),
                ("4", "EDITAR FRASE DEL JURADO"),
                ("5", "CERRAR MENÚ"),
                ("6", "APAGAR PC")
            ]

            y_offset = 160
            for num, texto in opciones:
                # Botón píldora
                btn_rect = pygame.Rect(280, y_offset, 720, 65)
                pygame.draw.rect(pantalla, (5, 15, 40), btn_rect, border_radius=30)
                
                # Borde del botón (amarillo si es la opción de apagar, azul claro para las demás)
                color_borde = ROJO if num == "6" else (50, 150, 255)
                pygame.draw.rect(pantalla, color_borde, btn_rect, 3, border_radius=30)

                # Círculo del número
                pygame.draw.circle(pantalla, (150, 20, 20), (320, y_offset + 32), 22)
                pygame.draw.circle(pantalla, AMARILLO, (320, y_offset + 32), 22, 2)
                
                # Número
                txt_num = fuente_num_opcion.render(num, True, BLANCO)
                pantalla.blit(txt_num, txt_num.get_rect(center=(320, y_offset + 32)))

                # Texto de la opción
                txt_opc = fuente_opcion.render(texto, True, AMARILLO)
                pantalla.blit(txt_opc, (370, y_offset + 18))

                y_offset += 80

            # Instrucciones inferiores
            txt_inst = fuente_pequena.render("Presiona el número de la opción que deseas", True, BLANCO)
            pantalla.blit(txt_inst, txt_inst.get_rect(center=(ANCHO//2, 650)))

            # Caja de edición de texto (si está activa)
            if config["editando_texto"]:
                pygame.draw.rect(pantalla, (0, 0, 0), (200, 200, 880, 60))
                pygame.draw.rect(pantalla, AMARILLO, (200, 200, 880, 60), 2)
                txt_actual = fuente_boton.render("Escribe y presiona ENTER: " + config["texto_edicion"] + "|", True, AMARILLO)
                pantalla.blit(txt_actual, (220, 215))

        pygame.display.flip()

if __name__ == "__main__":
    cargar_config()
    if not os.path.exists("assets"): os.makedirs("assets")
    juego()
