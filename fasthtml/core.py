# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/api/00_core.ipynb.

# %% auto 0
__all__ = ['empty', 'htmx_hdrs', 'htmxscr', 'htmxwsscr', 'surrsrc', 'scopesrc', 'viewport', 'charset', 'all_meths',
           'is_typeddict', 'is_namedtuple', 'date', 'snake2hyphens', 'HtmxHeaders', 'str2int', 'HttpHeader',
           'form2dict', 'flat_xt', 'Beforeware', 'WS_RouteX', 'RouteX', 'RouterX', 'get_key', 'FastHTML', 'cookie',
           'reg_re_param', 'MiddlewareBase']

# %% ../nbs/api/00_core.ipynb
import json,dateutil,uuid,inspect,types

from fastcore.utils import *
from fastcore.xml import *
from .xtend import *

from types import UnionType, SimpleNamespace as ns, GenericAlias
from typing import Optional, get_type_hints, get_args, get_origin, Union, Mapping, TypedDict, List, Any
from datetime import datetime
from dataclasses import dataclass,fields,is_dataclass,MISSING,asdict
from collections import namedtuple
from inspect import isfunction,ismethod,signature,Parameter,get_annotations
from functools import wraps, partialmethod
from http import cookies

from .starlette import *

empty = Parameter.empty

# %% ../nbs/api/00_core.ipynb
def is_typeddict(cls:type)->bool:
    "Check if `cls` is a `TypedDict`"
    attrs = 'annotations', 'required_keys', 'optional_keys'
    return isinstance(cls, type) and all(hasattr(cls, f'__{attr}__') for attr in attrs)

# %% ../nbs/api/00_core.ipynb
def is_namedtuple(cls):
    "`True` is `cls` is a namedtuple type"
    return issubclass(cls, tuple) and hasattr(cls, '_fields')

# %% ../nbs/api/00_core.ipynb
def date(s:str):
    "Convert `s` to a datetime"
    return dateutil.parser.parse(s)

# %% ../nbs/api/00_core.ipynb
def snake2hyphens(s:str):
    "Convert `s` from snake case to hyphenated and capitalised"
    s = snake2camel(s)
    return camel2words(s, '-')

# %% ../nbs/api/00_core.ipynb
htmx_hdrs = dict(
    boosted="HX-Boosted",
    current_url="HX-Current-URL",
    history_restore_request="HX-History-Restore-Request",
    prompt="HX-Prompt",
    request="HX-Request",
    target="HX-Target",
    trigger_name="HX-Trigger-Name",
    trigger="HX-Trigger")

@dataclass
class HtmxHeaders:
    boosted:str|None=None; current_url:str|None=None; history_restore_request:str|None=None; prompt:str|None=None
    request:str|None=None; target:str|None=None; trigger_name:str|None=None; trigger:str|None=None
    def __bool__(self): return any(hasattr(self,o) for o in htmx_hdrs)

def _get_htmx(h):
    res = {k:h.get(v.lower(), None) for k,v in htmx_hdrs.items()}
    return HtmxHeaders(**res)

# %% ../nbs/api/00_core.ipynb
def str2int(s)->int:
    "Convert `s` to an `int`"
    s = s.lower()
    if s=='on': return 1
    if s=='none': return 0
    return 0 if not s else int(s)

# %% ../nbs/api/00_core.ipynb
def _mk_list(t, v): return [t(o) for o in v]

# %% ../nbs/api/00_core.ipynb
def _fix_anno(t):
    "Create appropriate callable type for casting a `str` to type `t` (or first type in `t` if union)"
    origin = get_origin(t)
    if origin is Union or origin is UnionType or origin in (list,List):
        t = first(o for o in get_args(t) if o!=type(None))
    d = {bool: str2bool, int: str2int}
    res = d.get(t, t)
    if origin in (list,List): res = partial(_mk_list, res)
    return res

# %% ../nbs/api/00_core.ipynb
def _form_arg(k, v, d):
    "Get type by accessing key `k` from `d`, and use to cast `v`"
    if v is None: return
    # This is the type we want to cast `v` to
    anno = d.get(k, None)
    if not anno: return v
    return _fix_anno(anno)(v)

