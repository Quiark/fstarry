import os
import sys
import json
from pprint import pformat
import logging
import traceback
import subprocess


fstar_path = 'fstar.exe'
p = None

log = logging.getLogger('fstar')
log.setLevel(logging.DEBUG)
log.addHandler(logging.FileHandler('/Users/roman/fstar2.log'))

queries = {}
plugin = None


def super_read(f):
    return f.readline()
    res = b''
    while f.readable():
        b = f.read(1)
        res += b
        sys.stdout.write(b.decode())
        if b == b'\n': break

    return res

def read():
    resp = json.loads(super_read(p.stdout))
    log.debug('<<<' + str(resp))
    return resp

def send(obj):
    req = json.dumps(obj)
    log.debug('>>>' + str(req))
    p.stdin.write(req.encode())
    p.stdin.write(b'\n')
    p.stdin.flush()   # <-- it does not work without this

def handle_intro(data):
    assert data['kind'] == 'protocol-info'
    assert data['version'] == 2


def mk_query(q):
    # optimize, turn it into a list?
    ix = max(queries.keys()) + 1 if len(queries) > 0 else 0
    q['query-id'] = str(ix)
    queries[ix] = q
    return q


def query_lookup(symbol, mode='defined-at'):
    if mode == 'defined-at':
        info = ['defined-at']
    else:
        info = ["type", "documentation", "definition"]

    q = mk_query({'query': 'lookup',
            'client': {
                'mode': mode
            },
            'args': {
                'symbol': symbol,
                'requested-info': info
    }})
    send(q)

def handle_lookup(query, response):
    info = response['response']
    if query['client']['mode'] == 'defined-at':
        plugin.handle_lookup(info)
    else:
        defs = ('''NAME {name}
                \tDEFN {definition}
                \tTYPE {type}
                
                \tDOCU {documentation}'''.format(**info))
        plugin.handle_lookup_type(defs)

def push_code(code, line, column):
    q = mk_query({'query': 'push',
        'args': {
            'kind': 'full',
            'code': code,
            'line': line,
            'column': column
            }})
    send(q)

def handle_push(query, response):
    if response['status'] == 'failure':
        errs = response['response']
        plugin.handle_push_err(errs)
    else:
        plugin.handle_push_ok()

def pop_code():
    q = mk_query({'query': 'pop',
        'args': {}})
    send(q)

def query_complete(partial_symbol, context = None):
    q = mk_query({'query': 'autocomplete',
        'args': {
            'partial-symbol': partial_symbol,
            'context': context
            }})
    send(q)

def handle_complete(query, response):
    info = response['response']
    for i in info:
        log.info(i)

def compute(expr):
    q = mk_query({'query': 'compute',
        'args': {
            'term': expr
        }})
    send(q)

def handle_compute(query, response):
    info = response['response']
    print(info)

def read_any():
    obj = read()
    try:
        assert obj['kind'] == 'response'
        # assert obj['status'] == 'success'

        query_id = int(obj['query-id'])
        query = queries[query_id]
        query_type = query['query']
        if query_type == 'lookup':
            handle_lookup(query, obj)
        elif query_type == 'auto-complete':
            handle_complete(query, obj)
        elif query_type == 'push':
            handle_push(query, obj)
        elif query_type == 'compute':
            handle_compute(query, obj)

    except Exception as e:
        log.exception('Error when handling response {}\n'.format(pformat(obj)))

def init(module):
    global p
    cmdline = '{} --ide {}'.format(fstar_path, module)
    p = subprocess.Popen(cmdline, stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
    handle_intro(read())

def restart(module):
    try: p.terminate()
    except: pass

    init(module)

def main():
    # - init
    init('/Users/roman/OneDrive/fstarplayground/Roman.Hex.fst')

    push_code('module Play', 1, 0)
    read_any()

    # kind of REPL
    while True:
        line = input('--> ')
        compute(line)
        read_any()

'''
    push_code('let val xx, =', 10, 0)
    read_any()
    query_lookup('FStar.UInt8.t')
    read_any()
    query_lookup('FStar.Option.get')
    read_any()
'''

if __name__ == '__main__':
    main()
