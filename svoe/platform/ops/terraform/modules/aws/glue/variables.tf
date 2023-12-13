variable "datalake_s3_bucket_name" {
  type = string
  default = "svoe.test.1"
}

variable "query_results_s3_bucket_name" {
  type = string
  default = "svoe-athena-query-reults"
}

# TODO this var is not used anymore, remove
# TODO or is it? there is 'data_lake' folder in s3, shoud it be this?
variable "datalake_data_prefix" {
  type = string
  default = "parquet"
}

# TODO add outputs to this module and pipe to helmfile vars/secrets