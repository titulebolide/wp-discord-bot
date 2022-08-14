import datetime
import requests
import time
from urllib.parse import unquote
import markdownify
import config
import logging
import click

logging.basicConfig(level=logging.INFO)

refresh_rate = datetime.timedelta(hours=1)

content_max_length = 300

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
        name = resp['name']
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
    username = get_user_name(post['author'])
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

def send_msg(message, media_url):
    res = requests.post(
        config.DISCORD_WEBHOOK, 
        json = {
            'content':message,
            'embeds': [{
                "image": {
                    "url": media_url
                }
            }]
        }
    )
    print(res.text)

@click.command()
@click.option("--test/--no-test", default=False)
def main(test):
    logging.info("Starting")
    last_successful_fetch_date = datetime.datetime.now()
    already_seen_posts = []

    if not test:
        logging.debug("Fetching already existing articles")
        already_seen_posts.extend(
            [post['id'] for post in get_recent_posts(last_successful_fetch_date - datetime.timedelta(seconds=110))]
        )

    logging.info("Started")
    while True:
        if not test:
            time.sleep(refresh_rate.seconds)
        logging.info(f"Fetching {config.WEBSITE}")
        fetch_date = datetime.datetime.now()
        posts = []
        try:
            if not test:
                posts = get_recent_posts(last_successful_fetch_date - datetime.timedelta(seconds=100))
            else:
                posts = get_recent_posts(last_successful_fetch_date - datetime.timedelta(days=3))
        except Exception as e:
            logging.warning(e)
            continue
        last_successful_fetch_date = fetch_date
        for post in posts:
            if post['id'] in already_seen_posts:
                continue
            msg = create_msg(post)
            media_url = get_media_url(post['featured_media'])
            already_seen_posts.append(post['id'])
            logging.info(f"New article found : {markdownify.markdownify(post['title']['rendered'].encode('utf8'))}")
            if not test:
                send_msg(msg, media_url)
            else:
                logging.info(f"Skipping sending to discord the messsage :\n{msg}")
        
        if test:
            break
                
    logging.info("Exiting.")

if __name__ == "__main__":
    main()