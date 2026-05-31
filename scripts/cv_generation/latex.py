from typing import Any

LATEX_REPLACEMENTS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "€": r"\texteuro{}",
}


def escape_tex(value: Any) -> str:
    if value is None:
        return ""
    return "".join(LATEX_REPLACEMENTS.get(char, char) for char in str(value))


def escape_url(value: Any) -> str:
    if value is None:
        return ""
    # Hyperref receives URLs inside \detokenize so normal URL punctuation is preserved.
    return str(value).replace("}", "%7D")


def href_url(value: Any) -> str:
    return r"\detokenize{" + escape_url(value) + "}"


def category_label(value: str) -> str:
    special = {
        "programming_languages": "Programming",
        "machine_learning": "ML",
        "cloud_devops": "Cloud & DevOps",
    }
    return special.get(value, value.replace("_", " ").title())
