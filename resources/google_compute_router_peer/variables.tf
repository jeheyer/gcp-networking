variable "project_id" {
  description = "Project ID of our VPC network"
  type        = string
  default     = null
}
variable "name" {
  description = "Name for the BGP Session"
  type        = string
  default     = null
}
variable "name_prefix" {
  description = "Naming prefix for each BGP session"
  type        = string
  default     = null
}
variable "region" {
  description = "GCP region name"
  type        = string
}
variable "cloud_router_name" {
  description = "Cloud Router name"
  type        = string
  default     = null
}
variable "peer_vpn_gateway_name" {
  description = "Name of the Peer (External) VPN Gateway"
  type        = string
  default     = null
}
variable "peer_bgp_asn" {
  description = "BGP AS Number for all sessions (can also be set for each peer)"
  type        = number
  default     = null
}
variable "advertised_priority" {
  description = "Base BGP MED value for route advertisements"
  type        = number
  default     = 100
}
variable "advertised_groups" {
  description = "Groups to advertise"
  type        = list(string)
  default     = ["ALL_SUBNETS"]
}
variable "advertised_ip_ranges" {
  description = "List of custom prefixes to advertise"
  type        = list(string)
  default     = null
}
variable "enable_bfd" {
  description = "Support BFD"
  type        = bool
  default     = false
}
variable "bfd_parameters" {
  description = "BFD transmit, receive, and multiplier values"
  type        = list(number)
  default     = [1000, 1000, 5]
}
variable "enabled" {
  description = "Enable BGP for all peers"
  type        = bool
  default     = true
}
variable "bgp_peers" {
  type = list(object({
    bgp_peer_ip          = string
    name                 = optional(string)
    interface_name       = optional(string)
    bgp_name             = optional(string)
    peer_bgp_asn         = optional(number)
    advertised_priority  = optional(number)
    advertised_groups    = optional(list(string))
    advertised_ip_ranges = optional(list(string))
    enable_bfd           = optional(bool)
    enabled              = optional(bool)
  }))
  description = "Parameters for individual BGP Session"
}
