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

def setup_secret_manager(creds):
    """Configura los secretos en Secret Manager."""
    # Leer variables necesarias del .env
    load_dotenv()
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY no encontrada en .env")

    secrets = {
        'birthday-reminder-sa': 'service-account.json',
        'gmail-client-secret': 'credentials.json',
        'gmail-refresh-token': 'token_gmail.json',
        'gemini-api-key': gemini_api_key
    }
    
    for secret_id, value in secrets.items():
        # Verificar si el secreto ya existe
        list_command = f'gcloud secrets list --filter="name:{secret_id}" --format="get(name)"'
        result = subprocess.run(list_command, shell=True, capture_output=True, text=True)
        
        if secret_id not in result.stdout:
            # Crear el secreto
            create_command = f'gcloud secrets create {secret_id} --replication-policy="automatic"'
            subprocess.run(create_command, shell=True, check=True)
            print(f"Secreto {secret_id} creado")
        
        # Actualizar el valor del secreto
        if isinstance(value, str) and os.path.exists(value):
            update_command = f'gcloud secrets versions add {secret_id} --data-file="{value}"'
        else:
            # Para valores directos como GEMINI_API_KEY
            with open('temp_secret.txt', 'w') as f:
                f.write(str(value))
            update_command = f'gcloud secrets versions add {secret_id} --data-file="temp_secret.txt"'
            
        subprocess.run(update_command, shell=True, check=True)
        
        # Limpiar archivo temporal si fue creado
        if os.path.exists('temp_secret.txt'):
            os.remove('temp_secret.txt')
            
        print(f"Secreto {secret_id} actualizado")

def build_env_vars():
    """Construye la cadena de variables de entorno para el comando de deploy."""
    load_dotenv()
    
    # Solo variables de configuración y client_id
    load_dotenv()  # Aseguramos que tenemos las variables de .env
    credentials = json.load(open('credentials.json'))
    env_vars = {
        'SPREADSHEET_ID': os.getenv('SPREADSHEET_ID'),
        'YOUR_EMAIL': os.getenv('YOUR_EMAIL'),
        'PROJECT_ID': json.load(open('service-account.json'))['project_id'],
        'GMAIL_CLIENT_ID': credentials['installed']['client_id']
    }

    # Verificar que tenemos todas las variables necesarias
    missing_vars = [key for key, value in env_vars.items() if not value]
    if missing_vars:
        raise ValueError(f"Faltan variables de entorno: {', '.join(missing_vars)}")
    
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

def deploy_function(deploy_path, env_vars, creds):
    """Despliega la función en Google Cloud Functions."""
    deploy_command = (
        f'gcloud functions deploy birthday-reminder '  # nombre de la función en GCP
        f'--gen2 '  # Especificar Gen 2
        f'--runtime python39 '
        f'--region us-central1 '  # Especificar región
        f'--memory 512MB '  # Aumentar memoria disponible
        f'--timeout 60s '  # Establecer timeout en 60 segundos
        f'--trigger-topic birthday-reminder '
        f'--entry-point birthday_reminder '  # nombre de la función en el código
        f'--service-account {creds["client_email"]} '  # Usar el mismo service account
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
        '--time-zone "America/Bogota" '
        '--location us-central1'
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
            '--time-zone "America/Bogota" '
            '--location us-central1'
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
    
    # Dar permisos Owner a la cuenta de servicio
    service_account = f"serviceAccount:{creds['client_email']}"
    project_bind_command = (
        f'gcloud projects add-iam-policy-binding {creds["project_id"]} '
        f'--member="{service_account}" '
        '--role="roles/owner"'
    )
    subprocess.run(project_bind_command, shell=True, check=True)
    print(f"Permisos de Owner asignados a {service_account}")

    # Configurar Secret Manager y construir variables de entorno
    setup_secret_manager(creds)
    env_vars = build_env_vars()
    print("Secretos y variables de entorno configurados")
    
    # Crear topic y desplegar función
    if create_topic() and deploy_function(deploy_path, env_vars, creds):
        # Configurar scheduler
        create_scheduler()
    
    # Limpiar
    cleanup(deploy_path)
    print("Deploy finalizado")

if __name__ == '__main__':
    main()
