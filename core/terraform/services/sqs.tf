// Queue of S3 objects to be analyzed

resource "aws_sqs_queue" "s3_object_queue" {
    name = "${var.name_prefix}_objalert_s3_object_queue"

    visibility_timeout_seconds = "${format("%d", var.lambda_analyze_timout_sec + 3)}"
    message_retention_seconds = "${format("%d", var.sqs_retention_minutes * 60)}"
}

data "aws_iam_policy_document" "s3_object_queue_policy" {
    statement {
        sid = "AllowObjectAlertBucketToNotifySQS"
        effect = "Allow"

        principals {
            type = "AWS"
            identifiers = ["*"]
        }

        actions = ["sqs:SendMessage"]
        recourses = ["${aws_sqs_queue.s3_object_queue.arn}"]

        // We are restricting the notifying to only the ObjAlert S3 bucket
        condition {
            test = "ArnEquals"
            variable = "aws:SourceArn"
            values = ["${aws_s3_bucket.objalert_binaries.arn}"]
        }
    }
}