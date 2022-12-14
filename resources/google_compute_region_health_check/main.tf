resource "google_compute_region_health_check" "default" {
  count  = var.name == null ? 0 : 1
  name   = coalesce(var.name, local.default_name)
  region = var.region
  dynamic "tcp_health_check" {
    for_each = local.protocol != "HTTP" && local.protocol != "HTTPS" ? [0] : []
    content {
      port = var.port
    }
  }
  dynamic "http_health_check" {
    for_each = local.protocol == "HTTP" ? [0] : []
    content {
      port         = var.port
      request_path = var.request_path
      response     = var.response
    }
  }
  dynamic "https_health_check" {
    for_each = local.protocol == "HTTPS" ? [0] : []
    content {
      port         = var.port
      request_path = var.request_path
      response     = var.response
    }
  }
  #check_interval_sec = coalesce(var.interval, local.default_interval)
  #timeout_sec        = coalesce(var.timeout, local.default_timeout)
  check_interval_sec = var.interval
  timeout_sec        = var.timeout
  project            = var.project_id
}

locals {
  protocol         = upper(var.protocol)
  default_name     = "tcp-${var.port}"
  default_interval = 5
  default_timeout  = 5
}
