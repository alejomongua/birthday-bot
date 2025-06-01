import os
import datetime
import base64
import pandas as pd

from email.message import EmailMessage

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

import google.generativeai as genai
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# --- Configuración General de Sheets ---
SCOPES_SHEETS = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
RANGE_NAME    = 'Hoja1!A:D'
# --- Configuración de Gmail API ---
SCOPES_GMAIL = ['https://www.googleapis.com/auth/gmail.send']  # Solo permiso de envío
  # (sin acceso a bandeja) :contentReference[oaicite:6]{index=6}

# --- Configuración de Gemini ---
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)


def authenticate_google_sheets():
    """Autentica con Google Sheets API y devuelve el servicio."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES_SHEETS)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES_SHEETS)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('sheets', 'v4', credentials=creds)


def read_google_sheet(service):
    """Lee datos de Google Sheets en un DataFrame."""
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME
        ).execute()
        vals = result.get('values', [])
        if not vals:
            return pd.DataFrame()
        headers = [h.strip().lower() for h in vals[0]]
        return pd.DataFrame(vals[1:], columns=headers)
    except Exception as e:
        print(f"Error al leer Google Sheet: {e}")
        return pd.DataFrame()


def authenticate_gmail():
    """Autentica con Gmail API y devuelve el servicio de envío."""
    creds = None
    token_path = 'token_gmail.json'
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES_GMAIL)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES_GMAIL)
            creds = flow.run_local_server(port=0)  # primera vez abre navegador :contentReference[oaicite:7]{index=7}
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)


def get_today_birthdays(df):
    """Devuelve lista de filas con cumpleaños hoy (formato YYYY/MM/DD)."""
    today = datetime.date.today()
    if 'fecha de nacimiento' not in df.columns:
        return []
    result = []
    for _, row in df.iterrows():
        try:
            y, m, d = map(int, str(row['fecha de nacimiento']).split('/'))
            if m == today.month and d == today.day:
                result.append(row.to_dict())
        except:
            pass
    return result


def generate_birthday_message(person_data):
    """Genera un mensaje de cumpleaños con Gemini."""
    nombre = person_data.get('nombre', 'cumpleañero/a')
    prompt = (
        f"Genera un mensaje de cumpleaños corto y cálido para {nombre}. "
        "No incluyas firma ni nombre del remitente."
    )
    try:
        model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        return model.generate_content(prompt).text.strip()
    except:
        return f"¡Feliz cumpleaños, {nombre}! 🎉"


def send_email(to_email, subject, message_body):
    """
    Envía correo usando Gmail API:
    - Construye EmailMessage.
    - Codifica a base64url.
    - Llama a messages.send(userId='me', body={'raw': raw}).
    """ 
    service = authenticate_gmail()
    email_msg = EmailMessage()
    email_msg.set_content(message_body)
    email_msg['To'] = to_email
    email_msg['From'] = os.getenv('YOUR_EMAIL')
    email_msg['Subject'] = subject

    raw = base64.urlsafe_b64encode(email_msg.as_bytes()).decode()
    service.users().messages().send(userId='me', body={'raw': raw}).execute()
    print(f"Correo enviado a {to_email}")  # vía API :contentReference[oaicite:8]{index=8}


def main():
    print("Iniciando bot de cumpleaños...")
    sheets_svc = authenticate_google_sheets()
    df = read_google_sheet(sheets_svc)
    if df.empty:
        print("No hay datos o error al leer la hoja.")
        return

    birthdays = get_today_birthdays(df)
    if not birthdays:
        print("No hay cumpleaños hoy.")
        return

    print(f"Hoy hay {len(birthdays)} cumpleaños.")
    for person in birthdays:
        correo = person.get('correo electrónico')
        nombre = person.get('nombre', 'N/A')
        if not correo:
            print(f"Saltando {nombre}, sin correo.")
            continue

        msg = generate_birthday_message(person)
        subject = f"¡Feliz Cumpleaños, {nombre}!"
        send_email(correo, subject, msg)
        print("-" * 30)

    print("Bot finalizado.")


if __name__ == '__main__':
    main()
