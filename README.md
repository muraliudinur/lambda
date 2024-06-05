terraform code for lambda function to push aws secrets to Vault Enterprise 
ChatGPT
Creating Terraform code to deploy a Lambda function that pushes AWS Secrets to HashiCorp Vault Enterprise involves several steps:

Create the Lambda function: Write the Lambda function code and upload it to an S3 bucket or use an inline approach.
IAM Role and Policies: Define the necessary IAM roles and policies for the Lambda function.
Create the Lambda Function using Terraform: Configure the Lambda function, including environment variables and permissions.
Here's a step-by-step guide with the necessary Terraform code.

Step 1: Write the Lambda Function Code
Save the following Python code to a file, e.g., lambda_function.py.

python
Copy code
import os
import json
import boto3
import requests

# Initialize AWS Secrets Manager client
secrets_client = boto3.client('secretsmanager')

# Vault configuration from environment variables
VAULT_URL = os.environ['VAULT_URL']
VAULT_ROLE = os.environ['VAULT_ROLE']
VAULT_PATH = os.environ['VAULT_PATH']

def lambda_handler(event, context):
    secret_name = event.get('secret_name')
    
    if not secret_name:
        raise ValueError("The event must include 'secret_name'")
    
    # Retrieve secret from AWS Secrets Manager
    try:
        get_secret_value_response = secrets_client.get_secret_value(SecretId=secret_name)
        secret = get_secret_value_response['SecretString']
    except Exception as e:
        print(f"Error retrieving secret from AWS Secrets Manager: {e}")
        raise e
    
    # Authenticate with Vault using AWS IAM
    try:
        headers = {
            'X-Vault-Token': VAULT_ROLE,
            'Content-Type': 'application/json'
        }
        data = {
            'data': json.loads(secret)
        }
        
        response = requests.post(f"{VAULT_URL}/v1/{VAULT_PATH}", headers=headers, data=json.dumps(data))
        response.raise_for_status()
        
        print(f"Secret {secret_name} successfully written to Vault")
    except Exception as e:
        print(f"Error writing secret to Vault: {e}")
        raise e
Step 2: Terraform Configuration
Define Variables: Create a variables.tf file to define your variables.
hcl
Copy code
variable "aws_region" {
  description = "The AWS region where resources will be created."
  default     = "us-west-2"
}

variable "s3_bucket" {
  description = "The name of the S3 bucket to store the Lambda function code."
}

variable "vault_url" {
  description = "The URL of your Vault server."
}

variable "vault_role" {
  description = "The Vault role for authentication."
}

variable "vault_path" {
  description = "The path in Vault where secrets will be stored."
}
Provider Configuration: Create a provider.tf file.
hcl
Copy code
provider "aws" {
  region = var.aws_region
}
IAM Role and Policies: Create an iam.tf file.
hcl
Copy code
resource "aws_iam_role" "lambda_role" {
  name = "lambda_vault_secrets_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action    = "sts:AssumeRole"
        Effect    = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "lambda_policy" {
  name        = "lambda_vault_secrets_policy"
  description = "Policy for Lambda function to access AWS Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:ListSecrets"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_role_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}
Lambda Function Deployment: Create a lambda.tf file.
hcl
Copy code
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "lambda_function.py"
  output_path = "lambda_function.zip"
}

resource "aws_s3_bucket_object" "lambda_zip" {
  bucket = var.s3_bucket
  key    = "lambda_function.zip"
  source = data.archive_file.lambda_zip.output_path
}

resource "aws_lambda_function" "vault_secrets" {
  function_name = "PushSecretsToVault"
  role          = aws_iam_role.lambda_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.8"
  s3_bucket     = var.s3_bucket
  s3_key        = aws_s3_bucket_object.lambda_zip.key

  environment {
    variables = {
      VAULT_URL   = var.vault_url
      VAULT_ROLE  = var.vault_role
      VAULT_PATH  = var.vault_path
    }
  }
}
Lambda Execution Permissions: Ensure the Lambda function has the necessary permissions.
hcl
Copy code
resource "aws_lambda_permission" "allow_invoke" {
  statement_id  = "AllowExecutionFromAWS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.vault_secrets.function_name
  principal     = "secretsmanager.amazonaws.com"
}
Output the Lambda Function ARN: Create an outputs.tf file.
hcl
Copy code
output "lambda_function_arn" {
  value = aws_lambda_function.vault_secrets.arn
}
Step 3: Deploy with Terraform
Initialize Terraform:

bash
Copy code
terraform init
Apply the Configuration:

bash
Copy code
terraform apply
Review the changes and type yes to confirm.

Additional Considerations
Secrets Manager Event Trigger: If you want to automatically trigger the Lambda function when a secret is updated, you need to configure an AWS Secrets Manager event source mapping. This part can be done manually or automated using additional Terraform configurations.
Security: Ensure that sensitive information such as Vault tokens or AWS credentials are stored securely, possibly using AWS Secrets Manager or AWS Systems Manager Parameter Store.
Logging and Monitoring: Enable CloudWatch logging for your Lambda function to monitor and troubleshoot any issues.
This setup will allow your Lambda function to securely push secrets from AWS Secrets Manager to HashiCorp Vault Enterprise using Terraform for infrastructure as code (IaC) management.
