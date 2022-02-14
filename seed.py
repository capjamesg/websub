import sqlite3

connection = sqlite3.connect("websub.db")

with connection:
    cursor = connection.cursor()

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS subscriptions(
        hub_callback text,
        hub_mode text,
        hub_topic text,
        hub_lease_seconds text,
        hub_secret
    )"""
    )

    print("created subscriptions table in database")

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS feeds(
        feed_url text,
        last_url_fetched text
    )"""
    )

    print("created feeds table in database")

print("the database is now ready for use")
print("run app.py to execute the flask websub server")
