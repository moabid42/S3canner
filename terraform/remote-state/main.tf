// Remote state (backend) resources

provider "aws" {
    region = "eu-central-1"
}

resource "aws_kms_key" "remote_state_key" {
  description = "KMS key for Remote state S3 bucket."
  deletion_window_in_days = 7 # the min

  # Enable Key Rotation
  enable_key_rotation = true
}

resource "aws_s3_bucket" "terraform_state" {
  bucket = "s3canner-tfstate"

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        kms_master_key_id = aws_kms_key.remote_state_key.arn
        sse_algorithm = "aws:kms"
      }
    }
  }

  lifecycle {
    prevent_destroy = true
  }
  # enabled to prevent from accidental changes or deletions
  versioning {
    enabled = true
  }
  # force_destroy = true
}

resource "aws_s3_bucket_versioning" "terraform_state" {
    bucket = aws_s3_bucket.terraform_state.id

    versioning_configuration {
      status = "Enabled"
    }
}

resource "aws_dynamodb_table" "terraform_state_lock" {
  name           = "s3canner-app-state"
  read_capacity  = 1
  write_capacity = 1
  hash_key       = "LockID"

  // Enable Point-In-Time Recovery (PITR) for the table
  point_in_time_recovery {
    enabled = true
  }

  attribute {
    name = "LockID"
    type = "S"
  }
}
