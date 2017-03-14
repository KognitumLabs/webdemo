import os
import logging
import flask
import optparse
import tornado.wsgi
import tornado.httpserver
import requests
import urllib
import numpy as np
import cStringIO as StringIO
from PIL import Image, ImageOps, ImageDraw
import cv2

# Obtain the flask app object
app = flask.Flask(__name__)


@app.route('/')
def index():
    return flask.render_template('index.html', has_result=False)


@app.route('/compare', methods=['GET'])
def compare():
    image1 = flask.request.args.get('image1')
    image2 = flask.request.args.get('image2')
    detection = flask.request.args.get('detection_type', None) or False
    if not detection:
        pattern = 'http://{host}:{port}/detector?image1={url1}&image2={url2}&threshold=0.99'
        endpoint = pattern.format(host=os.environ.get('HOST', 'localhost'),
                                  port=os.environ.get('COMPARISON', '8080'),
                                  url1=image1,
                                  url2=image2)
    else:
        pattern = 'http://{host}:{port}/detector?image1={url1}&image2={url2}&threshold=0.99&detection_type={type}'
        endpoint = pattern.format(host=os.environ.get('HOST', 'localhost'),
                                  port=os.environ.get('COMPARISON', '8080'),
                                  url1=image1,
                                  url2=image2,
                                  type=detection)

    logging.info("Running {}".format(endpoint))
    response = requests.get(endpoint)
    if not response.ok:
        logging.info("Server error")
        return flask.render_template('index.html',
                                     has_result=True, result=(False,))

    data = response.json()
    logging.info("Response {}".format(data))
    img1 = embed_image_html(image1,
                            data['image1'].get('box'),
                            bool(data['image1']['is_document'][0]))

    img2 = embed_image_html(image2,
                            data['image2'].get('box'),
                            bool(data['image2']['is_document'][0]))

    return flask.render_template('index.html',
                                 has_result=True,
                                 result=(True, data.get('is_similar', False)),
                                 image1=img1,
                                 image2=img2)


def embed_image_html(url, box, has_document, alpha=0.4):
    string_buffer = StringIO.StringIO(urllib.urlopen(url).read())
    """Creates an image embedded in HTML base64 format."""
    image_pil = Image.open(string_buffer)
    if box:
        x1, y1, x2, y2 = box
        img = np.array(image_pil)
        color1 = img[y1:y2, x1:x2, :3]
        color2 = np.array([[0, 0, 255.]]) / 255.
        ncolor = (1 - alpha) * color1 + alpha * color2
        img[y1:y2, x1:x2, :3] = ncolor
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
        image_pil = Image.fromarray(img)

        # drawer = ImageDraw.Draw(image_pil)
        # drawer.rectangle((x1, y1, x2, y2), fill=None, outline=(255, 255, 255))
    image_pil = image_pil.resize((256, 256))
    string_buf = StringIO.StringIO()
    image_pil = ImageOps.expand(image_pil, border=20,
                                fill='green' if has_document else 'red')
    image_pil.save(string_buf, format='png')
    data = string_buf.getvalue().encode('base64').replace('\n', '')
    return 'data:image/png;base64,' + data


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
