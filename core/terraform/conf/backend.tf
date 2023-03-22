/* Defining a backend file to save the state of the pipeline        */
/* Versioning is enabled to store the previous versions if needed   */

terraform {
    backend "s3" {
        bucket          = "${var.name_prefix}-terraform-state-objalert"
        key             = "terraform.tfstate"
        region          = "${var.aws_region}"
        dynamodb_table  = "my-terraform-state-lock"
        encrypt         = true
        versioning {
            enabled = true
        }
    }
}