import functools
import inspect
import types

from newrelic.api.transaction import current_transaction
from newrelic.api.object_wrapper import (ObjectWrapper,
        callable_name, wrap_object)
from newrelic.api.function_trace import FunctionTrace

def GeneratorTraceWrapper(wrapped, name=None, group=None, label=None,
            params=None):

    def wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        if callable(name):
            if instance and inspect.ismethod(wrapped):
                _name = name(instance, *args, **kwargs)
            else:
                _name = name(*args, **kwargs)

        elif name is None:
            _name = callable_name(wrapped)

        else:
            _name = name

        if callable(group):
            if instance and inspect.ismethod(wrapped):
                _group = group(instance, *args, **kwargs)
            else:
                _group = group(*args, **kwargs)

        else:
            _group = group

        if callable(label):
            if instance and inspect.ismethod(wrapped):
                _label = label(instance, *args, **kwargs)
            else:
                _label = label(*args, **kwargs)

        else:
            _label = label

        if callable(params):
            if instance and inspect.ismethod(wrapped):
                _params = params(instance, *args, **kwargs)
            else:
                _params = params(*args, **kwargs)

        else:
            _params = params

        def _generator(generator):
            _gname = '%s (generator)' % _name

            try:
                value = None
                exc = None

                while True:
                    transaction = current_transaction()

                    params = {}

                    frame = generator.gi_frame

                    params['filename'] = frame.f_code.co_filename
                    params['lineno'] = frame.f_lineno

                    with FunctionTrace(transaction, _gname, _group,
                             params=params):
                        try:
                            if exc is not None:
                                yielded = generator.throw(*exc)
                                exc = None
                            else:
                                yielded = generator.send(value)

                        except StopIteration:
                            raise

                        except Exception:
                            raise

                    try:
                        value = yield yielded

                    except Exception:
                        exc = sys.exc_info()

            finally:
                generator.close()

        with FunctionTrace(transaction, _name, _group, _label, _params):
            try:
                result = wrapped(*args, **kwargs)

            except Exception:
                raise

            else:
                if isinstance(result, types.GeneratorType):
                    return _generator(result)

                else:
                    return result

    return ObjectWrapper(wrapped, None, wrapper)

def generator_trace(name=None, group=None, label=None, params=None):
    return functools.partial(GeneratorTraceWrapper, name=name,
            group=group, label=label, params=params)

def wrap_generator_trace(module, object_path, name=None,
        group=None, label=None, params=None):
    return wrap_object(module, object_path, GeneratorTraceWrapper,
            (name, group, label, params))
