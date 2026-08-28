from __future__ import annotations

import io
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from demo.models import Article, Author, Comment, Tag

AUTHORS = [
    ("Ada Lovelace", "ada@analytical.example"),
    ("Grace Hopper", "grace@compiler.example"),
    ("Katherine Johnson", "katherine@orbit.example"),
    ("Alan Turing", "alan@bombe.example"),
    ("Radia Perlman", "radia@spanningtree.example"),
    ("Barbara Liskov", "barbara@substitution.example"),
    ("Donald Knuth", "don@literate.example"),
    ("Margaret Hamilton", "margaret@apollo.example"),
]

TAGS = [
    "architecture",
    "performance",
    "security",
    "testing",
    "django",
    "htmx",
    "alpine",
    "forms",
    "databases",
    "deployment",
    "tooling",
    "ux",
]

TITLES = [
    "Rendering forms without a build step",
    "A field is not a widget",
    "The queryset never reaches order_by",
    "Client-side tables under two hundred rows",
    "Closures that know what they need",
    "One adapter for every hx attribute",
    "Escaping is a property of the position",
    "Sessions beat hidden fields for wizards",
    "Re-scoping bulk actions to the filtered set",
    "Why the schema decorates the form",
    "Thumbnails on write, not on render",
    "EXIF, orientation, and the GPS you forgot",
    "Semantic classes and the purge problem",
    "A Resource is four plain views",
    "Permission checks belong in two places",
    "The cost of a COUNT on a joined table",
    "Alpine, CSP, and the unsafe-eval tradeoff",
    "What Livewire does that htmx does not",
    "Diff coverage as a merge gate",
    "The registry only ever sees a key",
]

BODY = (
    "This entry walks through the reasoning, the tradeoffs considered, and the "
    "shape of the final implementation. It is deliberately concrete: every claim "
    "is backed by a test, and every alternative that was rejected is named.\n\n"
    "The short version is that the boring choice was usually the right one."
)

COMMENTERS = ["j.dev", "sam", "pat", "morgan", "riley", "casey", "quinn"]


def _avatar(name: str) -> ContentFile:
    from PIL import Image, ImageDraw

    seed = sum(ord(c) for c in name)
    rng = random.Random(seed)
    size = 256
    top = (rng.randint(40, 210), rng.randint(40, 210), rng.randint(40, 210))
    img = Image.new("RGB", (size, size), top)
    draw = ImageDraw.Draw(img)
    initials = "".join(part[0] for part in name.split()[:2]).upper()
    draw.ellipse((size * 0.12, size * 0.12, size * 0.88, size * 0.88), fill=(255, 255, 255, 40))
    try:
        draw.text((size / 2, size / 2), initials, anchor="mm", fill="white")
    except TypeError:
        draw.text((size * 0.38, size * 0.4), initials, fill="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return ContentFile(buf.getvalue(), name=f"{slugify(name)}.png")


def _cover(title: str) -> ContentFile:
    from PIL import Image

    rng = random.Random(hash(title) & 0xFFFFFF)
    w, h = 1200, 630
    base = (rng.randint(20, 90), rng.randint(20, 90), rng.randint(30, 120))
    img = Image.new("RGB", (w, h), base)
    px = img.load()
    for y in range(h):
        shade = int(30 * (y / h))
        for x in range(0, w, 3):
            px[x, y] = (
                min(base[0] + shade, 255),
                min(base[1] + shade, 255),
                min(base[2] + shade, 255),
            )
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=70)
    return ContentFile(buf.getvalue(), name=f"{slugify(title)[:40]}.jpg")


class Command(BaseCommand):
    help = "Populate the demo with realistic data. --fresh wipes first; --big N adds bulk rows."

    def add_arguments(self, parser):
        parser.add_argument("--fresh", action="store_true", help="delete existing demo data first")
        parser.add_argument(
            "--big", type=int, default=0, help="extra bulk articles for server-mode"
        )
        parser.add_argument("--no-images", action="store_true", help="skip avatar/cover generation")

    def handle(self, *args, **opts):
        rng = random.Random(42)

        if opts["fresh"]:
            Comment.objects.all().delete()
            Article.objects.all().delete()
            Tag.objects.all().delete()
            Author.objects.all().delete()
            self.stdout.write("wiped existing demo data")

        User = get_user_model()
        if not User.objects.filter(username="demo").exists():
            User.objects.create_superuser("demo", "demo@example.com", "demo")
            self.stdout.write(self.style.SUCCESS("superuser  demo / demo"))

        tags = [Tag.objects.get_or_create(name=t)[0] for t in TAGS]

        authors = []
        for name, email in AUTHORS:
            author, created = Author.objects.get_or_create(name=name, defaults={"email": email})
            if created and not opts["no_images"]:
                author.avatar.save(f"{slugify(name)}.png", _avatar(name), save=True)
            authors.append(author)

        now = timezone.now()
        made = 0
        for i, title in enumerate(TITLES * 3):
            slug = slugify(f"{title}-{i}")
            if Article.objects.filter(slug=slug).exists():
                continue
            status = rng.choices(
                [Article.Status.LIVE, Article.Status.DRAFT, Article.Status.ARCHIVED],
                weights=[6, 3, 1],
            )[0]
            created_at = now - timedelta(
                days=rng.randint(1, 540), hours=rng.randint(0, 23), minutes=rng.randint(0, 59)
            )
            art = Article.objects.create(
                title=title if i < len(TITLES) else f"{title} ({i // len(TITLES) + 1})",
                slug=slug,
                body=BODY,
                status=status,
                featured=rng.random() < 0.15,
                author=rng.choice(authors),
                published_at=created_at.date() if status == Article.Status.LIVE else None,
            )
            Article.objects.filter(pk=art.pk).update(created_at=created_at)
            art.tags.set(rng.sample(tags, rng.randint(1, 4)))
            if not opts["no_images"] and rng.random() < 0.6:
                art.cover.save(f"{slug[:40]}.jpg", _cover(title), save=True)
            for _ in range(rng.randint(0, 5)):
                Comment.objects.create(
                    article=art,
                    author_name=rng.choice(COMMENTERS),
                    body="Useful writeup — the part about re-scoping clicked for me.",
                    approved=rng.random() < 0.7,
                )
            made += 1

        if opts["big"]:
            bulk = [
                Article(
                    title=f"Log entry {n}",
                    slug=f"log-entry-{n}",
                    status=Article.Status.LIVE,
                    author=authors[n % len(authors)],
                )
                for n in range(opts["big"])
            ]
            Article.objects.bulk_create(bulk, batch_size=2000, ignore_conflicts=True)

        self.stdout.write(
            self.style.SUCCESS(
                f"authors={Author.objects.count()} tags={Tag.objects.count()} "
                f"articles={Article.objects.count()} comments={Comment.objects.count()} "
                f"(+{made} new)"
            )
        )
