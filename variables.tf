variable "project_id" {
  type = string
}
variable "region" {
  type    = string
  default = "us-central1"
}
variable "network_name" {
  type    = string
  default = "default"
}
variable "subnet_name" {
  type    = string
  default = "default"
}
variable "subnetwork_project_id" {
  type    = string
  default = null
}
variable "services" {
  type = map(object({
    ingress_traffic = optional(list(object({
      protocol = optional(string, "tcp")
      ports    = optional(list(number), [])
    })))
    egress_traffic = optional(list(object({
      protocol = optional(string, "tcp")
      ports    = optional(list(number), [])
    })))
    service_account_email  = string
    service_account_scopes = optional(list(string), ["cloud-platform"])
    image_project          = optional(string, "debian-cloud")
    image                  = optional(string, "debian-10")
    startup_script         = optional(string)
    network_tags           = optional(list(string), [])
    machine_type           = optional(string, "g1-small")
    disk_size_gb           = optional(number, 20)
    disk_type              = optional(string, "pd-ssd")
  }))
  default = {}
}

