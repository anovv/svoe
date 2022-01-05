data "aws_iam_policy_document" "glue-assume-role-policy" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "extra-policy-document" {
  statement {
    actions = [
      "s3:GetBucketLocation", "s3:ListBucket", "s3:ListAllMyBuckets", "s3:GetBucketAcl", "s3:GetObject"]
    resources = [
      "arn:aws:s3:::${var.datalake_s3_bucket_name}",
      "arn:aws:s3:::${var.datalake_s3_bucket_name}/*"
    ]
  }
}

data "aws_iam_policy" "AWSGlueServiceRole" {
  arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}
