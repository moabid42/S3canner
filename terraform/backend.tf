/* Defining a backend file to save the state of the pipeline        */

# terraform {
#   backend "s3" {
#     bucket         = "objalert-tfstate"
#     key            = "terraform.tfstate"
#     region         = "eu-central-1"
#     dynamodb_table = "objalert-app-state"
#     encrypt        = true
#   }
# }


