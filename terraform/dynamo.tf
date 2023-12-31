// DynamoDB table for storing match results.
resource "aws_dynamodb_table" "s3canner_yara_matches" {
  name           = "${var.name_prefix}_s3canner_matches"
  hash_key       = "SHA256"
  range_key      = "LambdaVersion"
  read_capacity  = var.dynamo_read_capacity
  write_capacity = var.dynamo_write_capacity

  // Only attributes used as hash/range keys are defined here.
  attribute {
    name = "SHA256"
    type = "S"
  }

  attribute {
    name = "LambdaVersion"
    type = "N"
  }

  // Enable Point-In-Time Recovery (PITR) for the table
  point_in_time_recovery {
    enabled = true
  }
  
  tags = {
    Name = "S3canner"
  }
}

// DynamoDB table for storing sensitive informations match results.
resource "aws_dynamodb_table" "s3canner_secrets_matches" {
  name           = "${var.name_prefix}_s3canner_secrets_matches"
  hash_key       = "SHA256"
  range_key      = "LambdaVersion"
  read_capacity  = var.dynamo_read_capacity
  write_capacity = var.dynamo_write_capacity

  // Only attributes used as hash/range keys are defined here.
  attribute {
    name = "SHA256"
    type = "S"
  }

  attribute {
    name = "LambdaVersion"
    type = "N"
  }

  // Enable Point-In-Time Recovery (PITR) for the table
  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name = "S3canner"
  }
}
