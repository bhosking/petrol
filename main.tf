provider aws {
  region = "ap-southeast-2"
  profile = "terraform"
}


module "lambda_checkPrices" {
  source = "github.com/bhosking/terraform-aws-lambda"

  function_name = "checkPrices"
  description = "Publishes a message if there is a petrol price increase."
  handler = "lambda_function.lambda_handler"
  runtime = "python3.8"
  memory_size = 512
  timeout = 4
  policy = {
    json = data.aws_iam_policy_document.lambda_checkPrices.json
  }
  source_path = "${path.module}/lambda/checkPrices"

  environment = {
    variables = {
      CENTRE_LAT = var.centre_lat
      CENTRE_LNG = var.centre_lng
      MIN_COORD_DIST = 0.06
      MAX_COORD_DIST = 0.2
      PETROL_ALERT_TOPIC = aws_sns_topic.petrol_alert.arn
      PRICES_BUCKET = aws_s3_bucket.prices_bucket.bucket
      URL_QUERY_TIMEOUT = 2
    }
  }
}
