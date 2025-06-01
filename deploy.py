import os
import json
import shutil
from pathlib import Path
import subprocess
from dotenv import load_dotenv

def read_service_account():
    """Lee el archivo de credenciales de service account."""
    with open('service-account.json') as f:
        return json.load(f)

def setup_deploy_folder():
    """Crea y prepara la carpeta para el deploy."""
    # Crear carpeta temporal
    deploy_path = Path('deploy_tmp')
    if deploy_path.exists():
        shutil.rmtree(deploy_path)
    deploy_path.mkdir()

    # Copiar y renombrar archivos necesarios
    shutil.copy2('gcf.py', deploy_path / 'main.py')  # GCF necesita main.py
    shutil.copy2('utils.py', deploy_path / 'utils.py')
    shutil.copy2('requirements.txt', deploy_path / 'requirements.txt')
    
    return deploy_path

def build_env_vars(creds):
    """Construye la cadena de variables de entorno para el comando de deploy."""
    load_dotenv()
    
    # Variables requeridas del .env
    env_vars = {
        'SPREADSHEET_ID': os.getenv('SPREADSHEET_ID'),
        'YOUR_EMAIL': os.getenv('YOUR_EMAIL'),
        'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY'),
        
        # Variables del service account
        'PROJECT_ID': creds['project_id'],
        'PRIVATE_KEY_ID': creds['private_key_id'],
        'PRIVATE_KEY': creds['private_key'],
        'CLIENT_EMAIL': creds['client_email'],
        'CLIENT_ID': creds['client_id'],
        'CLIENT_CERT_URL': creds.get('client_x509_cert_url', '')
    }
    
    # Construir string de variables de entorno
    env_vars_str = ' '.join([
        f'--set-env-vars {key}="{value}"'
        for key, value in env_vars.items()
    ])
    
    return env_vars_str

def create_topic():
    """Crea el topic de Pub/Sub si no existe."""
    # Primero verificamos si el topic existe
    # Usamos --format=json para parsing más confiable
    check_command = 'gcloud pubsub topics list --format=json'
    
    try:
        result = subprocess.run(check_command, shell=True, capture_output=True, text=True)
        topics = json.loads(result.stdout)
        for topic in topics:
            if '/topics/birthday-reminder' in topic['name']:
                print("El topic ya existe, continuando...")
                return True
        print("El topic no existe, creándolo...")
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"Error al verificar topics existentes: {e}")
        return False

    # Si no existe, intentamos crearlo
    create_command = 'gcloud pubsub topics create birthday-reminder'
    try:
        subprocess.run(create_command, shell=True, check=True)
        print("Topic de Pub/Sub creado exitosamente")
        return True
    except subprocess.CalledProcessError as e:
        # Si falla por alguna razón que no sea que ya existe
        print(f"Error al crear el topic: {e}")
        return False

def deploy_function(deploy_path, env_vars):
    """Despliega la función en Google Cloud Functions."""
    deploy_command = (
        f'gcloud functions deploy birthday-reminder '  # nombre de la función en GCP
        f'--gen2 '  # Especificar Gen 2
        f'--runtime python39 '
        f'--region us-central1 '  # Especificar región
        f'--trigger-topic birthday-reminder '
        f'--entry-point birthday_reminder '  # nombre de la función en el código
        f'--source {deploy_path} '
        f'{env_vars}'
    )
    
    print(f"Ejecutando comando de deploy:\n{deploy_command}")
    
    try:
        subprocess.run(deploy_command, shell=True, check=True)
        print("Función desplegada exitosamente")
    except subprocess.CalledProcessError as e:
        print(f"Error al desplegar la función: {e}")
        return False
    
    return True

def create_scheduler():
    """Crea o actualiza el Cloud Scheduler job."""
    scheduler_command = (
        'gcloud scheduler jobs create pubsub birthday-reminder-job '
        '--schedule "0 8 * * *" '
        '--topic birthday-reminder '
        '--message-body "Check birthdays" '
        '--time-zone "America/Bogota"'
    )
    
    try:
        subprocess.run(scheduler_command, shell=True, check=True)
        print("Scheduler configurado exitosamente")
    except subprocess.CalledProcessError:
        # Si ya existe, intentamos actualizarlo
        update_command = (
            'gcloud scheduler jobs update pubsub birthday-reminder-job '
            '--schedule "0 8 * * *" '
            '--topic birthday-reminder '
            '--message-body "Check birthdays" '
            '--time-zone "America/Bogota"'
        )
        try:
            subprocess.run(update_command, shell=True, check=True)
            print("Scheduler actualizado exitosamente")
        except subprocess.CalledProcessError as e:
            print(f"Error al configurar el scheduler: {e}")
            return False
    
    return True

def cleanup(deploy_path):
    """Limpia la carpeta temporal de deploy."""
    shutil.rmtree(deploy_path)
    print(f"Carpeta temporal {deploy_path} eliminada")

def main():
    print("Iniciando proceso de deploy...")
    
    # Leer credenciales
    try:
        creds = read_service_account()
        print("Credenciales de service account leídas correctamente")
    except FileNotFoundError:
        print("Error: No se encontró el archivo service-account.json")
        return
    except json.JSONDecodeError:
        print("Error: El archivo service-account.json no es un JSON válido")
        return
    
    # Preparar carpeta de deploy
    deploy_path = setup_deploy_folder()
    print(f"Carpeta de deploy creada en: {deploy_path}")
    
    # Construir variables de entorno
    env_vars = build_env_vars(creds)
    print("Variables de entorno configuradas")
    
    # Crear topic y desplegar función
    if create_topic() and deploy_function(deploy_path, env_vars):
        # Configurar scheduler
        create_scheduler()
    
    # Limpiar
    cleanup(deploy_path)
    print("Deploy finalizado")

if __name__ == '__main__':
    main()
