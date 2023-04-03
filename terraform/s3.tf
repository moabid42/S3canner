// S3 Bucket the store the backend state
# resource "aws_s3_bucket" "backend_state_bucket" {
#   bucket = "hg-terraform-state-objalert"
#   acl    = "private"
#   region = "eu-central-1"

#   versioning {
#     enabled = true
#   }

#   server_side_encryption_configuration {
#     rule {
#       apply_server_side_encryption_by_default {
#         sse_algorithm = "AES256"
#       }
#     }
#   }
# }

// S3 bucket for storing access logs.
resource "aws_s3_bucket" "objalert_log_bucket" {
  count = var.s3_log_bucket == "" ? 1 : 0 // Create only if no pre-existing log bucket.

  bucket = format("%s.objalert-binaries.%s.access-logs", var.name_prefix, var.aws_region)
  acl    = "log-delivery-write"

  // Everything in the log bucket rotates to infrequent access and expires.
  lifecycle_rule {
    id      = "log_expiration"
    prefix  = ""
    enabled = true

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    expiration {
      days = var.s3_log_expiration_days
    }

    // Old/deleted object versions are permanently removed after 1 day.
    noncurrent_version_expiration {
      days = 1
    }
  }

  // Enable logging on the logging bucket itself.
  logging {
    // The target bucket is the same as the name of this bucket.
    target_bucket = format("%s.objalert-binaries.%s.access-logs", var.name_prefix, var.aws_region)
    target_prefix = "self/"
  }

  tags = {
    Name = "ObjAlert"
  }

  // Enabling versioning protects against accidental deletes.
  versioning {
    enabled = true
  }

  force_destroy = true
}

// Source S3 bucket: binaries uploaded here will be automatically analyzed.
resource "aws_s3_bucket" "objalert_binaries" {
  bucket = "${var.name_prefix}.objalert-binaries.${var.aws_region}"
  acl    = "private"

  logging {
    // Send S3 access logs to either the user-defined logging bucket or the one we created.
    // Note: We can't reference log bucket ID here becuase the bucket may not exist.
    target_bucket = (var.s3_log_bucket == "" ?
      format("%s.objalert-binaries.%s.access-logs", replace(var.name_prefix, "_", "."), var.aws_region)
    : var.s3_log_bucket)

    target_prefix = var.s3_log_prefix
  }

  // Note: STANDARD_IA is not worth it because of the need to periodically re-analyze all binaries
  // in the bucket.

  lifecycle_rule {
    id      = "delete_old_versions"
    prefix  = ""
    enabled = true

    // Old/deleted object versions are permanently removed after 1 day.
    noncurrent_version_expiration {
      days = 1
    }
  }
  tags = {
    Name = "ObjAlert"
  }
  versioning {
    enabled = true
  }
  force_destroy = true
}

// Blocking public access to S3 buckets
resource "aws_s3_bucket_public_access_block" "block_objalert_binaries_bucket" {
  bucket = aws_s3_bucket.objalert_binaries.id

  restrict_public_buckets = true
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
}

resource "aws_s3_bucket_public_access_block" "block_objalert_log_bucket" {
  bucket = aws_s3_bucket.objalert_log_bucket[0].id

  restrict_public_buckets = true
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
}

# Notification event to SQS
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.objalert_binaries.id

  queue {
    queue_arn = aws_sqs_queue.s3_object_queue.arn
    events    = ["s3:ObjectCreated:*"]
  }

  // The queue policy must be created before we can configure the S3 notification.
  depends_on = [aws_sqs_queue_policy.s3_object_queue_policy]
}
