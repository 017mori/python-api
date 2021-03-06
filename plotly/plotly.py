"""
plotly
======

A module that contains the plotly class, a liaison between the user
and ploty's servers.

1. get DEFAULT_PLOT_OPTIONS for options

2. update plot_options with .plotly/ dir

3. update plot_options with _plot_options

4. update plot_options with kwargs!

"""
import requests
import json
import warnings
import httplib
from copy import copy
from . import utils

import tools
from . import exceptions

from .version import __version__

_credentials = dict()

_plot_options = dict()

_plotly_url = 'https://plot.ly/clientresp'


### _credentials stuff ###

def sign_in(username, api_key):
    """Set module-scoped _credentials for session. Verify with plotly."""
    global _credentials
    _credentials['username'], _credentials['api_key'] = username, api_key
    # TODO: verify these _credentials with plotly


### _plot_options stuff ###

def load_plot_options():
    """ Import the plot_options from file into the module-level _plot_options.
    """
    global _plot_options
    _plot_options = _plot_options.update(tools.get_plot_options_file())


def save_plot_options(**kwargs):
    """ Save the module-level _plot_options to file for later access
    """
    global _plot_options
    update_plot_options(**kwargs)
    tools.save_plot_options_file(**_plot_options)


def update_plot_options(**kwargs):
    """ Update the module-level _plot_options
    """
    global _plot_options
    _plot_options.update(kwargs)


def get_plot_options():
    """ Returns a copy of the user supplied plot options.
    Use `update_plot_options()` to change.
    """
    global _plot_options
    return copy(_plot_options)


### plot stuff ###

def iplot(figure_or_data, **plot_options):
    """for use in ipython notebooks"""
    if 'auto_open' not in plot_options:
        plot_options['auto_open'] = False
    res = plot(figure_or_data, **plot_options)
    urlsplit = res['url'].split('/')
    username, plot_id = urlsplit[-2][1:], urlsplit[-1]  # TODO: HACKY!

    embed_options = dict()
    if 'width' in plot_options:
        embed_options['width'] = plot_options['width']
    if 'height' in plot_options:
        embed_options['height'] = plot_options['height']

    return tools.embed(username, plot_id, **embed_options)


def plot(figure_or_data, **plot_options):
    """returns a url with the graph
        opens the graph in the browser if plot_options['auto_open'] is True
    """
    if isinstance(figure_or_data, dict):
        figure = figure_or_data
    elif isinstance(figure_or_data, list):
        figure = {'data': figure_or_data}
    else:
        raise exceptions.PlotlyError("The `figure_or_data` positional argument "
                                     "must be either `dict`-like or "
                                     "`list`-like.")

    res = _send_to_plotly(figure, **plot_options)
    if ('error' in res) and ('auto_open' in plot_options):  # TODO: OK?
        if (res['error'] == '') and plot_options['auto_open']:
            try:
                from webbrowser import open as wbopen
                wbopen(res['url'])
            except:  # TODO: what should we except here? this is dangerous
                pass
    return res


def iplot_mpl(fig, resize=True, **plot_options):
    fig = tools.mpl_to_plotly(fig, resize=resize)
    return iplot(fig, **plot_options)


def plot_mpl(fig, resize=True, **plot_options):
    fig = tools.mpl_to_plotly(fig, resize=resize)
    return plot(fig, **plot_options)


def get_figure(file_owner, file_id):
    # server = "http://ec2-54-196-84-85.compute-1.amazonaws.com"
    server = "https://plot.ly"
    resource = "/apigetfile/{username}/{file_id}".format(username=file_owner,
                                                         file_id=file_id)
    (username, api_key) = _validation_key_logic()

    headers = {'plotly-username': username,
               'plotly-apikey': api_key,
               'plotly-version': '2.0',
               'plotly-platform': 'pythonz'}

    response = requests.get(server + resource, headers=headers)
    if response.status_code == 200:
        content = json.loads(response.content)
        response_payload = content['payload']
        figure = response_payload['figure']
        utils.decode_unicode(figure)
        return tools.get_valid_graph_obj(figure, obj_type='figure')
    else:
        try:
            content = json.loads(response.content)
            print content['error']
        except:
            raise("There was an error retrieving this file")


