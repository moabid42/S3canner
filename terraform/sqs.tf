// Create a KMS key for SQS service
resource "aws_kms_key" "s3_object_queue_key" {
  description             = "KMS key for the s3_object_queue SQS queue"
  deletion_window_in_days = 7
}

resource "aws_kms_key_policy" "s3_object_queue_key_policy" {
  policy = jsonencode({
    Version : "2012-10-17",
    Statement : [
      {
        Sid : "Allow all actions",
        Effect : "Allow",
        Principal : {
          AWS : "*"
        },
        Action : "kms:*",
        Resource : "*"
      }
    ]
  })

  key_id = aws_kms_key.s3_object_queue_key.key_id
}


// Queue of S3 objects to be analyzed.
resource "aws_sqs_queue" "s3_object_queue" {
  name = "${var.name_prefix}_s3canner_s3_object_queue"

  // When a message is received, it will be hidden from the queue for this long.
  // Set to just a few seconds after the lambda analyzer would timeout.
  visibility_timeout_seconds = format("%d", var.lambda_analyze_timeout_sec + 2)

  message_retention_seconds = format("%d", var.sqs_retention_minutes * 60)

  kms_master_key_id = aws_kms_key.s3_object_queue_key.arn
}

data "aws_iam_policy_document" "s3_object_queue_policy" {
  statement {
    sid    = "AllowS3cannerBucketToNotifySQS"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    actions   = ["sqs:SendMessage"]
    resources = ["${aws_sqs_queue.s3_object_queue.arn}"]

    # // Allow only the S3canner S3 bucket to notify the SQS queue.
    # condition {
    #   test     = "ArnEquals"
    #   variable = "aws:SourceArn"
    #   values   = ["${aws_s3_bucket.s3canner_binaries.arn}"]
    # }
  }
}

// Allow SQS to be sent messages from the S3canner S3 bucket.
resource "aws_sqs_queue_policy" "s3_object_queue_policy" {
  queue_url = aws_sqs_queue.s3_object_queue.id
  policy    = data.aws_iam_policy_document.s3_object_queue_policy.json
}
