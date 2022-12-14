resource "google_compute_url_map" "default" {
  name = coalesce(var.name, "urlmap")
  dynamic "default_url_redirect" {
    for_each = var.redirect_to_https == true ? [0] : []
    content {
      https_redirect = var.redirect_to_https == true ? true : null
      strip_query    = var.redirect_to_https == true ? var.strip_query_on_redirect : null
    }
  }
  default_service = var.redirect_to_https == true ? null : var.default_backend
  dynamic "host_rule" {
    for_each = coalesce(var.route_rules, [])
    content {
      hosts        = host_rule.value.hostnames
      path_matcher = "path-matcher-${host_rule.key}"
    }
  }
  dynamic "path_matcher" {
    for_each = coalesce(var.route_rules, [])
    #content {
    #  name            = "path-matcher-${path_matcher.key}"
    #  default_service = path_matcher.value.backend
    #}
    content {
      name            = "path-matcher-${path_matcher.key}"
      default_service = coalesce(path_matcher.value["backend"], var.default_backend)
      dynamic "path_rule" {
        for_each = coalesce(path_matcher.value["path_rules"], [])
        content {
          paths   = path_rule.value["paths"]
          service = path_rule.value["backend"]
        }
      }
    }
  }
}


