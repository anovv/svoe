
# IAM Roles
resource "aws_iam_role" "glue-role" {
  name               = "glue_role"
  assume_role_policy = data.aws_iam_policy_document.glue-assume-role-policy.json
}

resource "aws_iam_policy" "extra-policy" {
  name        = "extra-policy"
  description = "A test policy"
  policy      = data.aws_iam_policy_document.extra-policy-document.json

}

resource "aws_iam_role_policy_attachment" "extra-policy-attachment" {
  role       = aws_iam_role.glue-role.name
  policy_arn = aws_iam_policy.extra-policy.arn
}

resource "aws_iam_role_policy_attachment" "glue-service-role-attachment" {
  role       = aws_iam_role.glue-role.name
  policy_arn = data.aws_iam_policy.AWSGlueServiceRole.arn
}

# Glue db
resource "aws_glue_catalog_database" "svoe-glue-db" {
  name = "svoe_glue_db"
}

# Glue Crawler
resource "aws_glue_crawler" "svoe-test-crawler" {
  database_name = aws_glue_catalog_database.svoe-glue-db.name
  name          = "test_crawler"
  role          = aws_iam_role.glue-role.arn

  s3_target {
#    path = "s3://${var.datalake_s3_bucket_name}/${var.datalake_data_prefix}/"
    path = "s3://${var.datalake_s3_bucket_name}/"
  }
}

# Athena
resource "aws_s3_bucket" "athena-results" {
  bucket        = var.query_results_s3_bucket_name
  acl           = "private"
  force_destroy = true
}

resource "aws_athena_workgroup" "example-workgroup" {
  name          = "query_workgroup"
  force_destroy = true

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena-results.bucket}/query-results/"
    }
  }
}