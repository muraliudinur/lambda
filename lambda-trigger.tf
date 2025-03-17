1. Use md5() or sha256() to Force Change
Terraform only redeploys AWS Lambda if the source file explicitly changes. The best way to ensure this is to use a hash-based filename.


data "local_file" "lambda_source" {
  filename = "lambda_function.py"
}

resource "null_resource" "trigger_lambda_update" {
  triggers = {
    file_hash = md5(data.local_file.lambda_source.content)
  }
}

data "archive_file" "lambda_package" {
  type        = "zip"
  output_path = "lambda_function_${md5(data.local_file.lambda_source.content)}.zip"

  source {
    content  = data.local_file.lambda_source.content
    filename = "lambda_function.py"
  }

  depends_on = [null_resource.trigger_lambda_update]
}

resource "aws_lambda_function" "lambda" {
  function_name = "my_lambda_function"
  role          = aws_iam_role.lambda_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.8"

  filename      = data.archive_file.lambda_package.output_path
  source_code_hash = filebase64sha256(data.archive_file.lambda_package.output_path)

  environment {
    variables = {
      MY_VAR = "test"
    }
  }
}
