

class HttpHeaders(dict):
    def __init__(self, *args, **kwargs):
        self.update(*args, **kwargs)

    def __getitem__(self, item: str) -> str:
        pass
