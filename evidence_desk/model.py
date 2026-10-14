"""A loopback-only llama.cpp client. No keys and no hosted service required."""
import json
import time
import urllib.request
from urllib.parse import urlsplit
from .core import SCHEMA


def validate_endpoint(endpoint):
    u = urlsplit(endpoint)
    if (u.scheme != 'http' or u.hostname not in ('127.0.0.1','localhost','::1')
            or u.username or u.password or u.query or u.fragment or u.path not in ('','/')):
        raise ValueError('Model endpoint must be a loopback HTTP origin, for example http://127.0.0.1:8094.')
    if u.port is None:
        raise ValueError('Model endpoint must specify a port.')
    return endpoint.rstrip('/')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Model endpoint redirects are not allowed.')


class LocalModel:
    def __init__(self, endpoint='http://127.0.0.1:8094', model='qwen3-0.6b-local', timeout=120):
        self.endpoint = validate_endpoint(endpoint)
        self.model = model
        self.timeout = timeout
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def health(self):
        with self.opener.open(self.endpoint+'/health', timeout=3) as response:
            return json.load(response).get('status') == 'ok'

    def complete(self, messages):
        payload = dict(model=self.model, messages=messages, temperature=0, seed=41, max_tokens=384,
                       stream=False, chat_template_kwargs={'enable_thinking':False},
                       response_format={'type':'json_object','schema':SCHEMA})
        request = urllib.request.Request(self.endpoint+'/v1/chat/completions',
                   data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'})
        started = time.perf_counter()
        with self.opener.open(request, timeout=self.timeout) as response:
            body = response.read(1000001)
        if len(body) > 1000000:
            raise ValueError('Model response exceeds size limit.')
        result = json.loads(body)
        choice = result['choices'][0]
        return {'content':choice['message']['content'], 'finish_reason':choice.get('finish_reason'),
                'usage':result.get('usage',{}), 'latency_seconds':round(time.perf_counter()-started, 3)}
