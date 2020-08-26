# Karmabot

A serverless Slack App for giving (and taking) karma.

> [ebarbara  9:32 PM] foo++

> [karmabot APP  9:32 PM] _New karma for_ **foo** `6`

## Installation

### Prerequisites

#### Install [Architect](http://arc.codes/)
```
npm i -g @architect/architect
```

#### Install and Configure AWS CLI
[Installing the AWS CLI version 2
](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)

[Configuration and credential file settings
](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)

### Create a Slack App
[Create new app](https://api.slack.com/apps)

Minimally configure the app to start. And add it to your Slack workspace.

Once installed visit https://api.slack.com/apps/<YOURAPPID>/install-on-team and grab the `Bot User OAuth Access Token`.

Similarly, visit https://api.slack.com/apps/<YOURAPPID>/general? and grab the `Signing Secret`.

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
* `groups:history` (optional if you want to use karmabot in private channels)

Enable event subscriptions.

You will be prompted to verify your app's URL. Use the API Gateway URL from the previous step to do so.

In addition, add the following bot events:

* `message:channels`
* `message:groups`

### Add the App to Slack
Add the app to your Slack workspace. Invite the bot to whichever channels you want to track karma.

## Usage
You can give karma to single word strings, specific people, or quoted phrases:
* `@ebarbara++`
* `tacos++`
* `"dragons love tacos"++`

You can also load all the users so that mentions without a preceding `@` attribute karma to the intended person (`ebarbara++`):
* `shibboleth reload` will load usernames

You can also decrement karma:
* `COVID-19--`

Happy trails!
