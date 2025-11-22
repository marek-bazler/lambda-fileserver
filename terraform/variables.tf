variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name prefix"
  type        = string
  default     = "fileserver"
}

variable "domain_name" {
  description = "Custom domain name for CloudFront"
  type        = string
  default     = "fileshare.bazlers.org"
}

variable "hosted_zone_id" {
  description = "Route53 hosted zone ID"
  type        = string
  default     = "Z04008502BKUSRFDXT5NP"
}
