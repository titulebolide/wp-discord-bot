import datetime
import requests
import time
from urllib.parse import unquote
import markdownify
import config
import logging

logging.basicConfig(level=logging.INFO)

logging.info("Starting")

refresh_rate = datetime.timedelta(hours=1)
last_successful_fetch_date = datetime.datetime.now()
content_max_length = 300

already_seen_posts = []

def get_recent_posts(after_date):
    return requests.get(
        f"{config.WEBSITE}/wp-json/wp/v2/posts",
        json = {
            'after' : after_date.isoformat()
        }
    ).json()

def get_user_name(id):
    resp = requests.get(
        f"{config.WEBSITE}/wp-json/wp/v2/users/{id}",
    ).json()
    try:
        name = res['name']
    except IndexError:
        logging.warning("error for name")
        name = "?"
    return name

def get_media_url(id):
    resp = requests.get(
        f"{config.WEBSITE}/wp-json/wp/v2/media/{id}"
    ).json()
    try:
        url = resp['media_details']['sizes']['medium']['source_url']
    except IndexError:
        logging.warning("error for media url")
        url = ""
    return url

def create_msg(post):
    username = get_user(post['author'])['name']
    print(post['title']['rendered'])
    text = markdownify.markdownify(post['content']['rendered'].encode('utf8'))
    for i in range(3):
        text = text.replace('\n\n','\n')
    text = text.replace('\n', '\n> ').rstrip('>')
    if len(text) > content_max_length:
        text = text[:content_max_length].rstrip('.') + "..."
    print(text)
    message = f"""
[Nouvel article sur le site du CHVD par {username}]({post['link']})

> **{markdownify.markdownify(post['title']['rendered'].encode('utf8'))}**
> {text}
    """
    return message

def send_msg(message):
    res = requests.post(
        config.DISCORD_WEBHOOK, 
        json = {
            'content':message,
            'embeds': [{
                "image": {
                    "url": get_media_url(post['featured_media'])
                }
            }]
        }
    )
    print(res.text)

logging.debug("Fetching already existing articles")
already_seen_posts.extend(
    [post['id'] for post in get_recent_posts(last_successful_fetch_date - datetime.timedelta(seconds=110))]
)

logging.info("Started")

while True:
    time.sleep(refresh_rate.seconds)
    logging.info(f"Fetching {config.WEBSITE}")
    fetch_date = datetime.datetime.now()
    posts = []
    try:
        posts = get_recent_posts(last_successful_fetch_date - datetime.timedelta(seconds=100))
    except Exception as e:
        logging.warning(e)
        continue
    last_successful_fetch_date = fetch_date
    for post in posts:
        if post['id'] in already_seen_posts:
            continue
        msg = create_msg(post)
        already_seen_posts.append(post['id'])
        send_msg(msg)
    
logging.info("Exiting.")