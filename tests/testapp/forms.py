from django import forms

from .models import Article, Author, Comment


class AuthorForm(forms.ModelForm):
    class Meta:
        model = Author
        fields = ["name", "email", "avatar"]


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = [
            "title",
            "slug",
            "body",
            "status",
            "featured",
            "author",
            "tags",
            "cover",
            "published_at",
        ]

    def clean_slug(self) -> str:
        slug = self.cleaned_data["slug"]
        if slug == "reserved":
            raise forms.ValidationError("That slug is reserved.")
        return slug


CommentFormSet = forms.inlineformset_factory(
    Article, Comment, fields=["author_name", "body", "approved"], extra=1, can_delete=True
)
