#!/usr/bin/env python3

from quart import Quart, jsonify, render_template, request, Response, session
from traceback import format_exc
from main import get_version
from rancid import main

RESPONSE_HEADERS = {'Cache-Control': "no-cache, no-store"}
CONTENT_TYPE = "text/plain"

app = Quart(__name__)
app.secret_key = "abc"


@app.route("/version")
async def _version():

    try:
        _ = await get_version(vars(request))
        return jsonify(_), RESPONSE_HEADERS
    except Exception as e:
        return Response(format_exc(), status=500, content_type=CONTENT_TYPE)


@app.route("/rancid")
async def _rancid():

    try:
        _ = await main()
        return jsonify(_), RESPONSE_HEADERS
    except Exception as e:
        return Response(format_exc(), status=500, content_type=CONTENT_TYPE)


@app.route("/quota_check")
async def _quota_check():

    try:
        return jsonify() #get_quota_data())
    except Exception as e:
        return Response(format_exc(), status=500, content_type=CONTENT_TYPE)


if __name__ == '__main__':
    app.run(debug=True)
