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
MORADO = (75, 0, 130)
CIAN = (0, 255, 255)

ANCHO, ALTO = 1280, 720
pantalla = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Karaoke Desafío Musical")

# Fuentes
fuente_titulo = pygame.font.SysFont("Arial", 50, bold=True)
fuente_boton = pygame.font.SysFont("Arial", 24, bold=True)
fuente_texto = pygame.font.SysFont("Arial", 30, bold=True)
fuente_pequena = pygame.font.SysFont("Arial", 20, bold=True)
fuente_puntaje = pygame.font.SysFont("Arial", 60, bold=True)
fuente_calificador = pygame.font.SysFont("Arial", 120, bold=True)

# Variables globales
config = {
    "puntaje_azul": 0,
    "puntaje_rojo": 0,
    "numero_cancion": 1,
    "tiempo_actual": 0,
    "tiempo_total": 15,
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

# --- BUCLE PRINCIPAL ---
def juego():
    cargando = True
    reloj = pygame.time.Clock()
    
    boton_alexa = Boton(250, 50, 150, 50, "Leer Alexa", AZUL, activar_alexa)
    boton_sig = Boton(650, 50, 100, 50, "Siguiente", AZUL, lambda: config.update({"numero_cancion": config["numero_cancion"] + 1}))

    while cargando:
        dt = reloj.tick(60) / 1000.0

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                guardar_config()
                pygame.quit()
                sys.exit()

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

                if evento.key == pygame.K_m:
                    config["menu_activo"] = not config["menu_activo"]
                
                if config["menu_activo"]:
                    if evento.key == pygame.K_3: 
                        config["editando_texto"] = True
                        config["texto_edicion"] = config["frase_calificacion"]
                    elif evento.key == pygame.K_7: 
                        pygame.quit()
                        sys.exit()
                    continue

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
        # DIBUJADO DEL SKIN BASE (Ya no depende de imágenes)
        # ==========================================
        
        # Fondo general oscuro
        pantalla.fill((20, 10, 40))

        # Escenario de fondo (Simulación)
        pygame.draw.rect(pantalla, (50, 20, 80), (100, 250, 1080, 450), border_radius=20)
        pygame.draw.circle(pantalla, (0, 100, 200), (640, 450), 150) # Luces del centro
        pygame.draw.circle(pantalla, (100, 0, 200), (640, 450), 100)

        # Panel Superior (Alexa)
        pygame.draw.rect(pantalla, (10, 30, 60), (200, 20, 880, 100), border_radius=15)
        pygame.draw.rect(pantalla, CIAN, (200, 20, 880, 100), 3, border_radius=15)
        
        # Caja de Tiempo
        pygame.draw.rect(pantalla, (60, 0, 0), (500, 130, 280, 40), border_radius=10)
        pygame.draw.rect(pantalla, ROJO, (500, 130, 280, 40), 2, border_radius=10)
        txt_t = fuente_boton.render("TIEMPO", True, BLANCO)
        pantalla.blit(txt_t, (590, 135))

        # Panel Equipo Rojo (Izquierda)
        pygame.draw.rect(pantalla, (60, 10, 20), (20, 130, 250, 150), border_radius=15)
        pygame.draw.rect(pantalla, (255, 50, 100), (20, 130, 250, 150), 3, border_radius=15)
        txt_eq_r = fuente_boton.render("EQUIPO ROJO", True, BLANCO)
        pantalla.blit(txt_eq_r, (60, 140))

        # Panel Equipo Azul (Derecha)
        pygame.draw.rect(pantalla, (10, 30, 60), (1010, 130, 250, 150), border_radius=15)
        pygame.draw.rect(pantalla, (50, 150, 255), (1010, 130, 250, 150), 3, border_radius=15)
        txt_eq_a = fuente_boton.render("EQUIPO AZUL", True, BLANCO)
        pantalla.blit(txt_eq_a, (1050, 140))

        # Botones
        boton_alexa.dibujar(pantalla)
        boton_sig.dibujar(pantalla)

        # Sintetizador animado
        if config["tiempo_actual"] > 0:
            for i in range(5):
                altura = random.randint(10, 40) if pygame.time.get_ticks() % 200 < 100 else 10
                pygame.draw.rect(pantalla, CIAN, (900 + i*15, 60, 10, altura))
                pygame.draw.rect(pantalla, CIAN, (900 + i*15, 60 - altura, 10, altura))

        # Marcadores
        color_rojo = AMARILLO if config["editando_puntaje"] == "rojo" else BLANCO
        color_azul = AMARILLO if config["editando_puntaje"] == "azul" else BLANCO
        
        txt_rojo = fuente_puntaje.render(str(config["puntaje_rojo"]), True, color_rojo)
        pantalla.blit(txt_rojo, (120, 190))
        
        txt_azul = fuente_puntaje.render(str(config["puntaje_azul"]), True, color_azul)
        pantalla.blit(txt_azul, (1110, 190))

        # Número de canción
        txt_num = fuente_titulo.render(str(config["numero_cancion"]), True, BLANCO)
        pantalla.blit(txt_num, (450, 40))

        # Barra de tiempo
        if config["tiempo_actual"] > 0:
            porcentaje = config["tiempo_actual"] / config["tiempo_total"]
            ancho_barra = int(280 * porcentaje)
            pygame.draw.rect(pantalla, GRIS, (500, 175, 280, 10))
            pygame.draw.rect(pantalla, ROJO, (500, 175, ancho_barra, 10))

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

        # Menú Principal (M)
        if config["menu_activo"]:
            pygame.draw.rect(pantalla, (20, 20, 20), (150, 100, 980, 500))
            pygame.draw.rect(pantalla, BLANCO, (150, 100, 980, 500), 3)
            
            opciones = [
                "[1] Logotipos (Próximamente)",
                "[2] Cambiar Fondo (Próximamente)",
                "[3] Editar Frase de Calificación",
                "[4] Sonidos (Próximamente)",
                "[5] Visualización (Próximamente)",
                "[6] Configurar Teclado",
                "[7] CERRAR PROGRAMA",
                "[8] Editor de Canciones y Textos"
            ]
            
            for i, txt in enumerate(opciones):
                color_txt = ROJO if i == 6 else BLANCO
                if i == 7: color_txt = AMARILLO
                render = fuente_boton.render(txt, True, color_txt)
                pantalla.blit(render, (200, 150 + i*50))

            if config["editando_texto"]:
                pygame.draw.rect(pantalla, (0, 0, 100), (200, 580, 880, 60))
                pygame.draw.rect(pantalla, AMARILLO, (200, 580, 880, 60), 2)
                txt_actual = fuente_boton.render(config["texto_edicion"] + "|", True, AMARILLO)
                pantalla.blit(txt_actual, (220, 590))

        pygame.display.flip()

if __name__ == "__main__":
    cargar_config()
    juego()
