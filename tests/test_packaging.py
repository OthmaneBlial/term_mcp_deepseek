from importlib.metadata import version
from importlib.resources import files

from term_mcp_deepseek import __version__


def test_version_has_one_package_source_of_truth():
    assert version("term-mcp-deepseek") == __version__


def test_runtime_assets_are_packaged_with_the_application():
    package = files("term_mcp_deepseek")

    assert package.joinpath("static/chat.html").is_file()
    assert package.joinpath("static/app.css").is_file()
    assert package.joinpath("static/app.js").is_file()
    assert package.joinpath("static/favicon.svg").is_file()
    assert package.joinpath("schemas/receipt.schema.json").is_file()
    assert package.joinpath("schemas/recipe.schema.json").is_file()
