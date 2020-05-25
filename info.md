# Sjöfartsverket integration

## Installation/Configuration:

Add the following to resources in your sensors.yaml:

```yaml
- platform: sjofartsverket
  location: 123
```

Or if you want multiple locations

```yaml
- platform: sjofartsverket
  location: 123,456,789
```

Replace location with number from from url from http://vivadisplay.sjofartsverket.se (after selecting station)
