import pytest


@pytest.fixture
def template(tmp_path):
    template = tmp_path / 'test_template.j2'
    template.write_text("""
    {% if not is_append %}# Example{% endif %}
    {{ TITLE }}

    ```bash
    {% for line in input_lines %}{{ line }}
    {% endfor %}
    ```
    """)
    return str(template)
