from flask import Flask

app = Flask(__name__, static_folder="client/build", static_url_path="")

from server.routes import *  # noqa: E402,F401,F403


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