# %% ../nbs/api/00_core.ipynb
@dataclass
class HttpHeader: k:str;v:str

# %% ../nbs/api/00_core.ipynb
def _annotations(anno):
    "Same as `get_annotations`, but also works on namedtuples"
    if is_namedtuple(anno): return {o:str for o in anno._fields}
    return get_annotations(anno)

# %% ../nbs/api/00_core.ipynb
def _is_body(anno): return issubclass(anno, (dict,ns)) or _annotations(anno)

# %% ../nbs/api/00_core.ipynb
def _formitem(form, k):
    "Return single item `k` from `form` if len 1, otherwise return list"
    o = form.getlist(k)
    return o[0] if len(o) == 1 else o if o else None

# %% ../nbs/api/00_core.ipynb
def form2dict(form: FormData) -> dict:
    "Convert starlette form data to a dict"
    return {k: _formitem(form, k) for k in form}

# %% ../nbs/api/00_core.ipynb
async def _from_body(req, p):
    form = await req.form()
    anno = p.annotation
    # Get the fields and types of type `anno`, if available
    d = _annotations(anno)
    cargs = {k:_form_arg(k, v, d) for k,v in form2dict(form).items() if not d or k in d}
    return anno(**cargs)

# %% ../nbs/api/00_core.ipynb
async def _find_p(req, arg:str, p:Parameter):
    "In `req` find param named `arg` of type in `p` (`arg` is ignored for body types)"
    anno = p.annotation
    # If there's an annotation of special types, return object of that type
    # GenericAlias is a type of typing for iterators like list[int] that is not a class
    if isinstance(anno, type) and not isinstance(anno, GenericAlias):
        if issubclass(anno, Request): return req
        if issubclass(anno, Request): return req
        if issubclass(anno, HtmxHeaders): return _get_htmx(req.headers)
        if issubclass(anno, Starlette): return req.scope['app']
        if _is_body(anno): return await _from_body(req, p)
    # If there's no annotation, check for special names
    if anno is empty:
        if 'request'.startswith(arg.lower()): return req
        if 'session'.startswith(arg.lower()): return req.scope.get('session', {})
        if arg.lower()=='auth': return req.scope.get('auth', None)
        if arg.lower()=='htmx': return _get_htmx(req.headers)
        if arg.lower()=='app': return req.scope['app']
        return None
    # Look through path, cookies, headers, session, query, and body in that order
    res = req.path_params.get(arg, None)
    if res in (empty,None): res = req.cookies.get(arg, None)
    if res in (empty,None): res = req.headers.get(snake2hyphens(arg), None)
    if res in (empty,None): res = nested_idx(req.scope, 'session', arg) or None
    if res in (empty,None): res = req.query_params.get(arg, None)
    if res in (empty,None):
        frm = await req.form()
        res = _formitem(frm, arg)
    # Raise 400 error if the param does not include a default
    if (res in (empty,None)) and p.default is empty: raise HTTPException(400, f"Missing required field: {arg}")
    # If we have a default, return that if we have no value
    if res in (empty,None): res = p.default
    # We can cast str and list[str] to types; otherwise just return what we have
    if not isinstance(res, (list,str)) or anno is empty: return res
    anno = _fix_anno(anno)
    try: return [anno(o) for o in res] if isinstance(res,list) else anno(res)
    except ValueError: raise HTTPException(404, req.url.path) from None

async def _wrap_req(req, params):
    return [await _find_p(req, arg, p) for arg,p in params.items()]

# %% ../nbs/api/00_core.ipynb
def flat_xt(lst):
    "Flatten lists, except for `FT`s"
    result = []
    for item in lst:
        if isinstance(item, (list,tuple)) and not isinstance(item, FT): result.extend(item)
        else: result.append(item)
    return result

# %% ../nbs/api/00_core.ipynb
class Beforeware:
    def __init__(self, f, skip=None): self.f,self.skip = f,skip or []

