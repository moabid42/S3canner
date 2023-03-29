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
  name   = "${var.name_prefix}_objalert_base_policy"
  policy = data.aws_iam_policy_document.base_policy.json
}

data "aws_iam_policy_document" "objalert_batcher_policy" {
  statement {
    sid       = "InvokeObjAlertBatcher"
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = ["${module.objalert_batcher.function_arn}"]
  }

  statement {
    sid       = "ListObjAlertBucket"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = ["${aws_s3_bucket.objalert_binaries.arn}"]
  }

  statement {
    sid       = "SendMessageToSQS"
    effect    = "Allow"
    actions   = ["sqs:SendMessage*"]
    resources = ["${aws_sqs_queue.s3_object_queue.arn}"]
  }
}

resource "aws_iam_role_policy" "objalert_batcher_policy" {
  name   = "${var.name_prefix}_objalert_batcher_policy"
  role   = module.objalert_batcher.role_id
  policy = data.aws_iam_policy_document.objalert_batcher_policy.json
}

data "aws_iam_policy_document" "objalert_dispatcher_policy" {
  statement {
    sid       = "InvokeObjAlertAnalyzer"
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = ["${module.objalert_analyzer.function_arn}"]
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

resource "aws_iam_role_policy" "objalert_dispatcher_policy" {
  name   = "${var.name_prefix}_objalert_dispatcher_policy"
  role   = module.objalert_dispatcher.role_id
  policy = data.aws_iam_policy_document.objalert_dispatcher_policy.json
}

data "aws_iam_policy_document" "objalert_analyzer_policy" {
  statement {
    sid    = "QueryAndUpdateDynamo"
    effect = "Allow"

    actions = [
      "dynamodb:PutItem",
      "dynamodb:Query",
      "dynamodb:UpdateItem",
    ]

    resources = ["${aws_dynamodb_table.objalert_yara_matches.arn}"]
  }

  statement {
    sid       = "GetFromObjAlertBucket"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.objalert_binaries.arn}/*"]
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

resource "aws_iam_role_policy" "objalert_analyzer_policy" {
  name   = "${var.name_prefix}_objalert_analyzer_policy"
  role   = module.objalert_analyzer.role_id
  policy = data.aws_iam_policy_document.objalert_analyzer_policy.json
}
