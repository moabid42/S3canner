/* Define IAM permissions for the Lambda functions. */

data "aws_iam_policy_document" "base_policy" {
  statement {
    sid    = "EnableLogsAndMetrics"
    effect = "Allow"

    actions = [
      "cloudwatch:PutMetricData",
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = ["*"]
  }
}

resource "aws_iam_policy" "base_policy" {
  name   = "${var.name_prefix}_s3canner_base_policy"
  policy = data.aws_iam_policy_document.base_policy.json
}
###########################################################
data "aws_iam_policy_document" "s3canner_batcher_policy" {
  statement {
    sid       = "InvokeS3cannerBatcher"
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = ["${module.s3canner_batcher.function_arn}"]
  }

  statement {
    sid       = "ListS3cannerBucket"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = ["${aws_s3_bucket.s3canner_binaries.arn}"]
  }

  statement {
    sid       = "SendMessageToSQS"
    effect    = "Allow"
    actions   = ["sqs:SendMessage*"]
    resources = ["${aws_sqs_queue.s3_object_queue.arn}"]
  }
}

resource "aws_iam_role_policy" "s3canner_batcher_policy" {
  name   = "${var.name_prefix}_s3canner_batcher_policy"
  role   = module.s3canner_batcher.role_id
  policy = data.aws_iam_policy_document.s3canner_batcher_policy.json
}
###########################################################
data "aws_iam_policy_document" "s3canner_dispatcher_policy" {
  statement {
    sid       = "InvokeS3cannerAnalyzer"
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = ["${module.s3canner_analyzer.function_arn}"]
  }

  statement {
    sid    = "ProcessSQSMessages"
    effect = "Allow"

    actions = [
      "sqs:DeleteMessage",
      "sqs:ReceiveMessage",
    ]

    resources = ["${aws_sqs_queue.s3_object_queue.arn}"]
  }
}

resource "aws_iam_role_policy" "s3canner_dispatcher_policy" {
  name   = "${var.name_prefix}_s3canner_dispatcher_policy"
  role   = module.s3canner_dispatcher.role_id
  policy = data.aws_iam_policy_document.s3canner_dispatcher_policy.json
}
###########################################################
data "aws_iam_policy_document" "s3canner_analyzer_policy" {
  statement {
    sid    = "QueryAndUpdateDynamo"
    effect = "Allow"

    actions = [
      "dynamodb:PutItem",
      "dynamodb:Query",
      "dynamodb:UpdateItem",
    ]

    resources = ["${aws_dynamodb_table.s3canner_yara_matches.arn}"]
  }

  statement {
    sid       = "GetFromS3cannerBucket"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.s3canner_binaries.arn}/*"]
  }

  statement {
    sid       = "PublishAlertsToSNS"
    effect    = "Allow"
    actions   = ["sns:Publish"]
    resources = ["${aws_sns_topic.yara_match_alerts.arn}"]
  }

  statement {
    sid       = "DeleteSQSMessages"
    effect    = "Allow"
    actions   = ["sqs:DeleteMessage"]
    resources = ["${aws_sqs_queue.s3_object_queue.arn}"]
  }
}

resource "aws_iam_role_policy" "s3canner_analyzer_policy" {
  name   = "${var.name_prefix}_s3canner_analyzer_policy"
  role   = module.s3canner_analyzer.role_id
  policy = data.aws_iam_policy_document.s3canner_analyzer_policy.json
}
###########################################################
data "aws_iam_policy_document" "s3canner_secrets_analyzer_policy" {
  statement {
    sid    = "QueryAndUpdateDynamo"
    effect = "Allow"

    actions = [
      "dynamodb:PutItem",
      "dynamodb:Query",
      "dynamodb:UpdateItem",
    ]

    resources = ["${aws_dynamodb_table.s3canner_secrets_matches.arn}"]
  }

  statement {
    sid       = "GetFromS3cannerBucket"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.s3canner_binaries.arn}/*"]
  }

  statement {
    sid       = "PublishAlertsToSNS"
    effect    = "Allow"
    actions   = ["sns:Publish"]
    resources = ["${aws_sns_topic.secrets_match_alerts.arn}"]
  }

  statement {
    sid       = "DeleteSQSMessages"
    effect    = "Allow"
    actions   = ["sqs:DeleteMessage"]
    resources = ["${aws_sqs_queue.s3_object_queue.arn}"]
  }
}

resource "aws_iam_role_policy" "s3canner_secrets_analyzer_policy" {
  name   = "${var.name_prefix}_s3canner_secrets_analyzer_policy"
  role   = module.s3canner_secrets_analyzer.role_id
  policy = data.aws_iam_policy_document.s3canner_secrets_analyzer_policy.json
}
