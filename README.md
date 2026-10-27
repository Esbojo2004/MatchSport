# 🏆 MatchSport

> Aplicación de escritorio para conectar a deportistas locales por nivel, deporte y horarios de quedada en red local (Wi-Fi).

---

## 🚀 Características

- **👤 Perfiles de Jugador:** Nombre, deportes favoritos (Pádel, Tenis, Fútbol, Running) y nivel de juego (*Principiante, Intermedio, Experto*).
- **⚽ Motor de Emparejamiento:** Filtra y sugiere partidos afines según tus preferencias y nivel.
- **🕒 Coordinación de Horarios:** Pestañas dedicadas para explorar partidos por horas (*Mañana, Tarde, Noche*) y agendar tus quedadas.
- **➕ Creación de Partidos:** Publica partidos con plazas limitadas directamente desde la aplicación.
- **📡 Red Local (Wi-Fi):** Arquitectura Cliente-Servidor con detección automática en red local sin necesidad de configuraciones complejas.
- **🎨 Interfaz Moderna:** Desarrollada con CustomTkinter, con soporte para Modo Oscuro y Modo Claro.

---

## 🛠️ Stack Tecnológico

- **Lenguaje:** Python 3.9+
- **Interfaz Gráfica (GUI):** [CustomTkinter](https://customtkinter.tomschimansky.com/)
- **Servidor Backend:** [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
- **Base de Datos:** SQLite3 (`matchsport.db`)
- **Protocolo de Red:** REST API (HTTP) + Auto-discovery (UDP Broadcast)

---

## 📦 Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/Esbojo2004/matchsport.git
   cd matchsport
   ```

2. Instala las dependencias necesarias:
   ```bash
   pip install -r requirements.txt
   ```

---

## ▶️ Cómo Ejecutar

### 1. Iniciar el Servidor (en el PC anfitrión)
Ejecuta el archivo por lotes o directamente por terminal:
```bash
python servidor.py
```
*(O haz doble clic en `iniciar_servidor.bat`)*

### 2. Iniciar la Aplicación (en tu PC o en cualquier PC del Wi-Fi)
```bash
python "aplicacion inventada.py"
```
*(O haz doble clic en `iniciar_app.bat`)*

La aplicación detectará automáticamente el servidor en la red local y sincronizará los partidos y perfiles en tiempo real.

