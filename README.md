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

1. Crea una cuenta de servicio en Google Cloud Console:
   - Ve a IAM & Admin > Service Accounts
   - Crea una nueva cuenta de servicio
   - Asigna los siguientes roles:
     * Gmail API > Gmail Send
     * Google Sheets API > Sheets Viewer

2. Genera una clave JSON para la cuenta de servicio:
   - Selecciona la cuenta de servicio creada
   - Ve a la pestaña "Keys"
   - Click en "Add Key" > "Create New Key"
   - Selecciona formato JSON
   - Guarda el archivo como `service-account.json` en la raíz del proyecto
   (No te preocupes, este archivo está en .gitignore)

3. Configura el archivo .env con las variables necesarias:
   ```
   SPREADSHEET_ID=tu_id_de_hoja_de_calculo
   YOUR_EMAIL=tu_correo@gmail.com
   GEMINI_API_KEY=tu_api_key_de_gemini
   ```

4. Ejecuta el script de deploy:
   ```bash
   python deploy.py
   ```

El script automáticamente:
- Crea una carpeta temporal para el deploy
- Lee las credenciales de service-account.json
- Configura todas las variables de entorno necesarias
- Crea o actualiza la función en Google Cloud Functions (si ya existe una función con el mismo nombre, la actualiza)
- Crea o actualiza el topic de Pub/Sub
- Configura o actualiza un Cloud Scheduler para ejecución diaria a las 8:00 AM
- Limpia los archivos temporales

Nota: Puedes ejecutar el script múltiples veces para actualizar la función. El script:
- Actualizará la función existente si ya existe
- Reutilizará el topic de Pub/Sub si ya existe
- Actualizará el Cloud Scheduler job si ya existe

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
