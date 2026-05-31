from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound

from scripts.cv_generation.errors import CvGenerationError
from scripts.cv_generation.files import ROOT
from scripts.cv_generation.latex import category_label, escape_tex, escape_url, href_url


def render_cv(context: dict[str, Any], template_name: str) -> str:
    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
    )
    env.filters["tex"] = escape_tex
    env.filters["tex_url"] = escape_url
    env.filters["href_url"] = href_url
    env.filters["category_label"] = category_label
    try:
        template = env.get_template(template_name)
    except TemplateNotFound:
        raise CvGenerationError(f"Template not found: templates/{template_name}") from None
    return template.render(**context)
