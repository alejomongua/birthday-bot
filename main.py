import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv
import google.generativeai as genai
from utils import (
    Config, setup_logging, process_birthdays
)

def get_google_service(api_name, api_version, scopes, token_path):
    """Obtiene servicio de Google API usando OAuth2 para autenticación local."""
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', scopes
            )
            creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return build(api_name, api_version, credentials=creds)

def main():
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
        ['https://www.googleapis.com/auth/spreadsheets.readonly'],
        'token.json'
    )
    gmail_service = get_google_service(
        'gmail', 'v1',
        ['https://www.googleapis.com/auth/gmail.send'],
        'token_gmail.json'
    )

    # Procesar cumpleaños
    from_email = os.getenv('YOUR_EMAIL')
    process_birthdays(sheets_service, gmail_service, config, from_email)

if __name__ == '__main__':
    main()
