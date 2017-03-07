import os
import time
import logging
import flask
import werkzeug
import optparse
import tornado.wsgi
import tornado.httpserver
import numpy as np
import requests

# Obtain the flask app object
app = flask.Flask(__name__)

@app.route('/')
def index():
    return flask.render_template('index.html', has_result=False)


@app.route('/compare', methods=['GET'])
def compare():
    image1 = flask.request.args.get('image1')
    image2 = flask.request.args.get('image2')
    endpoint = 'http://{}:{}/detector?image1={}&image2={}&threshold=0.9'.format(os.environ.get('HOST', 'localhost'),
                                                                                os.environ.get('COMPARISON', '8080'),
                                                                                image1, image2)
    logging.info("Running {}".format(endpoint))
    response = requests.get(endpoint)
    if not response.ok:
        logging.info("Server error")
        return flask.render_template('index.html', has_result=False, result=(False,))

    data = response.json()
    logging.info("Response {}".format(data))
    return flask.render_template('index.html', has_result=True, 
                                  result=(True, data), image1=image1, image2=image2)


def start_tornado(app, port=5000):
    http_server = tornado.httpserver.HTTPServer(
        tornado.wsgi.WSGIContainer(app))
    http_server.listen(port)
    print("Tornado server starting on port {}".format(port))
    tornado.ioloop.IOLoop.instance().start()


def start_from_terminal(app):
    """
    Parse command line options and start the server.
    """
    parser = optparse.OptionParser()
    parser.add_option(
        '-d', '--debug',
        help="enable debug mode",
        action="store_true", default=False)
    parser.add_option(
        '-p', '--port',
        help="which port to serve content on",
        type='int', default=5000)
    parser.add_option(
        '-g', '--gpu',
        help="use gpu mode",
        action='store_true', default=False)

    opts, args = parser.parse_args()
    if opts.debug:
        app.run(debug=True, host='0.0.0.0', port=opts.port)
    else:
        start_tornado(app, opts.port)


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    start_from_terminal(app)
