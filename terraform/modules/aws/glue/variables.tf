variable "datalake_s3_bucket_name" {
  type = string
  default = "svoe.test.1"
}

variable "query_results_s3_bucket_name" {
  type = string
  default = "svoe-athena-query-reults"
}

variable "datalake_data_prefix" {
  type = string
  default = "parquet"
}