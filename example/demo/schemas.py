from django_control_components.schemas import (
    FileUpload,
    MultiSelect,
    Schema,
    Section,
    Select,
    Textarea,
    TextInput,
    Toggle,
)

from .forms import ArticleForm


def article_schema() -> Schema:
    return (
        Schema.make()
        .form(ArticleForm)
        .schema(
            [
                Section.make("Content")
                .columns(1)
                .description("The parts readers see. Title and slug are required.")
                .schema(
                    [
                        TextInput.make("title").required().column_span_full(),
                        TextInput.make("slug")
                        .required()
                        .help_text("URL fragment - lowercase, dashes."),
                        Select.make("status").searchable(),
                        Textarea.make("body").column_span_full(),
                    ]
                ),
                Section.make("Publishing")
                .columns(2)
                .description("Ownership, taxonomy, and the publish date.")
                .schema(
                    [
                        Select.make("author").searchable(),
                        MultiSelect.make("tags").help_text("Type to filter."),
                        Toggle.make("featured").help_text("Show on the marketing page."),
                        TextInput.make("published_at")
                        .visible_when("status", equals="live")
                        .help_text("Only asked for when status is Live - zero requests."),
                    ]
                ),
                Section.make("Cover image").schema(
                    [
                        FileUpload.make("cover")
                        .image()
                        .max_size("5MB")
                        .resize(max_width=1600)
                        .convert("webp", quality=82)
                        .strip_exif()
                        .help_text("Validated with Pillow, resized and re-encoded on save."),
                    ]
                ),
            ]
        )
    )