class Stream:
    """ Plotly's real-time graphing interface. Initialize 
    a Stream object with a stream_id found in https://plot.ly/settings.
    Real-time graphs are initialized with a call to `plot` that embeds 
    your unique `stream_id`s in each of the graph's traces. The `Stream`
    interface plots data to these traces, as identified with the unique
    stream_id, in real-time. Every viewer of the graph sees the same 
    data at the same time.

    View examples here: nbviewer.ipython.org/github/plotly/Streaming-Demos

    Stream example:
    # Initialize a streaming graph
    # by embedding stream_id's in the graph's traces
    >>> stream_id = "your_stream_id" # See https://plot.ly/settings
    >>> py.plot(Data([Scatter(x=[],
                              y=[],
                              stream=dict(token=stream_id, maxpoints=100))])
    # Stream data to the import trace
    >>> stream = Stream(stream_id) # Initialize a stream object
    >>> stream.open() # Open the stream
    >>> stream.write(dict(x=1, y=1)) # Plot (1, 1) in your graph
    """
    def __init__(self, stream_id):
        """ Initialize a Stream object with your unique stream_id.
        Find your stream_id at https://plot.ly/settings.

        For more help, see: `help(plotly.plotly.Stream)`
        or see examples here:
        http://nbviewer.ipython.org/github/plotly/Streaming-Demos
        """
        self.stream_id = stream_id
        self.connected = False

    def open(self):
        """Open a streaming connection to plotly.

        For more help, see: `help(plotly.plotly.Stream)`
        or see examples here:
        http://nbviewer.ipython.org/github/plotly/Streaming-Demos
        """
        self.conn = httplib.HTTPConnection('stream.plot.ly', 80)
        self.conn.putrequest('POST', '/')
        self.conn.putheader('Host', 'stream.plot.ly')
        self.conn.putheader('User-Agent', 'Python-Plotly')
        self.conn.putheader('Transfer-Encoding', 'chunked')
        self.conn.putheader('Connection', 'close')
        self.conn.putheader('plotly-streamtoken', self.stream_id)
        self.conn.endheaders()
        self.connected = True

    def reopen(self):
        """ Not Implemented

        For more help, see: `help(plotly.plotly.Stream)`
        or see examples here:
        http://nbviewer.ipython.org/github/plotly/Streaming-Demos
        """
        raise NotImplementedError

    def write(self, data):
        """ Write `data` to your stream. This will plot the
        `data` in your graph in real-time.

        `data` is a plotly formatted dict.
        Valid keys:
            'x', 'y', 'text', 'z', 'marker', 'line'

        Examples:
        >>> write(dict(x = 1, y = 2))
        >>> write(dict(x = [1, 2, 3], y = [10, 20, 30]))
        >>> write(dict(x = 1, y = 2, text = 'scatter text'))
        >>> write(dict(x = 1, y = 3, marker = dict(color = 'blue')))
        >>> write(dict(z = [[1,2,3], [4,5,6]]))

        For more help, see: `help(plotly.plotly.Stream)`
        or see examples here:
        http://nbviewer.ipython.org/github/plotly/Streaming-Demos
        """
        if not self.connected:
            self.init()
        # plotly's streaming API takes new-line separated json objects
        msg = json.dumps(data, cls=tools._plotlyJSONEncoder) + '\n'
        msglen = format(len(msg), 'x')
        # chunked encoding requests contain the messege length in hex,
        # \r\n, and then the message
        print '{msglen}\r\n{msg}\r\n'.format(msglen=msglen, msg=msg)
        self.conn.send('{msglen}\r\n{msg}\r\n'.format(msglen=msglen, msg=msg))

    def close(self):
        """ Close the stream connection to plotly's streaming servers.

        For more help, see: `help(plotly.plotly.Stream)`
        or see examples here:
        http://nbviewer.ipython.org/github/plotly/Streaming-Demos
        """
        self.conn.send('0\r\n\r\n')
        self.conn.close()
        self.connected = False

    def is_connected(self):
        """ Not Implemented

        For more help, see: `help(plotly.plotly.Stream)`
        or see examples here:
        http://nbviewer.ipython.org/github/plotly/Streaming-Demos
        """
        raise NotImplementedError


def _send_to_plotly(figure, **supplied_plot_options):
    """
    """
    plot_options = dict()
    plot_options.update(tools._DEFAULT_PLOT_OPTIONS)
    plot_options.update(_plot_options)
    plot_options.update(supplied_plot_options)

    data = json.dumps(figure['data'] if 'data' in figure else [],
                      cls=utils._plotlyJSONEncoder)
    file_credentials = tools.get_credentials_file()
    if ('username' in _credentials) and ('api_key' in _credentials):
        username, api_key = _credentials['username'], _credentials['api_key']
    elif ('username' in file_credentials) and ('api_key' in file_credentials):
        (username, api_key) = (file_credentials['username'],
                               file_credentials['api_key'])
    else:
        raise exceptions.PlotlyAccountError("Couldn't find a username, "
                                            "api_key pair.")

    kwargs = json.dumps(dict(filename=plot_options['filename'],
                             fileopt=plot_options['fileopt'],
                             world_readable=plot_options['world_readable'],
                             layout=figure['layout'] if 'layout' in figure
                             else {}),
                        cls=utils._plotlyJSONEncoder)


    payload = dict(platform='python', # TODO: It'd be cool to expose the platform for RaspPi and others
                   version=__version__,
                   args=data,
                   un=username,
                   key=api_key,
                   origin='plot',
                   kwargs=kwargs)

    url = _plotly_url

    r = requests.post(url, data=payload)
    r.raise_for_status()
    r = json.loads(r.text)
    if 'error' in r and r['error'] != '':
        print(r['error'])
    if 'warning' in r and r['warning'] != '':
        warnings.warn(r['warning'])
    if 'message' in r and r['message'] != '':
        print(r['message'])

    return r


def _validation_key_logic():
    creds_on_file = tools.get_credentials_file()
    if 'username' in _credentials:
        username = _credentials['username']
    elif 'username' in creds_on_file:
        username = creds_on_file['username']
    else:
        raise exceptions.PlotlyAccountError("Not signed in or no username "
                                            "saved in config file") # TODO: a message that doesn't suck

    if 'api_key' in _credentials:
        api_key = _credentials['api_key']
    elif 'api_key' in creds_on_file:
        api_key = creds_on_file['api_key']
    else:
        raise exceptions.PlotlyAccountError("Not signed in or no api_key saved "
                                            "in config file") # TODO: a message that doesn't suck
    return (username, api_key)

