@app
karmabot

@http
post /

@tables
karma
  PointInTimeRecovery true
  encrypt true
  entity *String

users
  encrypt true
  id *String

userids
  encrypt true
  name *String

events
  encrypt true
  id *String
  ttl TTL

@aws
profile default
region us-east-1
runtime python3.7
timeout 20
