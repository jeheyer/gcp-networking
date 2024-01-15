from flask import Flask, jsonify, render_template, request, Response, session
from asyncio import run
from traceback import format_exc
from main import get_version
from rancid import main


app = Flask(__name__, static_url_path='/static')

RESPONSE_HEADERS = {'Cache-Control': "no-cache, no-store"}
CONTENT_TYPE = "text/plain"


@app.route("/version")
def _version():

    try:
        _ = run(get_version(request))
        return jsonify(_), RESPONSE_HEADERS
    except Exception as e:
        return Response(format(e), status=500, content_type=CONTENT_TYPE)


@app.route("/rancid")
async def _rancid():

    try:
        _ = await main()
        return jsonify(_), RESPONSE_HEADERS
    except Exception as e:
        return Response(format_exc(), status=500, content_type=CONTENT_TYPE)


@app.route("/")
def _root():
    try:
        _ = {} #run(main())
        return jsonify(_), RESPONSE_HEADERS
    except Exception as e:
        return Response(format(e), 500, content_type=CONTENT_TYPE)


if __name__ == '__main__':
    app.run(debug=True)
