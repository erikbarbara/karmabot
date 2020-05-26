## Installation

### Install [Architect](http://arc.codes/)
```
npm i -g @architect/architect
```

### Create a Slack App
Minimally configure the app to start.

### Initiate and Deploy the App
```
arc init
arc env production SLACK_SIGNING_SECRET <SECRET_FROM_SLACK>
arc env production SLACK_OAUTH_ACCESS_TOKEN <TOKEN_FROM_SLACK>
arc deploy production 
```
Save the API Gateway URL provided at the end of the deploy step.

### Grant OAuth Permissions to the App
Grant the following OAuth permissions to your bot:
* `users:read`
* `chat:write`
* `channels:history`
You may be prompted to verify your app's URL. Use the API Gateway URL from the previous step to do so.

### Add the App to Slack
Add the app to your Slack workspace. Invite the bot to whichever channels you want to track karma.

## Usage
You can give karma to single word strings, specific people, or quoted phrases:
* * `@ebarbara++`
`tacos++`
* `"we like going serverless"++`

You can also load all the users so that mentions without a preceding `@` attribute karma to the intended person (`ebarbara++`):
* `shibboleth reload` will load usernames

You can also decrement karma:
* `COVID-19--`

Happy trails!