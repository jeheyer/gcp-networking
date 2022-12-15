locals {
  subnetwork_project = coalesce(var.subnetwork_project_id, var.project_id)
  # Create health check object to be used for MIG and iLB backend
  health_check = {
    for k, v in var.services : k => {
      name                = k
      type                = "tcp"
      port                = v.ingress_traffic[0].ports[0]
      check_interval_sec  = 15
      timeout_sec         = 5
      healthy_threshold   = 2
      unhealthy_threshold = 2
      response            = ""
      proxy_header        = "NONE"
      port_name           = null
      request             = null
      request_path        = null
      host                = ""
      enable_log          = false
      initial_delay_sec   = 60
    }
  }
}

/*
 Create Instance Template
 https://github.com/terraform-google-modules/terraform-google-vm/tree/master/modules/instance_template
*/
module "instance-template" {
  source             = "terraform-google-modules/vm/google//modules/instance_template"
  version            = "~> 7.9"
  for_each           = var.services
  project_id         = var.project_id
  subnetwork_project = var.project_id
  network            = var.network_name
  subnetwork         = var.subnet_name
  name_prefix        = each.key
  machine_type       = each.value.machine_type
  disk_size_gb       = each.value.disk_size_gb
  disk_type          = each.value.disk_type
  service_account = {
    email  = each.value.service_account_email
    scopes = each.value.service_account_scopes
  }
  source_image_project = each.value.image_project
  source_image         = each.value.image
  startup_script       = each.value.startup_script
  region               = var.region
}

/*
  Create Managed Instance Group
  https://github.com/terraform-google-modules/terraform-google-vm/tree/master/modules/mig
*/
module "mig" {
  source              = "terraform-google-modules/vm/google//modules/mig"
  version             = "~> 7.9"
  for_each            = var.services
  project_id          = var.project_id
  subnetwork_project  = var.project_id
  mig_name            = "${each.key}-${var.region}"
  region              = var.region
  hostname            = "${each.key}-${var.region}"
  instance_template   = module.instance-template[each.key].self_link
  network             = var.network_name
  subnetwork          = var.subnet_name
  health_check_name   = "${each.key}-${var.region}"
  health_check        = local.health_check[each.key]
  autoscaling_enabled = true
  min_replicas        = 2
  max_replicas        = 9
  cooldown_period     = 120
  autoscaling_mode    = "ON"
  autoscaling_cpu     = []
}

/*
 Create Internal TCP/UDP Load Balancer
 https://github.com/terraform-google-modules/terraform-google-lb-internal/
*/
module "ilb" {
  source       = "GoogleCloudPlatform/lb-internal/google"
  version      = "~> 5.0"
  for_each     = var.services
  name         = "${each.key}-${var.region}"
  region       = var.region
  ports        = flatten([for k, v in each.value.ingress_traffic : v.ports])
  network      = var.network_name
  subnetwork   = var.subnet_name
  health_check = local.health_check[each.key]
  source_tags  = []
  target_tags  = []
  backends = [{
    group       = module.mig[each.key].instance_group
    description = "Managed Regional Instance Group"
  }]
  session_affinity             = "CLIENT_IP_PORT_PROTO"
  create_health_check_firewall = false
  create_backend_firewall      = false
  project                      = var.project_id
}

