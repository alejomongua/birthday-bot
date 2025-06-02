import os
import datetime
import base64
import logging
import pandas as pd
from email.mime.text import MIMEText
from base64 import urlsafe_b64encode
import google.generativeai as genai

class Config:
    """Clase para mantener la configuración de la aplicación."""
    def __init__(self):
        self.spreadsheet_id = None
        self.range_name = None

def setup_logging():
    """Configura el sistema de logging."""
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    is_cloud_function = bool(os.getenv('FUNCTION_TARGET'))

    handlers = [logging.StreamHandler()]
    if not is_cloud_function:
        handlers.append(logging.FileHandler('birthday_bot.log'))

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format='%(asctime)s - %(levelname)s - %(message)s' if not is_cloud_function else '%(levelname)s - %(message)s',
        handlers=handlers
    )

def get_today_birthdays(df):
    """Devuelve lista de filas con cumpleaños hoy (formato YYYY/MM/DD o MM/DD)."""
    today = datetime.date.today()
    if 'fecha de nacimiento' not in df.columns:
        return []
    result = []
    for _, row in df.iterrows():
        splitted_date = str(row['fecha de nacimiento']).split('/')
        year = None
        if len(splitted_date) == 3:  # Formato YYYY/MM/DD
            year, month, day = map(int, splitted_date)
        elif len(splitted_date) == 2:  # Formato MM/DD
            month, day = map(int, splitted_date)
        else:
            logging.info(f"Formato de fecha no válido: {row['fecha de nacimiento']}")
            continue  # Formato no válido
        if month == today.month and day == today.day:
            current_row = row.to_dict()
            if year is not None:
                current_row['edad'] = today.year - year
            result.append(current_row)

    return result

def generate_birthday_message(person_data):
    """Genera un mensaje de cumpleaños con Gemini."""
    nombre = person_data.get('nombre')
    edad = person_data.get('edad')
    parentesco = person_data.get('parentesco')
    genero = person_data.get('genero')
    if not parentesco:
        parentesco = 'conocido/a'
    if genero:
        msg_genero = f" (género {genero})"
    if edad:
        msg_edad = f" que cumple {edad} años"
    prompt = (
        f"Genera un mensaje de cumpleaños corto y cálido para {nombre}{msg_genero}{msg_edad}. "
        f"{nombre} es mi: {parentesco}. "
        "No incluyas firma ni nombre del remitente."
    )
    try:
        model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        logging.debug(f"Prompt enviado a Gemini: {prompt}")
        response = model.generate_content(prompt).text.strip()
        logging.debug(f"Respuesta recibida de Gemini: {response}")
        return response
    except Exception as e:
        logging.exception("Error al generar mensaje con Gemini")
        return f"¡Feliz cumpleaños, {nombre}! 🎉"

def read_sheet_data(service, config):
    """Lee datos de Google Sheets en un DataFrame."""
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=config.spreadsheet_id, range=config.range_name
        ).execute()
        vals = result.get('values', [])
        if not vals:
            return pd.DataFrame()
        headers = [h.strip().lower() for h in vals[0]]
        return pd.DataFrame(vals[1:], columns=headers)
    except Exception as e:
        logging.exception("Error al leer Google Sheet")
        return pd.DataFrame()

def send_birthday_email(service, to_email, subject, message_body, from_email):
    """Envía correo usando Gmail API con OAuth."""
    message = MIMEText(message_body)
    message['to'] = to_email
    message['from'] = from_email
    message['subject'] = subject

    encoded_message = urlsafe_b64encode(message.as_bytes()).decode()
    
    try:
        service.users().messages().send(
            userId='me',
            body={'raw': encoded_message}
        ).execute()
        logging.info(f"Correo enviado a {to_email}")
    except Exception as error:
        logging.error(f'Ocurrió un error al enviar el correo: {error}')
        raise

def process_birthdays(sheets_service, gmail_service, config, from_email):
    """Procesa los cumpleaños del día y envía los correos."""
    logging.info("Iniciando procesamiento de cumpleaños")
    
    df = read_sheet_data(sheets_service, config)
    if df.empty:
        logging.info("No hay datos o error al leer la hoja.")
        return

    logging.info(f"Datos leídos exitosamente de Google Sheets: {len(df)} filas")
    birthdays = get_today_birthdays(df)
    if not birthdays:
        logging.info("No hay cumpleaños hoy.")
        return

    logging.info(f"Hoy hay {len(birthdays)} cumpleaños:")
    for person in birthdays:
        correo = person.get('correo electrónico')
        nombre = person.get('nombre')
        if not correo or not nombre:
            logging.info(f"Saltando {nombre}, sin correo.")
            continue

        msg = generate_birthday_message(person)
        subject = f"¡Feliz Cumpleaños, {nombre}!"
        send_birthday_email(gmail_service, correo, subject, msg, from_email)
        logging.info("-" * 30)

    logging.info("Bot finalizado.")
