variable "project_id" {
  description = "Project ID for these Beautiful Resources"
  type        = string
}
variable "name" {
  description = "Name of this Thang"
  type        = string
  default     = null
}
variable "description" {
  description = "Tell me more, Tell me more"
  type        = string
  default     = null
}
variable "create" {
  description = "Do or don't do, there is no try"
  type        = bool
  default     = true
}
variable "params" {
  description = "Parameters for this SSL Certificate & Key"
  type = object({
    domains     = optional(list(string))
    certificate = optional(string)
    private_key = optional(string)
    regional    = optional(bool, false)
    region      = optional(string)
    key = optional(object({
      algo   = optional(string, "RSA")
      length = optional(number, 2048)
    }))
    self_signed = optional(object({
      valid_hours = optional(number, 87600)
      valid_days  = optional(number, 3650)
      valid_years = optional(number, 10)
      cert_domain = optional(string, "localhost-localdomain")
      cert_org    = optional(string)
    }))
  })
  default = {}
}
