import json
import logging
import random
import string

import feedparser
import mf2py
import requests
from flask import jsonify, request


def notify_subscribers(feed_item_url, hub_url, cursor, feed_item):
    fetch_last_item = cursor.execute(
        "SELECT last_url_fetched FROM feeds WHERE feed_url = ?", (hub_url,)
    ).fetchall()

    if len(fetch_last_item) > 0 and fetch_last_item[0][0] != feed_item_url:
        subscribers = cursor.execute(
            "SELECT * FROM subscriptions WHERE hub_topic = ?",
            (request.form.get("hub.url"),),
        ).fetchall()

        if len(fetch_last_item) > 0:
            cursor.execute(
                "UPDATE feeds SET last_url_fetched = ? WHERE feed_url = ?",
                (feed_item_url, hub_url),
            )
        else:
            cursor.execute(
                "INSERT INTO feeds (feed_url, last_url_fetched) VALUES (?, ?)",
                (hub_url, feed_item_url),
            )

        # send subscriber notification that content has changed
        for subscriber in subscribers:
            r = requests.post(
                subscriber[0],
                data=feed_item.text.encode("utf-8"),
                headers={
                    "Content-Type": feed_item.headers.get("content-type"),
                    "Link": feed_item.headers.get("link"),
                },
            )


def publish(cursor):
    # if hub.url form is a list
    if request.form.getlist("hub.url"):
        urls = request.form.getlist("hub.url")
    else:
        urls = [request.form.get("hub.url")]

    for url in urls:
        hub_url = url

        r = requests.get(hub_url)

        if r.status_code != 200:
            return jsonify({"message": "Invalid publish url."})

        if (
            "application/atom+xml" in r.headers["Content-Type"]
            or "application/rss+xml" in r.headers["Content-Type"]
        ):
            feed = feedparser.parse(r.text)

            # get most recent entry
            most_recent_entry = feed.entries[0]

            notify_subscribers(most_recent_entry["url"], hub_url, cursor, r)

        elif "text/html" in r.headers["Content-Type"]:
            feed_item = requests.get(hub_url)
            read_feed = mf2py.Parser(r.text)

            # most recent item in feed
            most_recent_item_json = read_feed.to_dict()

            # get first h-feed

            for item in most_recent_item_json["items"]:
                if type(item["type"]) == list and "h-feed" in item["type"]:
                    most_recent_item = item.get("children")
                elif type(item["type"]) == str and "h-feed" in item["type"]:
                    most_recent_item = item.get("children")

            if most_recent_item is not None:
                notify_subscribers(
                    most_recent_item[0]["properties"]["url"][0],
                    hub_url,
                    cursor,
                    feed_item,
                )

        elif "application/json" in r.headers["Content-Type"]:
            feed_item = requests.get(hub_url)
            feed_item_json = json.loads(feed_item.text)

            notify_subscribers(feed_item_json[0]["url"], hub_url, cursor, feed_item)

        elif "text/plain" in r.headers["Content-Type"]:
            feed_item = requests.get(hub_url)

            notify_subscribers(feed_item.url, hub_url, cursor, feed_item)

        logging.info("Received notification from hub: " + hub_url)

        return jsonify({"message": "Accepted"}), 202


def unsubscribe(subscription_exists, hub_callback, hub_topic, hub_mode, cursor):
    if len(subscription_exists) == 0:
        return jsonify({"message": "Subscription does not exist."})

    challenge = "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(30)
    )

    r = requests.get(
        hub_callback
        + "?mode=unsubscribe&hub.topic="
        + hub_topic
        + "&hub.challenge="
        + challenge
        + "&hub.mode="
        + hub_mode
    )

    if r.status_code != 200:
        return jsonify({"message": "Bad request."}), 400

    cursor.execute(
        "DELETE FROM subscriptions WHERE hub_callback = ? AND hub_topic = ?",
        (hub_callback, hub_topic),
    )

    logging.info("Unsubscribed from " + hub_topic)
    return jsonify({"message": "Accepted"}), 202


def subscribe(
    subscription_exists,
    hub_callback,
    hub_mode,
    hub_topic,
    hub_lease_seconds,
    hub_secret,
    cursor,
):
    if len(subscription_exists) > 0:
        cursor.execute(
            "DELETE FROM subscriptions WHERE hub_callback = ? AND hub_topic = ?",
            (hub_callback, hub_topic),
        )

    challenge = "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(30)
    )

    verify_request = requests.get(
        hub_callback
        + "?hub.mode=subscribe&hub.topic="
        + hub_topic
        + "&hub.challenge="
        + challenge
        + "&hub.lease_seconds="
        + str(hub_lease_seconds)
        + "&hub.mode"
        + hub_mode
    )

    if verify_request.status_code == 200:
        if verify_request.text and verify_request.text != challenge:
            return jsonify({"message": "Bad request."}), 400

        cursor.execute(
            """INSERT INTO subscriptions (
                hub_callback,
                hub_mode,
                hub_topic,
                hub_lease_seconds,
                hub_secret
            ) VALUES (?, ?, ?, ?, ?)""",
            (hub_callback, hub_mode, hub_topic, hub_lease_seconds, hub_secret),
        )

        logging.info("Subscribed to " + hub_topic)
        return jsonify({"message": "Accepted"}), 202
    else:
        return jsonify({"message": "Bad request."}), 400
