"""Small synchronous module-export cache; no imports or data dependencies."""
class LazyExports:
    def __init__(self, namespace, loaders):
        self.namespace = namespace
        self.loaders = loaders

    def get(self, name):
        if name in self.namespace:
            return self.namespace[name]
        if name not in self.loaders:
            raise AttributeError(name)
        value = self.loaders[name]()
        # Do not overwrite a value explicitly installed while loading.
        return self.namespace.setdefault(name, value)