# %% ../nbs/api/00_core.ipynb
def _find_wsp(ws, data, hdrs, arg:str, p:Parameter):
    "In `data` find param named `arg` of type in `p` (`arg` is ignored for body types)"
    anno = p.annotation
    if isinstance(anno, type):
        if issubclass(anno, HtmxHeaders): return _get_htmx(hdrs)
        if issubclass(anno, Starlette): return ws.scope['app']
    if anno is empty:
        if arg.lower()=='ws': return ws
        if arg.lower()=='data': return data
        if arg.lower()=='htmx': return _get_htmx(hdrs)
        if arg.lower()=='app': return ws.scope['app']
        if arg.lower()=='send': return partial(_send_ws, ws)
        return None
    res = data.get(arg, None)
    if res is empty or res is None: res = headers.get(snake2hyphens(arg), None)
    if res is empty or res is None: res = p.default
    # We can cast str and list[str] to types; otherwise just return what we have
    if not isinstance(res, (list,str)) or anno is empty: return res
    anno = _fix_anno(anno)
    return [anno(o) for o in res] if isinstance(res,list) else anno(res)

def _wrap_ws(ws, data, params):
    hdrs = data.pop('HEADERS', {})
    return [_find_wsp(ws, data, hdrs, arg, p) for arg,p in params.items()]

# %% ../nbs/api/00_core.ipynb
async def _send_ws(ws, resp):
    if not resp: return
    res = to_xml(resp) if isinstance(resp, (list,tuple)) or hasattr(resp, '__ft__') else resp
    await ws.send_text(res)

def _ws_endp(recv, conn=None, disconn=None, hdrs=None, before=None):
    cls = type('WS_Endp', (WebSocketEndpoint,), {"encoding":"text"})
    
    async def _generic_handler(handler, ws, data=None):
        wd = _wrap_ws(ws, loads(data) if data else {}, signature(handler).parameters)
        resp = handler(*wd)
        if resp:
            if is_async_callable(handler): resp = await resp
            await _send_ws(ws, resp)

    async def _connect(self, ws):
        await ws.accept()
        await _generic_handler(conn, ws)
    async def _disconnect(self, ws, close_code): await _generic_handler(disconn, ws)
    async def _recv(self, ws, data): await _generic_handler(recv, ws, data)

    if    conn: cls.on_connect    = _connect
    if disconn: cls.on_disconnect = _disconnect
    cls.on_receive = _recv
    return cls

# %% ../nbs/api/00_core.ipynb
class WS_RouteX(WebSocketRoute):
    def __init__(self, path:str, recv, conn:callable=None, disconn:callable=None, *,
                 name=None, middleware=None, hdrs=None, before=None):
        super().__init__(path, _ws_endp(recv, conn, disconn, hdrs, before), name=name, middleware=middleware)

