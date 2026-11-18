"""Instance-owned immutable repository-source policy; no I/O or application imports."""
class SourceReadPolicy(tuple):
    __slots__ = ()

    def __new__(cls, analysis_seed=False, public_report=False):
        if type(analysis_seed) is not bool or type(public_report) is not bool:
            raise ValueError('source policy requires explicit booleans')
        return tuple.__new__(cls, (analysis_seed, public_report))

    analysis_seed = property(lambda self: self[0])
    public_report = property(lambda self: self[1])


class SourceDisabled(RuntimeError):
    pass


def read_analysis(policy, loader, *args, **kwargs):
    if not isinstance(policy, SourceReadPolicy) or not policy.analysis_seed:
        raise SourceDisabled('analysis_seed_disabled')
    return loader(*args, **kwargs)


def read_public_report(policy, loader, *args, **kwargs):
    if not isinstance(policy, SourceReadPolicy) or not policy.public_report:
        raise SourceDisabled('public_report_source_disabled')
    return loader(*args, **kwargs)
