# Management of SSL Certificates in Google Cloud Platform

- Existing 3rd party certs & keys to upload to Certificate Manager
- Google Managed Certificates
- Self-Signed Certs

## Default behavior

 Creates a 2048 RSA private key and Self-signed Cert for "localhost.localdomain", good for 10 years

## Usage Examples

### Self-Signed Certificate for myspace.com

```
project_id = "myproject-123456"
params = {
  self_signed = {
    cert_domain = "myspace.com"
  }
}
```

### Regional Self-Signed Certificate for myspace.com

```
project_id = "myproject-123456"
params = {
  regional = true
  region   = "us-west1"
  self_signed = {
    cert_domain = "myspace.com"
  }
}
```
