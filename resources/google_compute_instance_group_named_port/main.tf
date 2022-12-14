resource "google_compute_instance_group_named_port" "default" {
  count = length(var.instance_groups)
  name  = coalesce(var.name, local.name)
  group = "projects/${var.project_id}/zones/${var.instance_groups_zones[count.index]}/instanceGroups/${var.instance_groups[count.index]}"
  port  = var.port
}

locals {
  name     = var.protocol != null ? "port-${var.port}-${local.protocol}" : "port-${var.port}"
  protocol = lower(var.protocol)
}
