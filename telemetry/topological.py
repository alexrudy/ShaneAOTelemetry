# -*- coding: utf-8 -*-
"""
Topological sort method
"""

__all__ = ['topological_sort', 'topological_filter']

def topological_filter(source, target):
    """Topological filter sort."""
    dependencies = dict((name, set(deps)) for name, deps in source)
    needed = set([target])
    for name in reversed(list(topological_sort(dependencies.items()))):
        if name in needed:
            needed.update(dependencies[name])
        else:
            dependencies.pop(name)
    return topological_sort(dependencies.items())

def topological_sort(source):
    """perform topological sort on elements.

    :arg source: list of ``(name, [list of dependencies])`` pairs
    :returns: list of names, with dependencies listed first
    """
    pending = [(name, set(deps)) for name, deps in source] # copy deps so we can modify set in-place       
    emitted = []        
    while pending:
        next_pending = []
        next_emitted = []
        for entry in pending:
            name, deps = entry
            deps.difference_update(emitted) # remove deps we emitted last pass
            if deps: # still has deps? recheck during next pass
                next_pending.append(entry) 
            else: # no more deps? time to emit
                yield name 
                emitted.append(name) # <-- not required, but helps preserve original ordering
                next_emitted.append(name) # remember what we emitted for difference_update() in next pass
        if not next_emitted: # all entries have unmet deps, one of two things is wrong...
            raise ValueError("cyclic or missing dependency detected: %r" % (next_pending,))
        pending = next_pending
        emitted = next_emitted
    

