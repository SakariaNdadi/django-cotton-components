from django import forms

from .models import Article


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
        widgets = {"published_at": forms.DateInput(attrs={"type": "date"})}
