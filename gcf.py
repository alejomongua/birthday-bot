import os
import sys
import json
import logging
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import google.generativeai as genai
from utils import (
    Config, process_birthdays
)

from google.cloud import secretmanager
from google.auth.transport.requests import Request

def setup_logging():
    logger = logging.getLogger()       # logger raíz
    logger.setLevel(logging.INFO)      # nivel mínimo INFO

    # Creamos un handler que imprima a stdout
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)

    # (Opcional) Formateador para que veas nivel+mensaje
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    stream_handler.setFormatter(formatter)

    # Reemplazamos **todos** los handlers anteriores por este:
    logger.handlers = [stream_handler]


def get_secret(secret_id):
    """Obtiene un secreto de Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{os.getenv('PROJECT_ID')}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def get_google_service(api_name, api_version, scopes):
    """Obtiene servicio de Google API usando las credenciales apropiadas."""
    if api_name == 'gmail':
        # Para Gmail usamos OAuth
        client_secret = json.loads(get_secret('gmail-client-secret'))
        refresh_token = get_secret('gmail-refresh-token')
        client_id = os.getenv('GMAIL_CLIENT_ID')
        
        creds = Credentials.from_authorized_user_info({
            'client_id': client_id,
            'client_secret': client_secret['installed']['client_secret'],
            'refresh_token': json.loads(refresh_token)['refresh_token'],
            'token_uri': 'https://oauth2.googleapis.com/token'
        }, scopes)
        # Refrescar el token en cada ejecución si hay refresh_token
        if creds and creds.refresh_token:
            creds.refresh(Request())
            # Guardar el nuevo token en Secret Manager
            client = secretmanager.SecretManagerServiceClient()
            parent = f"projects/{os.getenv('PROJECT_ID')}/secrets/gmail-refresh-token"
            payload = creds.to_json().encode("UTF-8")
            client.add_secret_version(
                request={
                    "parent": parent,
                    "payload": {"data": payload}
                }
            )
            logging.debug("Token de Gmail actualizado y guardado en Secret Manager")
    else:
        # Para otros servicios usamos service account
        service_account_info = json.loads(get_secret('birthday-reminder-sa'))
        creds = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=scopes
        )
    return build(api_name, api_version, credentials=creds)

def birthday_reminder(event, context=None):
    """Función principal para Google Cloud Functions."""
    setup_logging()
    # Log de inicio
    logging.debug("Birthday reminder iniciando ejecución")

    # Verificar variables de entorno
    for var in ['PROJECT_ID', 'SPREADSHEET_ID', 'YOUR_EMAIL', 'GMAIL_CLIENT_ID']:
        value = os.getenv(var)
        if not value:
            logging.error(f"Variable de entorno {var} no encontrada")
        else:
            logging.debug(f"Variable {var} encontrada")

    # Configurar APIs
    config = Config()
    config.spreadsheet_id = os.getenv('SPREADSHEET_ID')
    config.range_name = 'Hoja1!A:E'
    genai.configure(api_key=get_secret('gemini-api-key'))

    # Obtener servicios de Google
    sheets_service = get_google_service(
        'sheets', 'v4', 
        ['https://www.googleapis.com/auth/spreadsheets.readonly']
    )
    gmail_service = get_google_service(
        'gmail', 'v1',
        ['https://www.googleapis.com/auth/gmail.send']
    )

    # Procesar cumpleaños
    from_email = os.getenv('YOUR_EMAIL')
    process_birthdays(sheets_service, gmail_service, config, from_email)

    return 'OK'
