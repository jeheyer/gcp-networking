resource "google_compute_router_nat" "default" {
  project                            = var.project_id
  name                               = coalesce(var.name, local.name)
  router                             = coalesce(var.cloud_router_name, local.cloud_router_name)
  region                             = var.region
  nat_ip_allocate_option             = var.use_static_ip == true ? "MANUAL_ONLY" : "AUTO_ONLY"
  nat_ips                            = var.use_static_ip == true ? var.nat_ips : []
  source_subnetwork_ip_ranges_to_nat = length(var.subnets) > 0 ? "LIST_OF_SUBNETWORKS" : "ALL_SUBNETWORKS_ALL_IP_RANGES"
  dynamic "subnetwork" {
    for_each = var.subnets
    content {
      name                    = subnetwork.value
      source_ip_ranges_to_nat = ["ALL_IP_RANGES"]
    }
  }
  min_ports_per_vm                    = coalesce(var.min_ports_per_vm, var.enable_dpa == true ? 32 : 64)
  max_ports_per_vm                    = var.enable_dpa == true ? coalesce(var.max_ports_per_vm, 65536) : null
  enable_dynamic_port_allocation      = var.enable_dpa
  enable_endpoint_independent_mapping = var.enable_eim
  log_config {
    enable = lower(var.log_type) != "none" ? true : false
    filter = var.log_type != null ? lookup(local.log_filter, lower(var.log_type), local.default_log_filter) : local.default_log_filter
  }
  udp_idle_timeout_sec             = var.timeouts[0]
  tcp_established_idle_timeout_sec = var.timeouts[1]
  tcp_transitory_idle_timeout_sec  = var.timeouts[2]
  icmp_idle_timeout_sec            = var.timeouts[3]
}

locals {
  name              = "${var.vpc_network_name}-${var.region}"
  cloud_router_name = "${var.vpc_network_name}-${var.region}"
  log_filter = {
    "errors"       = "ERRORS_ONLY"
    "translations" = "TRANSLATIONS_ONLY"
    "all"          = "ALL"
  }
  default_log_filter = "ERRORS_ONLY"
}
