// Remote state (backend) resources

provider "aws" {
    region = "eu-central-1"
}

resource "aws_s3_bucket" "terraform_state" {
  bucket = "s3canner-tfstate"
     
  lifecycle {
    prevent_destroy = true
  }
  # versioning {
  #   enabled = true
  # }
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

  attribute {
    name = "LockID"
    type = "S"
  }
}
