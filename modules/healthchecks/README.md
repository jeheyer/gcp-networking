# Management of Healthchecks for Google Cloud Platform whether they be:

- Global
- Regional
- Legacy
- TCP
- HTTP
- HTTPS

## Default behavior

Creates a randomly named global TCP healthcheck on port 80

## Usage examples

### Global TCP Healthcheck on port 25

```
project_id = "project-123456"
name        = "smtp"
description = "A basic healthcheck for the mail relays"
params = {
  port = 25
}
```

### Global HTTP Healthcheck on nonstandard port at nonstandard interval

```
project_id = "myproject-123456"
name       = "gunicorn"
params = {
  protocol = "http"
  port     = 8081
  interval = 20
}
```

### Global HTTP Healthcheck with custom request / response

```
project_id = "myproject-123456"
name       = "apache"
params = {
  protocol     = "http"
  type         = "http"
  request_path = "/manual/en/index.html"
  response     = "Apache2"
}
```

### Regional TCP Healthcheck

```
project_id = "myproject-123456"
name       = "werkzeug"
params = {
  protocol  = "tcp"
  port      = 5000
  regional  = true
  region    = "europe-west3"
}
```

## Outputs


- name
- id 
- self_link
