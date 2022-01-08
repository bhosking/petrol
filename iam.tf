data aws_iam_policy_document lambda_checkPrices {
  statement {
    actions = [
      "s3:PutObject",
      "s3:GetObject",
    ]
    resources = [
      "${aws_s3_bucket.prices_bucket.arn}/*",
    ]
  }

  statement {
    actions = [
      "SNS:Publish",
    ]
    resources = [
      aws_sns_topic.petrol_alert.arn,
    ]
  }
}

data aws_iam_policy_document lambda_checkPrices_selfModify {
  statement {
    actions = [
      "lambda:UpdateFunctionConfiguration",
    ]
    resources = [
      module.lambda_checkPrices.function_arn,
    ]
  }
}

resource aws_iam_policy lambda_checkPrices_selfModify {
  name = "checkPrices-self-modify"
  policy = data.aws_iam_policy_document.lambda_checkPrices_selfModify.json
}

resource aws_iam_role_policy_attachment lambda_checkPrices_selfModify {
  role = module.lambda_checkPrices.role_name
  policy_arn = aws_iam_policy.lambda_checkPrices_selfModify.arn
}
