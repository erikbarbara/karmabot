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
  name *String

@aws
profile default
region us-east-2
runtime python3.7