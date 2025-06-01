import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv
import google.generativeai as genai
from utils import (
    Config, setup_logging, process_birthdays
)

def get_google_service(api_name, api_version, scopes):
    """Obtiene servicio de Google API usando Application Default Credentials."""
    credentials = service_account.Credentials.from_service_account_info(
        {
            "type": "service_account",
            "project_id": os.getenv('PROJECT_ID'),
            "private_key_id": os.getenv('PRIVATE_KEY_ID'),
            "private_key": os.getenv('PRIVATE_KEY').replace('\\n', '\n'),
            "client_email": os.getenv('CLIENT_EMAIL'),
            "client_id": os.getenv('CLIENT_ID'),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": os.getenv('CLIENT_CERT_URL')
        },
        scopes=scopes
    )
    return build(api_name, api_version, credentials=credentials)

def birthday_reminder(event, context):
    """Función principal para Google Cloud Functions."""
    # Configuración inicial
    load_dotenv()
    setup_logging()

    # Configurar APIs
    config = Config()
    config.spreadsheet_id = os.getenv('SPREADSHEET_ID')
    config.range_name = 'Hoja1!A:E'
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

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
