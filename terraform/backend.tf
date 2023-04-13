/* Defining a backend file to save the state of the pipeline        */

terraform {
  backend "s3" {
    bucket         = "s3canner-tfstate"
    key            = "terraform.tfstate"
    region         = "eu-central-1"
    dynamodb_table = "s3canner-app-state"
    encrypt        = true
  }
}


