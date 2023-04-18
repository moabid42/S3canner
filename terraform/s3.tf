// S3 bucket for storing access logs.
resource "aws_s3_bucket" "s3canner_log_bucket" {
  count = var.s3_log_bucket == "" ? 1 : 0 // Create only if no pre-existing log bucket.

  bucket = format("%s.s3canner-binaries.%s.access-logs", var.name_prefix, var.aws_region)
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

  # No need for kms key for just logging bucket
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  tags = {
    Name = "S3canner"
  }

  // Enabling versioning protects against accidental deletes.
  versioning {
    enabled = true
  }

  force_destroy = true
}

# A must since all kind of files could end up here
resource "aws_kms_key" "binaries_bucket_key" {
  description             = "KMS key for s3canner binaries bucket"
  deletion_window_in_days = 7
}

# resource "aws_kms_key_policy" "my_kms_key_policy" {
#   key_id = aws_kms_key.binaries_bucket_key.id

#   policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [
#       {
#         Sid    = "Allow S3 to write event messages to KMS-encrypted S3 bucket"
#         Effect = "Allow"
#         Principal = {
#           Service = "s3.amazonaws.com"
#         }
#         Action = [
#           "kms:GenerateDataKey*",
#           "kms:Decrypt",
#           "kms:ScheduleKeyDeletion"
#         ]
#         Resource = "*"
#       }
#     ]
#   })
# }


// Source S3 bucket: binaries uploaded here will be automatically analyzed.
resource "aws_s3_bucket" "s3canner_binaries" {
  bucket = "${var.name_prefix}.s3canner-binaries.${var.aws_region}"
  acl    = "private"

  logging {
    // Send S3 access logs to either the user-defined logging bucket or the one we created.
    // Note: We can't reference log bucket ID here becuase the bucket may not exist.
    target_bucket = (var.s3_log_bucket == "" ?
      format("%s.s3canner-binaries.%s.access-logs", replace(var.name_prefix, "_", "."), var.aws_region)
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

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        kms_master_key_id = aws_kms_key.binaries_bucket_key.arn
        sse_algorithm     = "aws:kms"
      }
    }
  }

  tags = {
    Name = "S3canner"
  }
  versioning {
    enabled = true
  }
  force_destroy = true
}

// Blocking public access to S3 buckets
resource "aws_s3_bucket_public_access_block" "block_s3canner_binaries_bucket" {
  bucket = aws_s3_bucket.s3canner_binaries.id

  restrict_public_buckets = true
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
}

resource "aws_s3_bucket_public_access_block" "block_s3canner_log_bucket" {
  bucket = aws_s3_bucket.s3canner_log_bucket[0].id

  restrict_public_buckets = true
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
}

# Notification event to SQS
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.s3canner_binaries.id

  queue {
    queue_arn = aws_sqs_queue.s3_object_queue.arn
    events    = ["s3:ObjectCreated:*"]
  }

  // The queue policy must be created before we can configure the S3 notification.
  depends_on = [aws_sqs_queue_policy.s3_object_queue_policy]
}

# Notfiy the lambda function
resource "aws_s3_bucket_notification" "lambda_bucket_notification" {
  bucket = aws_s3_bucket.s3canner_binaries.id

  lambda_function {
    lambda_function_arn = module.s3canner_batcher.function_arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = ""
    filter_suffix       = ""
  }
}

