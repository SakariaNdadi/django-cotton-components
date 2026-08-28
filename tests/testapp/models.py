from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True)

    def __str__(self) -> str:
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=60, unique=True)

    def __str__(self) -> str:
        return self.name


class Article(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        LIVE = "live", "Live"
        ARCHIVED = "archived", "Archived"

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    body = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    featured = models.BooleanField(default=False)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="articles")
    tags = models.ManyToManyField(Tag, blank=True, related_name="articles")
    cover = models.ImageField(upload_to="covers/", blank=True)
    published_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.title


class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="comments")
    author_name = models.CharField(max_length=120)
    body = models.TextField()
    approved = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.author_name} on {self.article_id}"
