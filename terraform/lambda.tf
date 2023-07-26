// Create the batch Lambda function.
module "s3canner_batcher" {
  source          = "./modules/lambda"
  function_name   = "${var.name_prefix}_s3canner_batcher"
  description     = "Enqueues all S3 objects into SQS for re-analysis"
  base_policy_arn = aws_iam_policy.base_policy.arn
  handler         = "main.batch_lambda_handler"
  memory_size_mb  = var.lambda_batch_memory_mb
  timeout_sec     = 300
  filename        = "lambda_batcher.zip"

  environment_variables = {
    BATCH_LAMBDA_NAME      = "${var.name_prefix}_s3canner_batcher"
    BATCH_LAMBDA_QUALIFIER = "Production"
    OBJECTS_PER_MESSAGE    = "${var.lambda_batch_objects_per_message}"
    S3_BUCKET_NAME         = "${aws_s3_bucket.s3canner_binaries.id}"
    SQS_QUEUE_URL          = "${aws_sqs_queue.s3_object_queue.id}"
  }

  log_retention_days = var.lambda_log_retention_days
  alarm_sns_arns     = ["${aws_sns_topic.metric_alarms.arn}"]
  tagged_name        = var.tagged_name
}

resource "aws_lambda_permission" "allow_s3_trigger" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = module.s3canner_batcher.function_arn
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.s3canner_binaries.arn
}

// Create the dispatching Lambda function.
module "s3canner_dispatcher" {
  source          = "./modules/lambda"
  function_name   = "${var.name_prefix}_s3canner_dispatcher"
  description     = "Poll SQS events and fire them off to analyzers"
  base_policy_arn = aws_iam_policy.base_policy.arn
  handler         = "main.dispatch_lambda_handler"
  memory_size_mb  = var.lambda_dispatch_memory_mb
  timeout_sec     = var.lambda_dispatch_timeout_sec
  filename        = "lambda_dispatcher.zip"

  environment_variables = {
    ANALYZE_LAMBDA_NAME              = "${module.s3canner_analyzer.function_name}"
    ANALYZE_LAMBDA_QUALIFIER         = "${module.s3canner_analyzer.alias_name}"
    SECRETS_ANALYZE_LAMBDA_NAME      = "${module.s3canner_secrets_analyzer.function_name}"
    SECRETS_ANALYZE_LAMBDA_QUALIFIER = "${module.s3canner_secrets_analyzer.alias_name}"
    MAX_DISPATCHES                   = "${var.lambda_dispatch_limit}"
    SQS_QUEUE_URL                    = "${aws_sqs_queue.s3_object_queue.id}"
  }

  log_retention_days = var.lambda_log_retention_days
  alarm_sns_arns     = ["${aws_sns_topic.metric_alarms.arn}"]
  tagged_name        = var.tagged_name
}


// Map the Lambda function to the SQS queue
resource "aws_lambda_event_source_mapping" "dispatcher_source_mapping" {
  event_source_arn = aws_sqs_queue.s3_object_queue.arn
  function_name    = module.s3canner_dispatcher.function_name
  batch_size       = 10
}

resource "aws_lambda_permission" "dispacher_sqs_permission" {
  statement_id  = "AllowSQS"
  action        = "lambda:InvokeFunction"
  function_name = module.s3canner_dispatcher.function_name
  principal     = "sqs.amazonaws.com"

  source_arn = aws_sqs_queue.s3_object_queue.arn
}

# // Allow dispatcher to be invoked via a CloudWatch rule.3
# resource "aws_lambda_permission" "allow_cloudwatch_to_invoke_dispatch" {
#   statement_id  = "AllowExecutionFromCloudWatch_${module.s3canner_dispatcher.function_name}"
#   action        = "lambda:InvokeFunction"
#   function_name = module.s3canner_dispatcher.function_name
#   principal     = "events.amazonaws.com"
#   source_arn    = aws_cloudwatch_event_rule.dispatch_cronjob.arn
#   qualifier     = module.s3canner_dispatcher.alias_name
# }

resource "aws_iam_policy" "lambda_policy" {
  name_prefix = "lambda_policy_"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = "arn:aws:lambda:eu-central-1:375140005095:function:hg_s3canner_analyzer:Production"
      },
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = module.s3canner_secrets_analyzer.alias_arn
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:GetQueueAttributes",
          "sqs:SendMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = "arn:aws:sqs:eu-central-1:*:*"
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  policy_arn = aws_iam_policy.lambda_policy.arn
  role       = "hg_s3canner_dispatcher_role"
}

// Create the analyzer Lambda function.
module "s3canner_analyzer" {
  source          = "./modules/lambda"
  function_name   = "${var.name_prefix}_s3canner_analyzer"
  description     = "Analyze a obj with a set of YARA rules"
  base_policy_arn = aws_iam_policy.base_policy.arn
  handler         = "main.analyze_lambda_handler"
  memory_size_mb  = var.lambda_analyze_memory_mb
  timeout_sec     = var.lambda_analyze_timeout_sec
  filename        = "lambda_analyzer.zip"

  environment_variables = {
    S3_BUCKET_NAME                 = "${aws_s3_bucket.s3canner_binaries.id}"
    SQS_QUEUE_URL                  = "${aws_sqs_queue.s3_object_queue.id}"
    YARA_MATCHES_DYNAMO_TABLE_NAME = "${aws_dynamodb_table.s3canner_yara_matches.name}"
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


// Create the secrests and sensitive informations analyzer Lambda function.
module "s3canner_secrets_analyzer" {
  source          = "./modules/lambda"
  function_name   = "${var.name_prefix}_s3canner_secrets_analyzer"
  description     = "Analyze an obj with thrufflehog"
  base_policy_arn = aws_iam_policy.base_policy.arn
  handler         = "main.secrets_analyze_lambda_handler"
  memory_size_mb  = var.lambda_analyze_memory_mb
  timeout_sec     = var.lambda_analyze_timeout_sec
  filename        = "secrets_lambda_analyzer.zip"

  environment_variables = {
    S3_BUCKET_NAME                    = "${aws_s3_bucket.s3canner_binaries.id}"
    SQS_QUEUE_URL                     = "${aws_sqs_queue.s3_object_queue.id}"
    SECRETS_MATCHES_DYNAMO_TABLE_NAME = "${aws_dynamodb_table.s3canner_secrets_matches.name}"
    SECRETS_ALERTS_SNS_TOPIC_ARN      = "${aws_sns_topic.secrets_match_alerts.arn}"
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