import argparse
import json
from pathlib import Path
import sys
from .core import Index, bundled, answer
from .model import LocalModel


def main():
    p = argparse.ArgumentParser(description='Local LLM document answers with source-checked quotations.')
    p.add_argument('--endpoint',default='http://127.0.0.1:8094')
    p.add_argument('--model',default='qwen3-0.6b-local')
    p.add_argument('--corpus',type=Path,help='Local JSON corpus; default is the fictional bundled handbook.')
    sub = p.add_subparsers(dest='command',required=True)
    ask = sub.add_parser('ask'); ask.add_argument('question'); ask.add_argument('--k',type=int,default=1)
    ev = sub.add_parser('evaluate'); ev.add_argument('--out',default='reports/evaluation')
    ev.add_argument('--provenance',type=Path,help='Optional operator-supplied runtime provenance JSON.')
    render = sub.add_parser('render'); render.add_argument('--input',default='reports/evaluation/evaluation.json'); render.add_argument('--out',default='reports/evaluation/report.html')
    web = sub.add_parser('serve'); web.add_argument('--port',type=int,default=8774); web.add_argument('--report',default='reports/evaluation/evaluation.json')
    args = p.parse_args()
    try:
        if args.command == 'render':
            from .evaluate import render
            render(json.loads(Path(args.input).read_text(encoding='utf-8')),args.out)
            return 0
        client = LocalModel(args.endpoint,args.model)
        index = Index(json.loads(args.corpus.read_text(encoding='utf-8')) if args.corpus else bundled('corpus.json'))
        if args.command == 'ask':
            result = answer(index,args.question,client,args.k)
            print(json.dumps(result,indent=2,ensure_ascii=False))
            return 2 if result['status']=='CHECK_FAILED' else 0
        if args.command == 'evaluate':
            if args.corpus:
                raise ValueError('The published evaluation uses the bundled corpus and labels only.')
            from .evaluate import evaluate,render
            provenance = json.loads(args.provenance.read_text(encoding='utf-8')) if args.provenance else None
            payload = evaluate(client,args.out,provenance)
            render(payload,Path(args.out)/'report.html')
            return 1 if payload['summary']['errors'] else 0
        if not 1024 <= args.port <= 65535:
            raise ValueError('Use a port between 1024 and 65535.')
        from .server import serve
        serve(index,client,args.report,args.port)
        return 0
    except (OSError,ValueError,KeyError,IndexError,TypeError) as exc:
        print(f'Unable to complete: {exc}',file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
