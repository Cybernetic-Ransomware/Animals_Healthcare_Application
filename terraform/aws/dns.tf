# Fully gated behind var.manage_dns (default false). Inert until both a
# real, owned domain (var.domain_name) and manage_dns = true are supplied —
# see kubernetes/README-aws.md. Without this, the aws overlay ships with a
# placeholder host and no valid ALB certificate, which is a safe resting
# state, not a broken one.

data "aws_route53_zone" "this" {
  count = var.manage_dns ? 1 : 0
  name  = var.domain_name
}

resource "aws_acm_certificate" "this" {
  count             = var.manage_dns ? 1 : 0
  domain_name       = "ahc.${var.domain_name}"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "cert_validation" {
  for_each = var.manage_dns ? {
    for dvo in aws_acm_certificate.this[0].domain_validation_options : dvo.domain_name => dvo
  } : {}

  zone_id = data.aws_route53_zone.this[0].zone_id
  name    = each.value.resource_record_name
  type    = each.value.resource_record_type
  records = [each.value.resource_record_value]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "this" {
  count                   = var.manage_dns ? 1 : 0
  certificate_arn         = aws_acm_certificate.this[0].arn
  validation_record_fqdns = [for r in aws_route53_record.cert_validation : r.fqdn]
}
