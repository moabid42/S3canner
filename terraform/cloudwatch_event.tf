/* A scheduled cloudwatch event is used to trigger Lambda functions like cronjobs. */

resource "aws_cloudwatch_event_rule" "dispatch_cronjob" {
  name                = "${var.name_prefix}_s3canner_dispatch_cronjob"
  description         = "Regularly executes the S3canner dispatcher Lambda function."
  schedule_expression = "rate(${var.lambda_dispatch_frequency_minutes} ${var.lambda_dispatch_frequency_minutes == 1 ? "minute" : "minutes"})"
}

resource "aws_cloudwatch_event_target" "invoke_dispatch_lambda" {
  rule      = aws_cloudwatch_event_rule.dispatch_cronjob.name
  target_id = "${var.name_prefix}_s3canner_dispatch_to_lambda"
  arn       = module.s3canner_dispatcher.alias_arn
}
