# 🎂 Bot de Correos de Cumpleaños

Un bot automatizado en Python que envía correos electrónicos personalizados de cumpleaños a contactos desde una hoja de cálculo de Google utilizando la API de Gmail y mensajes generados por IA.

## Características

- 🔄 Verificaciones diarias de cumpleaños en una hoja de Google
- 🤖 Mensajes personalizados de cumpleaños generados por IA usando Google Gemini
- ✉️ Envío automatizado de correos a través de la API de Gmail
- 🔐 Autenticación segura OAuth2 con servicios de Google

## Requisitos Previos

- Python 3.7+
- Cuenta de Google con acceso a Sheets y Gmail
- Clave API de Gemini (desde Google AI Studio)
- Proyecto de Google Cloud con APIs de Sheets y Gmail habilitadas

## Instrucciones de Configuración

1. **Clona el repositorio**

2. **Crea un entorno virtual e instala las dependencias**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # En Windows
   # source venv/bin/activate  # En macOS/Linux
   pip install -r requirements.txt
   ```

3. **Configura el Proyecto de Google Cloud**
   - Crea un proyecto en la [Consola de Google Cloud](https://console.cloud.google.com/)
   - Habilita las APIs de Google Sheets y Gmail
   - Crea credenciales OAuth (tipo aplicación de escritorio)
   - Descarga las credenciales como `credentials.json` y colócalas en la raíz del proyecto

4. **Configura las variables de entorno**
   - Copia el archivo `.env.example` a `.env`
   - Rellena con tu ID de hoja de cálculo, clave API de Gemini y dirección de Gmail

5. **Primera autenticación**
   - Ejecuta el script una vez para autenticarte con Google
   - Esto abrirá ventanas del navegador para confirmar el acceso
   - Los tokens de autenticación se guardarán para uso futuro

## Configuración

Edita el archivo `.env`:

```
SPREADSHEET_ID="tu_id_de_hoja_de_google"
GEMINI_API_KEY="tu_clave_api_de_gemini"
YOUR_EMAIL="tu_direccion_de_gmail"
```

## Formato de la Hoja de Google

Tu hoja de Google debe tener estas columnas:
- `nombre` - Nombre de la persona
- `parentezco` - Parentezco con la persona
- `fecha de nacimiento` - Fecha de nacimiento (formato: YYYY/MM/DD)
- `correo electrónico` - Dirección de correo electrónico

El nombre de la hoja debe ser "Hoja1" (sin espacios). Por defecto el nombre viene con espacio, así que hay que cambiarlo

## Uso

Ejecuta el script diariamente para verificar y enviar correos de cumpleaños:

```bash
python main.py
```

Para ejecución automatizada, considera configurar un cron job (Linux/Mac) o el Programador de tareas (Windows).

## Notas de Seguridad

- Nunca subas tus archivos de credenciales al control de versiones
- El archivo `.gitignore` excluye archivos sensibles
- Esta aplicación solicita permisos mínimos (solo lectura para Sheets, solo envío para Gmail)
- Los tokens se almacenan localmente en `token.json` y `token_gmail.json`

## Licencia

MIT
