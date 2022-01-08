resource aws_cloudwatch_event_rule schedule {
  name = "schedule"
  description = "Fires every hour"
  schedule_expression = "rate(1 hour)"
}

resource aws_cloudwatch_event_target checkPrice_schedule  {
  rule = aws_cloudwatch_event_rule.schedule.name
  target_id = "lambda"
  arn = module.lambda_checkPrices.function_arn
}
