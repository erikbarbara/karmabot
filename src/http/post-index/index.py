import base64
import hashlib
import hmac
import json
import re
import time

from os import environ
from urllib import parse, request

import arc.tables

SLACK_API_BASE_URL = 'https://slack.com/api/'
SLACK_OAUTH_ACCESS_TOKEN = environ['SLACK_OAUTH_ACCESS_TOKEN']
SLACK_SIGNING_SECRET = environ['SLACK_SIGNING_SECRET']

SPECIAL_KARMA = {
    -1: ':yoda: Fear is the path to the dark side. Fear leads to anger. Anger leads to hate. Hate leads to suffering. :darth_vader:',
    1: ':one: The journey of :1000: karma begins with one.',
    8: 'That\'s one byte of karma. Mazel tov!',
    20: 'Twenty karma! You\'re cooking with gas now.',
    42: 'Ah, the answer. But what is the question?',
    50: 'Look at you, you helpful person.',
    84: ':happymac: On January 24th Apple Computer will introduce Macintosh...',
    100: ':whoa_keanu: Welcome to the :100: club!',
    1000: ':1000: Lifer. You can check out anytime you want, but you can never leave.',
}

# https://api.slack.com/authentication/verifying-requests-from-slack#a_recipe_for_security
def validate_slack_request(headers, body):
    if 'x-slack-request-timestamp' not in headers or 'x-slack-signature' not in headers:
        return False
    timestamp = headers['x-slack-request-timestamp']
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False
    sig_basestring = 'v0:' + timestamp + ':' + body
    req_hash = 'v0=' + hmac.new(str.encode(
        SLACK_SIGNING_SECRET),
        str.encode(sig_basestring), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(req_hash, headers['x-slack-signature']):
        return False
    return True

# https://api.slack.com/web#basics
def _slack_api_call(url, data):
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data['token'] = SLACK_OAUTH_ACCESS_TOKEN
    data = parse.urlencode(data).encode('utf-8')
    slack_req = request.Request(
            url, 
            data=data, 
            method='POST',
            headers=headers,
    )
    return request.urlopen(slack_req).read()

def post_slack_message(channel, text):
    data = {
        'channel': channel,
        'text': text,
    }
    _slack_api_call('{}{}'.format(SLACK_API_BASE_URL, 'chat.postMessage'), data)

def get_slack_users_list(cursor=None):
    users = []
    data = {}
    if cursor:
        data['cursor'] = cursor
    res = json.loads(_slack_api_call('{}{}'.format(SLACK_API_BASE_URL, 'users.list'), data).decode('utf-8'))
    if res.get('members'):
        users += res['members']
    if res.get('response_metadata', {}).get('next_cursor', None):
        users += get_slack_users_list(res['response_metadata']['next_cursor'])
    return users

def is_slack_user_id(s):
    return re.match('<@((U|W)\w+)>', s)

def handler(req, context):
    body = req.get('body', '')
    if not body:
        body = '{}'
    if req.get('isBase64Encoded'):
        # decode but don't parse to json before validating the signature
        body = base64.b64decode(body).decode('utf-8')

    # validate signature
    if not validate_slack_request(req.get('headers'), body):
        return {'statusCode': 401}

    body = json.loads(body)

    # https://api.slack.com/events/url_verification
    if body and 'challenge' in body:
        return {
            'headers': {
                'cache-control': 'no-cache, no-store, must-revalidate, max-age=0, s-maxage=0',
                'content-type': 'text/json; charset=utf8'
            },
            'statusCode': 200,
            'body': json.dumps({'challenge': body['challenge']})
        }

    event = body.get('event', {})
    event_bot_id = event.get('bot_id', None)
    event_channel = event.get('channel', None)
    event_type = event.get('type', None)    
    event_subtype = event.get('subtype', None)
    event_text = event.get('text', None)
    event_user = '<@{}>'.format(event.get('user', None))
    event_timestamp = event.get('ts', None)
    event_id = f'{event_channel}-{event_timestamp}'
    
    # only respond to messages that aren't from bots, and that contain ++
    if event_type == 'message' and (event_subtype != 'bot_message' and not event_bot_id):
        events_table = arc.tables.table(tablename='events')
        ddb_event = events_table.get_item(Key={'id': event_id})
        if 'Item' not in ddb_event:
            item = {
                'id': event_id,
                'ttl': int(time.time()) + 86400
            }
            events_table.put_item(Item=item)

            event_text_matches = [re.sub('\"|“|”', '', m[0]) for m in re.findall(r'((\S+|".*"|“.*”)[ ]?(\+\+))', str(event_text))]
            if event_text_matches:
                for i in event_text_matches:
                    delta = 1
                    i = re.sub(' ?(\+\+)', '', i)

                    # look up potential users
                    if is_slack_user_id(i):
                        user_id = i
                        users_table = arc.tables.table(tablename='users')
                        ddb_item = users_table.get_item(Key={'id': i})
                        if 'Item' in ddb_item:
                            item = ddb_item['Item']
                            i = item['name']
                    else:
                        i = i.lower()
                        user_id = None
                        userids_table = arc.tables.table(tablename='userids')
                        ddb_item = userids_table.get_item(Key={'name': i})
                        if 'Item' in ddb_item:
                            item = ddb_item['Item']
                            user_id = item['id']

                    # don't allow for modification of self-karma 
                    if user_id and user_id == event_user:
                        response_text = '{}, {}'.format('Let go of your ego' if delta>0 else 'Hang on to your ego', event_user)
                    # get and modify karma
                    else:
                        karma_table = arc.tables.table(tablename='karma')
                        ddb_item = karma_table.get_item(Key={'entity': i})
                        item = {}
                        if 'Item' in ddb_item:
                            item = ddb_item['Item']
                            item['karma'] += delta
                        else:
                            item = {
                                'entity': i,
                                'karma': delta
                            }
                        karma_table.put_item(Item=item)
                        response_text = ':karmabot: _New karma for_ *{}* `{}`'.format(i, item['karma'])
                        if SPECIAL_KARMA.get(item['karma']):
                            response_text += f"\n{SPECIAL_KARMA[item['karma']]}"
                    # post to channel
                    post_slack_message(event_channel, response_text)
            # display karma
            elif event_text.startswith('karma '):
                entity = event_text[len('karma '):]
                karma_table = arc.tables.table(tablename='karma')
                ddb_item = karma_table.get_item(Key={'entity': entity})
                if 'Item' in ddb_item:
                    item = ddb_item['Item']
                    karma = item['karma']
                    response_text = f':karmabot: _Karma for_ *{entity}* `{karma}`'
                else:
                    response_text = f':karmabot: _No karma for_ *{entity}*'
                post_slack_message(event_channel, response_text)
            # reload all users
            elif event_text == 'shibboleth reload':
                users = get_slack_users_list()
                users_table = arc.tables.table(tablename='users')
                userids_table = arc.tables.table(tablename='userids')
                for t in (users_table, userids_table):
                    with t.batch_writer() as batch:
                        for i in users:
                            if i.get('name') and i.get('id'):
                                item = {
                                    'name': i['name'],
                                    'id': '<@{}>'.format(i['id']),
                                }
                                batch.put_item(Item=item)
                post_slack_message(event_channel, 'Reloaded {} users'.format(len(users)))
    return {'statusCode': 200}
