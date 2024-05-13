import re
import os
import yt_dlp
import requests
from duckduckgo_search import DDGS
ddgs = DDGS()


def clean_song_name(text):
    # to shorten song name
    text = re.split(r"[-|]", text)[0].strip()

    # to escape reserved ssml characters
    # https://docs.aws.amazon.com/polly/latest/dg/escapees.html
    replacements = {
        '"': '&quot;',
        '&': '&amp;',
        "'": '&apos;',
        '<': '&lt;',
        '>': '&gt;'
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)

    return text

# time efficient - 0.5s improvement over 'search'
def search_ddgs(query):
    info_dict = {}
    search_string = f"{query} song"
    results = ddgs.videos(search_string, license_videos='youtube', max_results=1)
    if results:
        url = results[0]['content']
        info_dict = get_info_by_id(url)
    return info_dict

def search(query):
    info_dict = {}
    ydl_opts = {
        # "extractor_args": {"youtube": {"player_client": ["web"]}},
        'noplaylist': True,
        'default_search': 'ytsearch1',  # Search on YouTube
        'format': 'bestaudio/best',    # Choose the best audio quality
        'quiet': True                  # Suppress logging output
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        results = ydl.extract_info(query, download=False)['entries']
        if results:
            # Extract the first video from the search results
            video = results[0]
            info_dict = {
                'id': video['id'],
                'title': video['title'],
                'name': clean_song_name(video['title']),
                'thumbnail': video['thumbnail'],
                'url': video['url'],
            }
    return info_dict

def get_info_by_id(id):
    ydl_opts = {
        # "cachedir": False,
        # "extractor_args": {"youtube": {"player_client": ["web"]}},
        'format': 'bestaudio/best',    # Choose the best audio quality
        'quiet': True                  # Suppress logging output
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        video = ydl.extract_info(id, download=False)
        info_dict = {
            'id': video['id'],
            'title': video['title'],
            'name': clean_song_name(video['title']),
            'thumbnail': video['thumbnail'],
            'url': video['url']
        }
    return info_dict

def get_suggested_video_info(id):
    info_dict = {}
    url = "https://youtube-v31.p.rapidapi.com/search"
    querystring = {
        "relatedToVideoId":id,
        "part":"id",
        "type":"video",
        "maxResults":"1"
        }

    headers = {
        "X-RapidAPI-Key": os.environ['RAPID_API_KEY'],
        "X-RapidAPI-Host": "youtube-v31.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code == 200:
        suggested_vid_id = response.json()['items'][0]['id']['videoId']
        info_dict = get_info_by_id(suggested_vid_id)
    return info_dict