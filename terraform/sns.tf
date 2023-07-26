# KMS key for yara matches topic
resource "aws_kms_key" "yara_matches_topic_key" {
  description             = "KMS key for the Yara matches sns topic"
  deletion_window_in_days = 7

  # Enable Key Rotation
  enable_key_rotation = true
}

# KMS key for yara matches topic
resource "aws_kms_key" "metric_topic_key" {
  description             = "KMS key for the metric sns topic"
  deletion_window_in_days = 7

  # Enable Key Rotation
  enable_key_rotation = true
}

# KMS key for yara matches topic
resource "aws_kms_key" "secrets_match_topic_key" {
  description             = "KMS key for the secrets match sns topic"
  deletion_window_in_days = 7

  # Enable Key Rotation
  enable_key_rotation = true
}

// YARA match alerts will be published to this SNS topic.
resource "aws_sns_topic" "yara_match_alerts" {
  name = "${var.name_prefix}_s3canner_yara_match_alerts"

  kms_master_key_id = aws_kms_key.yara_matches_topic_key.arn
}

// CloudWatch metric alarms notify this SNS topic.
resource "aws_sns_topic" "metric_alarms" {
  name = "${var.name_prefix}_s3canner_metric_alarms"

  kms_master_key_id = aws_kms_key.metric_topic_key.arn
}

// Sensitive match alerts will be published to this SNS topic.
resource "aws_sns_topic" "secrets_match_alerts" {
  name = "${var.name_prefix}_s3canner_secrets_match_alerts"

  kms_master_key_id = aws_kms_key.secrets_match_topic_key.arn
}