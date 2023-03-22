###         S3 Bucket Recources         ###

// S3 bucket for storing access logs
resource "aws_s3" "abjalert_log_bucket" {
    count   = "${var.s3_log_bucket == "" ? 1 : 0}" // condition of creation if none existing

    bucket  = "${format("%s.objalert-binaries.%s.access-logs", var.name_prefix, var.aws_region)}"
    acl     = "log-delivery-write"

    lifecycle_rule {
        id  = "log_expiration"
        prefix = ""
        enabled = true

        transition {
            days = 30
            storage_class = "STANDARD_IA"
        }

        expiration {
            days = "${var.s3_log_expiration_days}"
        }

        noncurrent_version_expiration {
            days = 1
        }

        logging {
            target_bucket = "${format("%s.objalert-binaries.%s.access-logs", var.name_prefix, var.aws_region)}"
            target_prefix = "self/"
        }

        tags {
            Name = "Objalert"
        }

        versioning {
            enabled = true
        }
    }
}

// Source S3 bucket where we store the uploaded binaries (here will be automatically analyzed)
resource "aws_s3_bucket" "objalert_binaries" {
    bucket = "${var.name_prefix}.objalert-binaries.${var.aws_region}"
    acl = "private"

    logging {
        target_bucket = "${var.s3_log_bucket == "" ?
        format("%s.objalert-binaries.%s.access-logs", var.name_prefix, var.aws_region)
        : var.s3_log_bucket}"

        target_prefix =  "${var.s3_log_prefix}"
    }

    lifecycle_rule {
        id = "delete_old_versions"
        prefix = ""
        enabled = true

        noncurrent_version_expiration {
            days = 1
        }
    }
}

resource "aws_s3_bucket_notification" "bucket_notification" {
    bucket = "${aws_s3_bucket.objalert_binaries.id}"

    queue {
        queue_arn = "${aws_sqs_queue.s3_object_queue.arn}"
        events = ["s3:ObjectCreated:*"]
    }

    depends_on = ["aws_sqs_queue_policy.s3_object_queue_policy"]
}


