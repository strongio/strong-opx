import base64

from strong_opx.template.template import Template


@Template.register_filter("base64")
def base64_filter(v: str) -> str:
    return base64.b64encode(v.encode("utf-8")).decode("utf-8")
