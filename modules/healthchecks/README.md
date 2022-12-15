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

### TCP Healthcheck on port 25

```
project_id = "project-123456"
name = "smtp"
params = {
  port = 25
}
```

### Generic HTTP Healtcheck on nonstandard port at nonstandard interval

```
project_id = "myproject-123456"
name = "gunicorn"
params = {
  type = "http"
  port = 8081
  interval = 20
}
```

