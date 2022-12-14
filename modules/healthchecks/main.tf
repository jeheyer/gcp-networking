locals {
  create_hc       = coalesce(var.create, true) && local.is_global || local.is_regional || local.is_legacy
  name            = local.use_random_name ? try(lower(one(random_string.name).result), null) : lower(var.name)
  use_random_name = var.name == null ? true : false
  description     = try(lower(var.description), null)
  is_regional     = var.params.regional ? true : false
  is_global       = !var.params.regional ? true : false
  is_legacy       = var.params.legacy == true ? true : false
  protocol        = upper(var.params.protocol)
  is_http         = local.protocol == "HTTP" ? true : false
  is_https        = local.protocol == "HTTPS" ? true : false
}

# Generate a random name, if required
resource "random_string" "name" {
  count   = local.use_random_name ? 1 : 0
  length  = 31
  special = false
}

# Global Health Checks
resource "google_compute_health_check" "default" {
  count       = local.create_hc && local.is_global && !local.is_legacy ? 1 : 0
  name        = local.name
  description = local.description
  dynamic "tcp_health_check" {
    for_each = local.protocol == "TCP" ? [true] : []
    content {
      port = var.params.port
    }
  }
  dynamic "http_health_check" {
    for_each = local.protocol == "HTTP" ? [true] : []
    content {
      port         = var.params.port
      request_path = var.params.request_path
      response     = var.params.response
    }
  }
  dynamic "https_health_check" {
    for_each = local.protocol == "HTTPS" ? [true] : []
    content {
      port         = var.params.port
      request_path = var.params.request_path
      response     = var.params.response
    }
  }
  check_interval_sec  = var.params.interval
  timeout_sec         = var.params.timeout
  healthy_threshold   = var.params.healthy_threshold
  unhealthy_threshold = var.params.unhealthy_threshold
  log_config {
    enable = var.params.logging
  }
  project = var.project_id
}

# Regional Health Checks
resource "google_compute_region_health_check" "default" {
  count       = local.create_hc && local.is_regional && !local.is_legacy ? 1 : 0
  name        = local.name
  description = local.description
  region      = var.params.region
  dynamic "tcp_health_check" {
    for_each = local.protocol == "TCP" ? [true] : []
    content {
      port = var.params.port
    }
  }
  dynamic "http_health_check" {
    for_each = local.protocol == "HTTP" ? [true] : []
    content {
      port         = var.params.port
      request_path = var.params.request_path
      response     = var.params.response
    }
  }
  dynamic "https_health_check" {
    for_each = local.protocol == "HTTPS" ? [true] : []
    content {
      port         = var.params.port
      request_path = var.params.request_path
      response     = var.params.response
    }
  }
  check_interval_sec  = var.params.interval
  timeout_sec         = var.params.timeout
  healthy_threshold   = var.params.healthy_threshold
  unhealthy_threshold = var.params.unhealthy_threshold
  log_config {
    enable = var.params.logging
  }
  project = var.project_id
}

# Legacy HTTP Health Check
resource "google_compute_http_health_check" "default" {
  count              = local.create_hc && local.is_legacy && local.is_http ? 1 : 0
  name               = local.name
  description        = local.description
  port               = var.params.port
  check_interval_sec = var.params.interval
  timeout_sec        = var.params.timeout
  project            = var.project_id
}

# Legacy HTTPS Health Check
resource "google_compute_https_health_check" "default" {
  count              = local.create_hc && local.is_legacy && local.is_https ? 1 : 0
  name               = local.name
  description        = local.description
  port               = var.params.port
  check_interval_sec = var.params.interval
  timeout_sec        = var.params.timeout
  project            = var.project_id
}

