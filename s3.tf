resource aws_s3_bucket prices_bucket {
  bucket_prefix = "petrol-prices-bucket"
  force_destroy = true
}

resource aws_s3_bucket_lifecycle_configuration prices_bucket {
  bucket = aws_s3_bucket.prices_bucket.id
  rule {
    id = "rule-1"
    expiration {
      days = 1
    }
    status = "Enabled"
  }
}