# %% ../nbs/api/00_core.ipynb
class RouteX(Route):
    def __init__(self, path:str, endpoint, *, methods=None, name=None, include_in_schema=True, middleware=None,
                hdrs=None, ftrs=None, before=None, after=None, htmlkw=None, **bodykw):
        self.sig = signature(endpoint)
        self.f,self.hdrs,self.ftrs,self.before,self.after,self.htmlkw,self.bodykw = endpoint,hdrs,ftrs,before,after,htmlkw,bodykw
        super().__init__(path, self._endp, methods=methods, name=name, include_in_schema=include_in_schema, middleware=middleware)

    def _xt_resp(self, req, resp):
        if not isinstance(resp, tuple): resp = (resp,)
        resp = resp + tuple(req.injects)
        http_hdrs,resp = partition(resp, risinstance(HttpHeader))
        http_hdrs = {o.k:str(o.v) for o in http_hdrs}
        titles,bdy = partition(resp, lambda o: getattr(o, 'tag', '') in ('title','meta'))
        if resp and 'hx-request' not in req.headers and not any(getattr(o, 'tag', '')=='html' for o in resp):
            if not titles: titles = [Title('FastHTML page')]
            resp = Html(Head(*titles, *flat_xt(self.hdrs)), Body(bdy, *flat_xt(self.ftrs), **self.bodykw), **self.htmlkw)
        return HTMLResponse(to_xml(resp), headers=http_hdrs)

    def _resp(self, req, resp):
        if not resp: resp=()
        cls = self.sig.return_annotation
        if cls in (Any,FT): cls=empty
        if isinstance(resp, FileResponse) and not os.path.exists(resp.path): raise HTTPException(404, resp.path)
        if isinstance(resp, Response): return resp
        if cls is not empty: return cls(resp)
        if isinstance(resp, (list,tuple,HttpHeader)) or hasattr(resp, '__ft__'): return self._xt_resp(req, resp)
        if isinstance(resp, str): cls = HTMLResponse
        elif isinstance(resp, Mapping): cls = JSONResponse
        else:
            resp = str(resp)
            cls = HTMLResponse
        return cls(resp)

    async def _endp(self, req):
        resp = None
        req.injects = []
        for b in self.before:
            if not resp:
                if isinstance(b, Beforeware): bf,skip = b.f,b.skip
                else: bf,skip = b,[]
                if not any(re.match(r, req.url.path) for r in skip):
                    wreq = await _wrap_req(req, signature(bf).parameters)
                    resp = bf(*wreq)
                    if is_async_callable(bf): resp = await resp
        if not resp:
            wreq = await _wrap_req(req, self.sig.parameters)
            resp = self.f(*wreq)
            if is_async_callable(self.f): resp = await resp
        for a in self.after:
            _,*wreq = await _wrap_req(req, signature(a).parameters)
            nr = a(resp, *wreq)
            if nr: resp = nr
        return self._resp(req, resp)

# %% ../nbs/api/00_core.ipynb
class RouterX(Router):
    def __init__(self, routes=None, redirect_slashes=True, default=None, on_startup=None, on_shutdown=None,
                 lifespan=None, *, middleware=None, hdrs=None, ftrs=None, before=None, after=None, htmlkw=None, **bodykw):
        super().__init__(routes, redirect_slashes, default, on_startup, on_shutdown,
                 lifespan=lifespan, middleware=middleware)
        self.hdrs,self.ftrs,self.bodykw,self.htmlkw,self.before,self.after = hdrs,ftrs,bodykw,htmlkw or {},before,after

    def add_route( self, path: str, endpoint: callable, methods=None, name=None, include_in_schema=True):
        route = RouteX(path, endpoint=endpoint, methods=methods, name=name, include_in_schema=include_in_schema,
                       hdrs=self.hdrs, ftrs=self.ftrs, before=self.before, after=self.after, htmlkw=self.htmlkw, **self.bodykw)
        self.routes.append(route)

    def add_ws( self, path: str, recv: callable, conn:callable=None, disconn:callable=None, name=None):
        route = WS_RouteX(path, recv=recv, conn=conn, disconn=disconn, name=name, hdrs=self.hdrs, before=self.before)
        self.routes.append(route)

# %% ../nbs/api/00_core.ipynb
htmxscr   = Script(src="https://unpkg.com/htmx.org@next/dist/htmx.min.js")
htmxwsscr = Script(src="https://unpkg.com/htmx-ext-ws/ws.js")
surrsrc   = Script(src="https://cdn.jsdelivr.net/gh/answerdotai/surreal@1.3.0/surreal.js")
scopesrc  = Script(src="https://cdn.jsdelivr.net/gh/gnat/css-scope-inline@main/script.js")
viewport  = Meta(name="viewport", content="width=device-width, initial-scale=1, viewport-fit=cover")
charset   = Meta(charset="utf-8")

# %% ../nbs/api/00_core.ipynb
def get_key(key=None, fname='.sesskey'):
    if key: return key
    fname = Path(fname)
    if fname.exists(): return fname.read_text()
    key = str(uuid.uuid4())
    fname.write_text(key)
    return key

# %% ../nbs/api/00_core.ipynb
def _list(o): return [] if not o else list(o) if isinstance(o, (tuple,list)) else [o]

