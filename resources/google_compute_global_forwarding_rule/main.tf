resource "google_compute_global_forwarding_rule" "default" {
  name                  = coalesce(var.name, "fwdrule")
  network               = var.vpc_network_name
  ip_address            = var.ip_address
  port_range            = var.port_range
  target                = var.tproxy_id
  load_balancing_scheme = var.lb_scheme
  project               = var.project_id
}

