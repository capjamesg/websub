import logging
import sqlite3

import requests
from flask import (jsonify, redirect, render_template, request,
                   send_from_directory)
from flask.blueprints import Blueprint

import actions
import config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = Blueprint("app", __name__)


@app.route("/", methods=["GET", "POST"])
def websub_endpoint():
    if request.method == "POST":
        hub_callback = request.form.get("hub.callback")

        hub_mode = request.form.get("hub.mode")

        hub_topic = request.form.get("hub.topic")

        if hub_topic and not hub_topic.startswith(config.ME):
            return (
                jsonify(
                    {
                        "error": f"Only {config.ME} URLs are supported by this WebSub endpoint."
                    }
                ),
                400,
            )

        hub_lease_seconds = 3600000

        hub_secret = request.form.get("hub.secret")

        connection = sqlite3.connect("websub.db")

        if not hub_topic or not hub_mode:
            return jsonify({"error": "Bad request."}), 400

        with connection:
            cursor = connection.cursor()

            # check if subscription exists
            subscription_exists = cursor.execute(
                "SELECT * FROM subscriptions WHERE hub_callback = ? AND hub_topic = ?",
                (hub_callback, hub_topic),
            ).fetchall()

            if hub_mode == "subscribe":
                logging.info(f"Subscribing to {hub_topic}")

                if not hub_callback or not hub_topic:
                    return jsonify({"error": "Bad request."}), 400

                return actions.subscribe(
                    subscription_exists,
                    hub_callback,
                    hub_mode,
                    hub_topic,
                    hub_lease_seconds,
                    hub_secret,
                    cursor,
                )

            elif hub_mode == "unsubscribe":
                logging.info(f"Unsubscribing from {hub_topic}")

                return actions.unsubscribe(
                    subscription_exists, hub_callback, hub_topic, hub_mode, cursor
                )

            elif hub_mode == "publish":
                logging.info(f"Publishing to {hub_topic}")

                return actions.publish(hub_callback, hub_topic, hub_secret, cursor)

            return jsonify({"message": "Bad request."}), 400

    return render_template("index.html", title="James' WebSub Endpoint")


@app.route("/setup", methods=["GET", "POST"])
def setup():
    if config.SETUP != True:
        return redirect("/")

    return render_template("setup.html", title="WebSub Endpoint Setup")


@app.route("/forward", methods=["GET", "POST"])
def forward_to_subscriptions():
    r = requests.post("https://websub.jamesg.blog/", data=request.args)

    return r.text, 200


@app.route("/robots.txt")
def robots():
    return send_from_directory(app.static_folder, "robots.txt")
