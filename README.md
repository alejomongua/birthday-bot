# Birthday Reminder Bot

Bot que envía automáticamente mensajes de cumpleaños personalizados usando Google Sheets, Gmail y Gemini.

## Configuración Local

1. Crea un proyecto en Google Cloud Console y habilita las siguientes APIs:
   - Google Sheets API
   - Gmail API

2. Crea credenciales OAuth2:
   - Ve a "APIs & Services > Credentials"
   - Crea un "OAuth 2.0 Client ID"
   - Descarga el archivo JSON y guárdalo como `credentials.json` en la raíz del proyecto

3. Crea un archivo `.env` con las siguientes variables:
   ```
   SPREADSHEET_ID=tu_id_de_hoja_de_calculo
   YOUR_EMAIL=tu_correo@gmail.com
   GEMINI_API_KEY=tu_api_key_de_gemini
   ```

4. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

5. Ejecuta el bot:
   ```bash
   python main.py
   ```

## Configuración en Google Cloud Functions

1. Instala y configura Google Cloud SDK:
   - [Instrucciones de instalación de gcloud](https://cloud.google.com/sdk/docs/install)
   - Verifica la instalación: `gcloud --version`
   - Inicia sesión: `gcloud auth login`

2. Habilita las APIs necesarias:
   ```bash
   gcloud services enable cloudfunctions.googleapis.com \
       run.googleapis.com \
       cloudbuild.googleapis.com \
       eventarc.googleapis.com \
       cloudscheduler.googleapis.com \
       secretmanager.googleapis.com
   ```

3. Crea una cuenta de servicio en Google Cloud Console:
   - Ve a IAM & Admin > Service Accounts
   - Crea una nueva cuenta de servicio
   - Asigna el rol Owner
   - Importante: Abre la hoja de cálculo y compártela con el email de la cuenta de servicio 
     (es el campo client_email en service-account.json) dándole permisos de Lector

4. Genera una clave JSON para la cuenta de servicio:
   - Selecciona la cuenta de servicio creada
   - Ve a la pestaña "Keys"
   - Click en "Add Key" > "Create New Key"
   - Selecciona formato JSON
   - Guarda el archivo como `service-account.json` en la raíz del proyecto
   (No te preocupes, este archivo está en .gitignore)

5. Configura el archivo .env con las variables necesarias:
   ```
   SPREADSHEET_ID=tu_id_de_hoja_de_calculo
   YOUR_EMAIL=tu_correo@gmail.com
   GEMINI_API_KEY=tu_api_key_de_gemini
   ```

6. Ejecuta el script de deploy:
   ```bash
   python deploy.py
   ```

El script automáticamente:
- Crea una carpeta temporal para el deploy
- Lee el archivo service-account.json
- Configura Secret Manager:
  * Crea un secreto llamado 'birthday-reminder-sa'
  * Almacena las credenciales del service account
  * Configura los permisos necesarios
- Configura variables de entorno no sensibles
- Crea o actualiza la función en Google Cloud Functions
- Crea o actualiza el topic de Pub/Sub
- Configura o actualiza un Cloud Scheduler
- Limpia los archivos temporales

## Configuración de Recursos

Por defecto, la función se despliega con:
- 512MB de memoria (configurable con --memory)
- 1 CPU (configurable con --cpu)
- Timeout de 60 segundos (configurable con --timeout)

Si necesitas ajustar estos valores, modifica los flags en el script deploy.py:
```bash
--memory 512MB     # Valores disponibles: 128MB, 256MB, 512MB, 1024MB, etc
--cpu 1            # Número de CPUs
--timeout 540s     # Tiempo máximo de ejecución en segundos
```

Nota: Puedes ejecutar el script múltiples veces para actualizar la función. El script:
- Actualizará la función existente si ya existe
- Reutilizará el topic de Pub/Sub si ya existe
- Actualizará el Cloud Scheduler job si ya existe

## Pruebas y Monitoreo

Para probar la función manualmente:
```bash
# Publica un mensaje en el topic para ejecutar la función
gcloud pubsub topics publish birthday-reminder --message="Test run"
```

Para ver los logs de la función, tienes varias opciones:

1. En la terminal:
   ```bash
   # Ver todos los logs (incluye logs de sistema y tus logging.info)
   gcloud functions logs read birthday-reminder --region us-central1

   # Ver solo los logs más recientes
   gcloud functions logs read birthday-reminder --region us-central1 --limit=50

   # Ver logs en tiempo real mientras ejecutas la función
   gcloud functions logs tail birthday-reminder --region us-central1

   # Filtrar solo tus mensajes de logging.info
   gcloud functions logs read birthday-reminder --region us-central1 --filter="textPayload:birthday"
   ```

2. En la consola web de GCP:
   - Ve a [Cloud Functions](https://console.cloud.google.com/functions)
   - Selecciona la función birthday-reminder
   - Ve a la pestaña "Logs"
   - Usa los filtros superiores para:
     * Ver solo cierto rango de tiempo
     * Filtrar por nivel de log (INFO, ERROR, etc.)
     * Buscar texto específico en los mensajes

## Estructura de Google Sheets

La hoja de cálculo debe tener las siguientes columnas:
- nombre
- correo electrónico
- fecha de nacimiento (formato: YYYY/MM/DD o MM/DD)
- parentezco

## Configuración de Logging

- Por defecto, el nivel de logging es INFO
- Puedes cambiar el nivel usando la variable de entorno LOG_LEVEL
- En Cloud Functions, los logs se envían automáticamente a Cloud Logging
- En local, además de la consola se genera un archivo birthday_bot.log

## Estructura del Código

- `main.py`: Ejecución local con autenticación OAuth2
- `gcf.py`: Código para Google Cloud Functions con autenticación de cuenta de servicio
- `utils.py`: Funcionalidad común compartida entre ambos entornos
