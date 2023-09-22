import logging
import os
import signal
import uuid
from pathlib import Path

# Create an API specification instance
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec_webframeworks.flask import FlaskPlugin
from flask import Flask, jsonify, render_template, request
from flask_restx import Api, Resource, fields, reqparse
from flask_swagger_ui import get_swaggerui_blueprint

from audio import Stream as AudioStream
from helper import STREAMS, BackgroundThread, BackgroundThreadFactory

SWAGGER_URL = '/docs'  # URL for exposing Swagger UI (without trailing '/')
API_URL = 'http://localhost:5000/swagger.json'  # Our API url (can of course be a local resource)

spec = APISpec(
    title='Your API',
    version='1.0.0',
    openapi_version='3.0.2',
    plugins=[FlaskPlugin(), MarshmallowPlugin()],
)

def create_app():
    app = Flask(__name__)
    api = Api(app, doc='/v1', contact='jackovsky8@gmail.com', )

    stream_model = api.model('stream', {
        'stream_id': fields.String(),
        'url': fields.String(),
        'uri': fields.Url('stream_ep', absolute=True),
        'last_accessed': fields.DateTime()
    })
    streams_model = api.model('streams', {
        'streams': fields.List(fields.Nested(stream_model))
    })

    @api.route('/v1/streams/<string:stream_id>', endpoint='stream_ep')
    class Stream(Resource):
        @api.marshal_with(stream_model)
        def get(self, stream_id):
            return STREAMS[stream_id]
        @api.marshal_with(stream_model)
        def delete(self, stream_id):
            STREAMS[stream_id].stop_recording()
            return STREAMS.pop(stream_id)

    parser = reqparse.RequestParser()
    parser.add_argument('uri', type=str, help='URI of the stream')
    
    @api.route('/v1/streams', endpoint='streams_ep')
    class Streams(Resource):
        @api.marshal_with(streams_model)
        def get(self):
            return {'streams': list(STREAMS.values())}
        @api.marshal_with(stream_model)
        @api.expect(parser)
        def post(self):

            args = parser.parse_args(strict=True)

            new_uuid = str(uuid.uuid4())
            stream = AudioStream(args['uri'], new_uuid)
            stream.start_recording()
            STREAMS[new_uuid] = stream

            return stream
    
    # TODO Thread for deleting to old data and ending streams which are not used anymore
    # backgound_thread = BackgroundThreadFactory.create('streaming')

    # # this condition is needed to prevent creating duplicated thread in Flask debug mode
    # if not (app.debug or os.environ.get('FLASK_ENV') == 'development') or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    #     backgound_thread.start()

    #     original_handler = signal.getsignal(signal.SIGINT)

    #     def sigint_handler(signum, frame):
    #         backgound_thread.stop()

    #         # wait until thread is finished
    #         if backgound_thread.is_alive():
    #             backgound_thread.join()

    #         original_handler(signum, frame)

    #     try:
    #         signal.signal(signal.SIGINT, sigint_handler)
    #     except ValueError as e:
    #         logging.error(f'{e}. Continuing execution...')

    # https://pypi.org/project/flask-swagger-ui/
    # Call factory function to create our blueprint
    swaggerui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL,  # Swagger UI static files will be mapped to '{SWAGGER_URL}/dist/'
        API_URL,
        config={  # Swagger UI config overrides
            'app_name': "Radio Proxy"
        }
    )

    app.register_blueprint(swaggerui_blueprint)

    return app
