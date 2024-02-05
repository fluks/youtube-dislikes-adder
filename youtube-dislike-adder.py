#!/usr/bin/env python

import os
import re
from time import sleep

import google.oauth2.credentials

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret.
CLIENT_SECRETS_FILE = "client_secret.json"

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'
WAIT_IN_BETWEEN = 60 * 15

def get_authenticated_service():
  flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
  credentials = flow.run_console()
  return build(API_SERVICE_NAME, API_VERSION, credentials = credentials)

def get_my_videos_list(service):
    r = service.channels().list(mine=True, part='contentDetails').execute()
    for channel in r['items']:
        return channel['contentDetails']['relatedPlaylists']['uploads']

    return None

def get_dislikes(video_id, video_stats):
    for stat in video_stats:
        if video_id == stat['id']:
            return stat['statistics']['dislikeCount']

def add_dislikes(description, dislikes):
    return re.sub(r'(( |\n\n)Dislikes: \d+)?$', '\n\nDislikes: ' + str(dislikes), description)

def get_categoryId(video_id, video_stats):
    for stat in video_stats:
        if video_id == stat['id']:
            return stat['snippet']['categoryId']

def get_dislikes_from_description(description):
    m = re.search(r'( |\n\n)Dislikes: (?P<n>\d+)$', description)
    if not m:
        return ''
    return m.group('n')

def add_dislikes_to_descriptions(service, list_id):
    playlistitems_list_response = service.playlistItems().list(
        playlistId=list_id,
        part='snippet',
    ).execute()

    video_ids = []
    for playlist_item in playlistitems_list_response['items']:
        video_ids.append(playlist_item['snippet']['resourceId']['videoId'])
    video_stats = service.videos().list(id=','.join(video_ids), part='statistics,snippet').execute()['items']

    for playlist_item in playlistitems_list_response['items']:
        video_id = playlist_item['snippet']['resourceId']['videoId']
        dislikes = get_dislikes(video_id, video_stats)
        if dislikes == get_dislikes_from_description(playlist_item['snippet']['description']):
            continue
        description = add_dislikes(playlist_item['snippet']['description'], dislikes)
        playlist_item['snippet']['description'] = description
        playlist_item['snippet']['categoryId'] = get_categoryId(video_id, video_stats)

        service.videos().update(
            part='snippet',
            body=dict(
                snippet=playlist_item['snippet'],
                id=video_id,
            ),
        ).execute()

if __name__ == '__main__':
# When running locally, disable OAuthlib's HTTPs verification. When
# running in production *do not* leave this option enabled.
    #os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    service = get_authenticated_service()
    while True:
        list_id = get_my_videos_list(service)
        if list_id:
            add_dislikes_to_descriptions(service, list_id)
        sleep(WAIT_IN_BETWEEN)
