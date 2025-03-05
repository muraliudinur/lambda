import json
import boto3
import psycopg2
import secrets
import string
import logging
import os
from hvac import Client

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
AWS_REGION = os.getenv("AWS_REGION")
VAULT_SERVER = os.getenv("VAULT_SERVER")
VAULT_NAMESPACE = os.getenv("VAULT_NAMESPACE")
VAULT_ROLE = os.getenv("VAULT_ROLE")
MASTER_CREDENTIALS_PATH = os.getenv("MASTER_CREDENTIALS_PATH")
APP_CREDENTIALS_PATH = os.getenv("APP_CREDENTIALS_PATH")
PIPELINE_CREDENTIALS_PATH = os.getenv("PIPELINE_CREDENTIALS_PATH")

# User and password keys as environment variables
APP_READ_USER_KEY = os.getenv("APP_READ_USER_KEY")
APP_READ_USER_PASS_KEY = os.getenv("APP_READ_USER_PASS_KEY")
APP_READWRITE_USER_KEY = os.getenv("APP_READWRITE_USER_KEY")
APP_READWRITE_USER_PASS_KEY = os.getenv("APP_READWRITE_USER_PASS_KEY")
PIPELINE_READWRITE_USER_KEY = os.getenv("PIPELINE_READWRITE_USER_KEY")
PIPELINE_READWRITE_USER_PASS_KEY = os.getenv("PIPELINE_READWRITE_USER_PASS_KEY")
MASTER_USER_KEY = os.getenv("MASTER_USER_KEY")
MASTER_PASS_KEY = os.getenv("MASTER_PASS_KEY")


def get_vault_client():
    session = boto3.Session(region_name=AWS_REGION)
    aws_credentials = session.get_credentials().get_frozen_credentials()
    
    logger.info("Logging into Vault")
    vault_client = Client(url=VAULT_SERVER, verify=False, namespace=f"aws/{VAULT_NAMESPACE}")
    vault_client.auth.aws.iam_login(
        access_key=aws_credentials.access_key,
        secret_key=aws_credentials.secret_key,
        session_token=aws_credentials.token,
        role=VAULT_ROLE
    )
    return vault_client


def get_credentials(vault_client, path):
    response = vault_client.secrets.kv.v2.read_secret_version(path=path)
    return response['data']['data']


def generate_new_password(length=16):
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(chars) for _ in range(length))


def update_db_password(master_user, master_password, username, new_password, db_host, db_name):
    conn = psycopg2.connect(
        host=db_host, database=db_name, user=master_user, password=master_password
    )
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute(f"ALTER USER {username} WITH PASSWORD '{new_password}';")
    cursor.close()
    conn.close()


def update_vault_password(vault_client, vault_path, user_key, new_password):
    existing_data = vault_client.secrets.kv.v2.read_secret_version(path=vault_path)['data']['data']
    existing_data[user_key] = new_password
    vault_client.secrets.kv.v2.create_or_update_secret(
        path=vault_path,
        secret=existing_data
    )


def rotate_master_password(vault_client):
    master_creds = get_credentials(vault_client, MASTER_CREDENTIALS_PATH)
    master_user, master_password = master_creds[MASTER_USER_KEY], master_creds[MASTER_PASS_KEY]
    
    new_master_password = generate_new_password()
    
    try:
        update_db_password(master_user, master_password, master_user, new_master_password, master_creds['host'], master_creds['db'])
        update_vault_password(vault_client, MASTER_CREDENTIALS_PATH, MASTER_PASS_KEY, new_master_password)
        logger.info("Successfully rotated master password")
    except Exception as e:
        logger.error(f"Failed to rotate master password: {str(e)}")


def rotate_user_passwords(vault_client, path, user_key, password_key, db_host, db_name, master_user, master_password):
    creds = get_credentials(vault_client, path)
    new_password = generate_new_password()
    
    try:
        update_db_password(master_user, master_password, creds[user_key], new_password, db_host, db_name)
        update_vault_password(vault_client, path, password_key, new_password)
        logger.info(f"Successfully rotated password for {creds[user_key]}")
    except Exception as e:
        logger.error(f"Failed to rotate password for {creds[user_key]}: {str(e)}")


def lambda_handler(event, context):
    vault_client = get_vault_client()
    master_creds = get_credentials(vault_client, MASTER_CREDENTIALS_PATH)
    master_user, master_password = master_creds[MASTER_USER_KEY], master_creds[MASTER_PASS_KEY]
    
    app_creds = get_credentials(vault_client, APP_CREDENTIALS_PATH)
    rotate_user_passwords(vault_client, APP_CREDENTIALS_PATH, APP_READ_USER_KEY, APP_READ_USER_PASS_KEY, app_creds['host'], app_creds['db'], master_user, master_password)
    rotate_user_passwords(vault_client, APP_CREDENTIALS_PATH, APP_READWRITE_USER_KEY, APP_READWRITE_USER_PASS_KEY, app_creds['host'], app_creds['db'], master_user, master_password)
    
    pipeline_creds = get_credentials(vault_client, PIPELINE_CREDENTIALS_PATH)
    rotate_user_passwords(vault_client, PIPELINE_CREDENTIALS_PATH, PIPELINE_READWRITE_USER_KEY, PIPELINE_READWRITE_USER_PASS_KEY, app_creds['host'], app_creds['db'], master_user, master_password)
    
    rotate_master_password(vault_client)
    
    return {
        'statusCode': 200,
        'body': json.dumps('Password rotation completed.')
    }