# %% ../nbs/api/00_core.ipynb
class FastHTML(Starlette):
    def __init__(self, debug=False, routes=None, middleware=None, exception_handlers=None,
                 on_startup=None, on_shutdown=None, lifespan=None, hdrs=None, ftrs=None,
                 before=None, after=None, default_hdrs=True,
                 secret_key=None, session_cookie='session_', max_age=365*24*3600, ws_hdr=False, sess_path='/',
                 same_site='lax', sess_https_only=False, sess_domain=None, key_fname='.sesskey', htmlkw=None, **bodykw):
        middleware,before,after = _list(middleware),_list(before),_list(after)
        secret_key = get_key(secret_key, key_fname)
        sess = Middleware(SessionMiddleware, secret_key=secret_key, session_cookie=session_cookie,
                          max_age=max_age, path=sess_path, same_site=same_site,
                          https_only=sess_https_only, domain=sess_domain)
        middleware.append(sess)
        super().__init__(debug, routes, middleware, exception_handlers, on_startup, on_shutdown, lifespan=lifespan)
        hdrs = list([] if hdrs is None else hdrs)
        ftrs = list([] if ftrs is None else ftrs)
        if default_hdrs: hdrs = [charset, viewport, htmxscr,surrsrc,scopesrc] + hdrs
        if ws_hdr: hdrs.append(htmxwsscr)
        self.router = RouterX(routes, on_startup=on_startup, on_shutdown=on_shutdown, lifespan=lifespan,
                              hdrs=hdrs, ftrs=ftrs, before=before, after=after, htmlkw=htmlkw or {}, **bodykw)

    def route(self, path:str, methods=None, name=None, include_in_schema=True):
        def f(func):
            m = [methods] if isinstance(methods,str) else [func.__name__] if not methods else methods
            self.router.add_route(path, func, methods=m, name=name, include_in_schema=include_in_schema)
            return func
        return f

    def ws(self, path:str, conn=None, disconn=None, name=None):
        def f(func):
            self.router.add_ws(path, func, conn=conn, disconn=disconn, name=name)
            return func
        return f

all_meths = 'get post put delete patch head trace options'.split()
for o in all_meths: setattr(FastHTML, o, partialmethod(FastHTML.route, methods=o))

# %% ../nbs/api/00_core.ipynb
def cookie(key: str, value="", max_age=None, expires=None, path="/", domain=None, secure=False, httponly=False, samesite="lax",):
    "Create a 'set-cookie' `HttpHeader`"
    cookie = cookies.SimpleCookie()
    cookie[key] = value
    if max_age is not None: cookie[key]["max-age"] = max_age
    if expires is not None:
        cookie[key]["expires"] = format_datetime(expires, usegmt=True) if isinstance(expires, datetime) else expires
    if path is not None: cookie[key]["path"] = path
    if domain is not None: cookie[key]["domain"] = domain
    if secure: cookie[key]["secure"] = True
    if httponly: cookie[key]["httponly"] = True
    if samesite is not None:
        assert samesite.lower() in [ "strict", "lax", "none", ], "must be 'strict', 'lax' or 'none'"
        cookie[key]["samesite"] = samesite
    cookie_val = cookie.output(header="").strip()
    return HttpHeader("set-cookie", cookie_val)

# %% ../nbs/api/00_core.ipynb
def reg_re_param(m, s):
    cls = get_class(f'{m}Conv', sup=StringConvertor, regex=s)
    register_url_convertor(m, cls())

# %% ../nbs/api/00_core.ipynb
# Starlette doesn't have the '?', so it chomps the whole remaining URL
reg_re_param("path", ".*?")
reg_re_param("static", "ico|gif|jpg|jpeg|webm|css|js|woff|png|svg|mp4|webp|ttf|otf|eot|woff2|txt|xml|html")

# %% ../nbs/api/00_core.ipynb
class MiddlewareBase:
    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] not in ["http", "websocket"]:
            await self.app(scope, receive, send)
            return
        return HTTPConnection(scope)
