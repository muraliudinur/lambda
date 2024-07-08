import json
import boto3
import requests
import os

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    secret = response['SecretString']
    return json.loads(secret)

def push_to_vault(secret_data, vault_path):
    vault_url = os.environ['VAULT_URL']
    vault_token = os.environ['VAULT_TOKEN']
    
    headers = {
        'X-Vault-Token': vault_token,
        'Content-Type': 'application/json'
    }
    
    response = requests.post(f'{vault_url}/v1/{vault_path}', headers=headers, data=json.dumps(secret_data))
    
    if response.status_code != 204:
        raise Exception(f"Error pushing to Vault: {response.text}")

def lambda_handler(event, context):
    secret_names = os.environ['SECRET_NAMES'].split(',')
    vault_paths = os.environ['VAULT_PATHS'].split(',')
    
    for secret_name, vault_path in zip(secret_names, vault_paths):
        secret_data = get_secret(secret_name)
        push_to_vault(secret_data, vault_path)
    
    return {
        'statusCode': 200,
        'body': json.dumps('Secrets pushed to Vault successfully')
    }
