import json
from http.server import ThreadingHTTPServer
import threading
import unittest
import urllib.request
import urllib.error
from evidence_desk.core import Index,bundled
from evidence_desk.server import make_handler
from test_core import FakeModel


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.index=Index(bundled('corpus.json'))
        self.client=FakeModel('{"decision":"abstain","evidence":[]}')
        self.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(self.index,self.client,{},0))
        self.port=self.server.server_port
        self.server.RequestHandlerClass=make_handler(self.index,self.client,{},self.port)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join()

    def post(self,data,headers=None):
        req=urllib.request.Request(f'http://127.0.0.1:{self.port}/api/ask',data=json.dumps(data).encode(),
            headers=headers or {'Content-Type':'application/json'})
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(req,timeout=3) as r:return r.status,json.load(r)
        except urllib.error.HTTPError as e:return e.code,json.load(e)

    def test_local_question(self):
        status,r=self.post({'question':'backup retention'})
        self.assertEqual(status,200);self.assertEqual(r['status'],'ABSTAIN')

    def test_cross_origin_rejected(self):
        status,_=self.post({'question':'backup'}, {'Content-Type':'application/json','Origin':'https://evil.example'})
        self.assertEqual(status,403);self.assertEqual(self.client.calls,0)

    def test_form_post_rejected(self):
        status,_=self.post({'question':'backup'},{'Content-Type':'text/plain'})
        self.assertEqual(status,415)

    def test_invalid_question_rejected(self):
        status,_=self.post({'question':['backup']})
        self.assertEqual(status,400);self.assertEqual(self.client.calls,0)

    def test_rebinding_host_rejected(self):
        status,_=self.post({'question':'backup'},{'Content-Type':'application/json','Host':'evil.example'})
        self.assertEqual(status,403)


if __name__=='__main__':unittest.main()
