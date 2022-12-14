variable "project_id" {
  type    = string
  default = null
}
variable "zone_name" {
  description = "The Google Zone Name (i.e. 'whatever-com')"
  type        = string
  default     = null
}
variable "dns_name" {
  description = "The DNS name of the domain (i.e. 'whatever.com.')"
  type        = string
}
variable "records" {
  type = list(object({
    name    = optional(string)
    type    = optional(string)
    ttl     = optional(number)
    rrdatas = optional(list(string))
  }))
  default = []
}
variable "default_ttl" {
  type    = number
  default = 300
}
