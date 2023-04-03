// Declare archive_file data source in root module
# data "archive_file" "lambda_functions" {
#   for_each = var.lambda_functions

#   type        = "zip"
#   source_dir  = "../core/lambda_functions/${each.value}"
#   output_path = "${path.module}/dist/${each.value}.zip"
# }

// Create the batch Lambda function.
module "objalert_batcher" {
  source          = "./modules/lambda"
  function_name   = "${var.name_prefix}_objalert_batcher"
  description     = "Enqueues all S3 objects into SQS for re-analysis"
  base_policy_arn = aws_iam_policy.base_policy.arn
  handler         = "main.batch_lambda_handler"
  memory_size_mb  = var.lambda_batch_memory_mb
  timeout_sec     = 300
  filename        = "lambda_batcher.zip"

  environment_variables = {
    BATCH_LAMBDA_NAME      = "${var.name_prefix}_objalert_batcher"
    BATCH_LAMBDA_QUALIFIER = "Production"
    OBJECTS_PER_MESSAGE    = "${var.lambda_batch_objects_per_message}"
    S3_BUCKET_NAME         = "${aws_s3_bucket.objalert_binaries.id}"
    SQS_QUEUE_URL          = "${aws_sqs_queue.s3_object_queue.id}"
  }

  log_retention_days = var.lambda_log_retention_days
  alarm_sns_arns     = ["${aws_sns_topic.metric_alarms.arn}"]
  tagged_name        = var.tagged_name
}

resource "aws_lambda_permission" "allow_s3_trigger" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = module.objalert_batcher.function_arn
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.objalert_binaries.arn
}

// Create the dispatching Lambda function.
module "objalert_dispatcher" {
  source          = "./modules/lambda"
  function_name   = "${var.name_prefix}_objalert_dispatcher"
  description     = "Poll SQS events and fire them off to analyzers"
  base_policy_arn = aws_iam_policy.base_policy.arn
  handler         = "main.dispatch_lambda_handler"
  memory_size_mb  = var.lambda_dispatch_memory_mb
  timeout_sec     = var.lambda_dispatch_timeout_sec
  filename        = "lambda_dispatcher.zip"

  environment_variables = {
    ANALYZE_LAMBDA_NAME      = "${module.objalert_analyzer.function_name}"
    ANALYZE_LAMBDA_QUALIFIER = "${module.objalert_analyzer.alias_name}"
    MAX_DISPATCHES           = "${var.lambda_dispatch_limit}"
    SQS_QUEUE_URL            = "${aws_sqs_queue.s3_object_queue.id}"
  }

  log_retention_days = var.lambda_log_retention_days
  alarm_sns_arns     = ["${aws_sns_topic.metric_alarms.arn}"]
  tagged_name        = var.tagged_name
}

// Allow dispatcher to be invoked via a CloudWatch rule.3
resource "aws_lambda_permission" "allow_cloudwatch_to_invoke_dispatch" {
  statement_id  = "AllowExecutionFromCloudWatch_${module.objalert_dispatcher.function_name}"
  action        = "lambda:InvokeFunction"
  function_name = module.objalert_dispatcher.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.dispatch_cronjob.arn
  qualifier     = module.objalert_dispatcher.alias_name
}

// Create the analyzer Lambda function.
module "objalert_analyzer" {
  source          = "./modules/lambda"
  function_name   = "${var.name_prefix}_objalert_analyzer"
  description     = "Analyze a obj with a set of YARA rules"
  base_policy_arn = aws_iam_policy.base_policy.arn
  handler         = "main.analyze_lambda_handler"
  memory_size_mb  = var.lambda_analyze_memory_mb
  timeout_sec     = var.lambda_analyze_timeout_sec
  filename        = "lambda_analyzer.zip"

  environment_variables = {
    S3_BUCKET_NAME                 = "${aws_s3_bucket.objalert_binaries.id}"
    SQS_QUEUE_URL                  = "${aws_sqs_queue.s3_object_queue.id}"
    YARA_MATCHES_DYNAMO_TABLE_NAME = "${aws_dynamodb_table.objalert_yara_matches.name}"
    YARA_ALERTS_SNS_TOPIC_ARN      = "${aws_sns_topic.yara_match_alerts.arn}"
  }

  log_retention_days = var.lambda_log_retention_days
  tagged_name        = var.tagged_name
  // During batch operations, the analyzer will have a high error rate because of S3 latency.
  alarm_errors_help = <<EOF
If (a) the number of errors is not growing unbounded,
(b) the errors are correlated with a rise in S3 download latency, and
(c) the batcher is currently running (e.g. after a deploy),
then you can resolve this alert (and consider increasing the threshold for this alarm).
Otherwise, there is an unknown problem with the analyzers (which may still be related to S3).
EOF

  alarm_errors_threshold     = 50
  alarm_errors_interval_secs = 300
  alarm_sns_arns             = ["${aws_sns_topic.metric_alarms.arn}"]
}
