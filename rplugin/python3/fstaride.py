import os
import sys
import neovim

sys.path.append(os.path.dirname(__file__))
import proc as fstar

# does not work
def catch_exception(fn):
    def body(self, *args, **kwargs):
        try:
            fn(self, *args, **kwargs)
        except Exception as ex:
            self.log.exception('auto caught exception')


@neovim.plugin
class FStarIde:
    def __init__(self, vim):
        self.vim = vim
        self.fstar_inited = False

        # wire things together
        fstar.plugin = self
        self.log = fstar.log
        self.reset()

        self.log.info('Started')

    def reset(self):
        self.current_push_stop = 0
        self.horizons = [0]
        self.vim.api.call_function('setpos', ["'p", [0, 0, 0, 0]])

    def fstar_init(self):
        if not self.fstar_inited:
            self.filename = self.vim.api.call_function('expand', ['%:p'])
            fstar.init(self.filename)
            self.fstar_inited = True

    def getpos(self):
        return self.vim.api.call_function('getpos', ['.'])

    def setpos(self, p):
        self.vim.api.call_function('setpos', ['.', p])

    def getcurline(self):
        return self.getpos()[1]

    def set_horizon(self, ln):
        'Do not add to self.horizons though'
        self.vim.api.call_function('setpos', ["'p", [0, ln, 0, 0]])
        bnr = self.vim.current.buffer.number
        # this is retarded, use highlight or something
        self.vim.api.call_function('execute', ['sign unplace 1'])
        self.vim.api.call_function('execute', ['sign place 1 line={} name=horizon buffer={}'.format(ln, bnr)])

    def get_horizon(self):
        pos = self.vim.api.call_function('getpos', ["'p"])[1]
        return pos

    def get_block(self, to_cursor):
        start = self.get_horizon()

        if not to_cursor:
            self.setpos([0, start, 0, 0])
            self.vim.feedkeys('}')

        stop = self.getcurline()

        lines = self.vim.current.buffer[start:stop]
        self.log.debug('block start={} stop={} lines={}'.format(start,stop,len(lines)))

        # must be delayed, only updated on success
        #self.set_horizon(stop)
        self.current_push_stop = stop
        # return starting position of this block for F* to report
        # apparently it counts from 1
        return ('\n'.join(lines), start + 1, 0)

    def handle_push_err(self, errs):
        lst = []
        for err in errs:
            ranges = err['ranges']
            message = err['message']
            level = err['level']
            for ix, i in enumerate(ranges):
                lst.append({
                    'lnum': i['beg'][0],
                    'col': i['beg'][1],
                    'text': message if ix == 0 else 'related',
                    'type': level[0].upper()
                    })
            self.log.debug('qf {}'.format(lst))

        self.vim.api.call_function('setqflist', [lst])
        self.vim.command('cc')
        # self.vim.out_write(lst[0]['text'])

    def handle_push_ok(self):
        self.set_horizon(self.current_push_stop)
        self.horizons.append(self.current_push_stop)

    def handle_lookup(self, info):
        def_at = info['defined-at']
        if def_at['fname'] == '<input>':
            def_at['fname'] = self.filename

        self.vim.command('pedit +:{} {}'.format(def_at['beg'][0], def_at['fname']))

    def handle_lookup_type(self, info):
        self.vim.command('pedit type_lookup')
        nr = self.vim.api.call_function('bufnr', ['type_lookup'])
        buf = self.vim.buffers[nr]
        buf.append(info)

        

    @neovim.command('FStarSendPara', range='', nargs='0', sync=False)
    def send_para(self, args, range):
        try:
            self.fstar_init()
            (code, lnum, col) = self.get_block(False)
            self.log.debug('sending code\n' + code)
            self.vim.api.call_function('setqflist', [[]])
            fstar.push_code(code, lnum, col)
            fstar.read_any()
        except Exception as ex:
            self.log.exception('when pushing code')


    @neovim.command('FStarSendToCursor', range='', nargs='0', sync=False)
    def send_to_cursor(self, args, range):
        try:
            self.fstar_init()
            (code, lnum, col) = self.get_block(True)
            self.vim.api.call_function('setqflist', [[]])
            fstar.push_code(code, lnum, col)
            fstar.read_any()
        except Exception as ex:
            self.log.exception('when pushing to cursor')

    @neovim.command('FStarPop', range='', nargs='0', sync=False)
    def pop_code(self, args, range):
        try:
            self.horizons.pop()
            h = self.horizons[-1]
            self.set_horizon(h)
            fstar.pop_code()
            fstar.read_any()
        except Exception as ex:
            self.log.exception('in pop code')

    # todo: would be cool if it not only went to definition but also displayed type
    #       somewhere
    #    +: and be mapped to a key using <cword>
    @neovim.command('FStarLookup', range='', nargs='?', sync=False)
    def lookup(self, args, range):
        if len(args) == 0:
            args = [self.vim.api.call_function('expand', ['<cword>'])]
        fstar.query_lookup(args[0], 'defined-at')
        fstar.read_any()

    @neovim.command('FStarLookupType', range='', nargs='?', sync=False)
    def lookup_type(self, args, range):
        if len(args) == 0:
            args = [self.vim.api.call_function('expand', ['<cword>'])]
        fstar.query_lookup(args[0], 'type')
        fstar.read_any()

    @neovim.command('FStarRestart', range=None, nargs=0, sync=False)
    def restart(self, args, rng):
        fstar.restart()
        self.reset()
