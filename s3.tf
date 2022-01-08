resource aws_s3_bucket prices_bucket {
  bucket_prefix = "petrol-prices-bucket"
  force_destroy = true
  lifecycle_rule {
    enabled = true
      expiration {
      days = 1
    }
  }
}
