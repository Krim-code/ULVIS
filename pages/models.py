from django.db import models
from django.utils.text import slugify
from ckeditor_uploader.fields import RichTextUploadingField

# Create your models here.
class HeroSlide(models.Model):
    title = models.CharField("Заголовок", max_length=120, blank=True)
    subtitle = models.CharField("Подзаголовок", max_length=255, blank=True)
    cta_text = models.CharField("Текст кнопки", max_length=60, blank=True, default="Узнать больше")
    cta_url = models.CharField("Ссылка кнопки", max_length=255, blank=True, default="#lead")
    image = models.ImageField("Фон", upload_to="slides/")
    is_active = models.BooleanField("Показывать", default=True)
    order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Слайд хиро"
        verbose_name_plural = "Слайды хиро"

    def __str__(self):
        return self.title or f"Слайд #{self.pk}"
    

# models.py
class Category(models.Model):
    title = models.CharField("Название", max_length=120)
    slug = models.SlugField("Слаг", max_length=140, unique=True, blank=True)
    image = models.ImageField("Картинка (превью)", upload_to="categories/")
    # --- новое ---
    header_image = models.ImageField("Хедер: большое изображение", upload_to="categories/headers/", blank=True, null=True)
    header_title = models.CharField("Хедер: заголовок", max_length=160, blank=True)
    header_subtitle = models.CharField("Хедер: подзаголовок", max_length=240, blank=True)
    description = models.TextField("Описание категории", blank=True)
    # SEO (по желанию)
    meta_title = models.CharField("SEO Title", max_length=160, blank=True)
    meta_description = models.CharField("SEO Description", max_length=240, blank=True)

    is_active = models.BooleanField("Показывать", default=True)
    order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    @property
    def og_image(self):
        return self.header_image or self.image

class CategoryPhoto(models.Model):
    class Size(models.TextChoices):
        NORMAL = "normal", "Обычная"
        WIDE   = "wide",   "Широкая (2 колонки)"
        TALL   = "tall",   "Высокая (2 строки)"

    category   = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="photos", verbose_name="Категория")
    image      = models.ImageField("Изображение", upload_to="category_photos/")
    title      = models.CharField("Подпись", max_length=160, blank=True)
    size       = models.CharField("Размер в сетке", max_length=12, choices=Size.choices, default=Size.NORMAL)
    is_active  = models.BooleanField("Показывать", default=True)
    order      = models.PositiveIntegerField("Порядок", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("order","id")
        verbose_name = "Фото категории"
        verbose_name_plural = "Фото категории"

    def __str__(self):
        return self.title or f"Фото #{self.pk}"

from django.db import models

class USPSection(models.Model):
    title = models.CharField("Заголовок секции", max_length=120, default="Почему мы")
    subtitle = models.CharField("Подзаголовок", max_length=255, blank=True)
    image = models.ImageField("Изображение слева", upload_to="usp/", blank=True, null=True)
    is_active = models.BooleanField("Показывать", default=True)
    order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Секция преимуществ"
        verbose_name_plural = "Секции преимуществ"

    def __str__(self):
        return self.title


ICON_CHOICES = [
    ("ruler", "Замер/дизайн"),
    ("truck", "Доставка/монтаж"),
    ("shield", "Гарантия"),
    ("timer", "Сроки"),
    ("cube", "Материалы"),
    ("star", "Качество"),
]

class USPItem(models.Model):
    section = models.ForeignKey(USPSection, on_delete=models.CASCADE, related_name="items")
    title = models.CharField("Заголовок", max_length=120)
    text = models.CharField("Описание", max_length=255, blank=True)
    icon = models.CharField("Иконка", max_length=24, choices=ICON_CHOICES, default="star")
    is_active = models.BooleanField("Показывать", default=True)
    order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Преимущество"
        verbose_name_plural = "Преимущества"

    def __str__(self):
        return self.title


class AboutSection(models.Model):
    is_active = models.BooleanField("Показывать секцию", default=True)
    order = models.PositiveIntegerField("Порядок", default=0)

    title = models.CharField("Заголовок", max_length=120, default="О компании")
    subtitle = models.CharField("Подзаголовок", max_length=255, blank=True)

    years = models.PositiveIntegerField("Лет на рынке", default=10)
    projects = models.PositiveIntegerField("Проектов", default=1000)
    partners = models.PositiveIntegerField("Партнёров", default=100)

    cta_text = models.CharField("Текст кнопки", max_length=60, default="Заказать проект")
    cta_url = models.CharField("Ссылка кнопки", max_length=255, default="#lead")

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Секция — О компании"
        verbose_name_plural = "Секция — О компании"

    def __str__(self):
        return f"{self.title} (active={self.is_active})"
    

class GallerySection(models.Model):
    title = models.CharField("Заголовок", max_length=160, default="Наша мебель в интерьере")
    is_active = models.BooleanField("Показывать секцию", default=True)
    order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Секция галереи"
        verbose_name_plural = "Секции галереи"

    def __str__(self):
        return self.title


SIZE_CHOICES = [
    ("auto", "Обычная"),
    ("wide", "Широкая"),
    ("tall", "Высокая"),
]

class GalleryImage(models.Model):
    section = models.ForeignKey(GallerySection, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField("Изображение", upload_to="gallery/")
    alt = models.CharField("ALT/подпись", max_length=180, blank=True)
    size = models.CharField("Размер в сетке", max_length=8, choices=SIZE_CHOICES, default="auto")
    is_active = models.BooleanField("Показывать", default=True)
    order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Картинка галереи"
        verbose_name_plural = "Картинки галереи"

    def __str__(self):
        return self.alt or f"#{self.pk}"
    


class ReviewSection(models.Model):
    is_active   = models.BooleanField("Показывать секцию", default=True)
    order       = models.PositiveIntegerField("Порядок", default=0)
    title       = models.CharField("Заголовок", max_length=160, default="Отзывы клиентов")
    subtitle    = models.CharField("Подзаголовок", max_length=255, blank=True)
    bg_image    = models.ImageField("Фоновое изображение", upload_to="reviews/", blank=True, null=True)
    use_slider  = models.BooleanField("Слайдер (Swiper)", default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Секция отзывов"
        verbose_name_plural = "Секция отзывов"

    def __str__(self):
        return self.title


RATING_CHOICES = [(i, f"{i}") for i in range(1, 6)]

class Review(models.Model):
    section     = models.ForeignKey(ReviewSection, on_delete=models.CASCADE, related_name="reviews")
    author      = models.CharField("Автор", max_length=120)
    city        = models.CharField("Город", max_length=120, blank=True)
    text        = models.TextField("Текст")
    rating      = models.IntegerField("Оценка", choices=RATING_CHOICES, default=5)
    avatar      = models.ImageField("Аватар", upload_to="reviews/avatars/", blank=True, null=True)
    is_active   = models.BooleanField("Показывать", default=True)
    order       = models.PositiveIntegerField("Порядок", default=0)
    date        = models.DateField("Дата", blank=True, null=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"

    def __str__(self):
        return f"{self.author}: {self.text[:30]}…"
    


from django.core.validators import RegexValidator

# Секция CTA (управляется из админки)
class LeadSection(models.Model):
    is_active  = models.BooleanField("Показывать секцию", default=True)
    order      = models.PositiveIntegerField("Порядок", default=0)
    title      = models.CharField("Заголовок", max_length=160, default="Мы спроектируем и изготовим, доставим бесплатно")
    subtitle   = models.CharField("Подзаголовок", max_length=255, blank=True)
    bg_image   = models.ImageField("Фон", upload_to="cta/", blank=True, null=True)
    cta_text   = models.CharField("Текст кнопки", max_length=60, default="Отправить")
    class Meta:
        ordering = ["order","id"]
        verbose_name = "Секция CTA/Форма"
        verbose_name_plural = "Секция CTA/Форма"
    def __str__(self): return self.title

# Валидация РФ номера: +7XXXXXXXXXX или 8XXXXXXXXXX, пробелы/скобки/дефисы игнорим
ru_phone_validator = RegexValidator(
    regex=r'^(?:\+7|8)\s*\(?\d{3}\)?\s*-?\s*\d{3}\s*-?\s*\d{2}\s*-?\s*\d{2}$',
    message="Телефон должен быть в формате +7XXXXXXXXXX или 8XXXXXXXXXX"
)

class Lead(models.Model):
    name      = models.CharField("Имя", max_length=120)
    phone     = models.CharField("Телефон", max_length=32, validators=[ru_phone_validator])
    message   = models.TextField("Сообщение", blank=True)
    utm_source = models.CharField("utm_source", max_length=80, blank=True)
    utm_medium = models.CharField("utm_medium", max_length=80, blank=True)
    utm_campaign = models.CharField("utm_campaign", max_length=120, blank=True)
    referer   = models.URLField("Реферер", blank=True)
    ip        = models.GenericIPAddressField("IP", blank=True, null=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    status    = models.CharField("Статус", max_length=20, default="new",
                                 choices=[("new","Новая"),("in_work","В работе"),("done","Закрыта")])
    admin_note = models.TextField("Заметка менеджера", blank=True)
    source = models.CharField("Источник", max_length=64, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"

    def __str__(self):
        return f"{self.name} — {self.phone}"
    

class ContactPage(models.Model):
    # Хедер
    header_bg   = models.ImageField("Фон хедера", upload_to="contacts/", blank=True, null=True)
    title       = models.CharField("Заголовок", max_length=160, default="Контакты")
    subtitle    = models.CharField("Подзаголовок", max_length=240, blank=True)

    # Основные контакты
    address     = models.CharField("Адрес", max_length=240, blank=True)
    phone       = models.CharField("Телефон", max_length=64, blank=True)
    email       = models.EmailField("Email", blank=True)

    # Мессенджеры/соцсети (по-простому полями; хочешь — сделаем отдельной таблицей)
    whatsapp    = models.URLField("WhatsApp", blank=True)
    telegram    = models.URLField("Telegram", blank=True)
    vk          = models.URLField("VK", blank=True)

    # Режим работы (многострочный текст)
    schedule    = models.TextField("График работы", blank=True,
                    help_text="Каждую строку – отдельной строкой, например: Пн–Пт 10:00–20:00")

    # Реквизиты (многострочный текст)
    requisites  = models.TextField("Реквизиты", blank=True)

    # Карта: либо embed-код, либо координаты
    map_embed   = models.TextField("Карта (iframe-embed)", blank=True,
                    help_text='Вставь iframe от Яндекс/Google. Если заполнено – координаты ниже игнорятся.')
    map_lat     = models.DecimalField("Широта", max_digits=9, decimal_places=6, blank=True, null=True)
    map_lng     = models.DecimalField("Долгота", max_digits=9, decimal_places=6, blank=True, null=True)
    map_zoom    = models.PositiveSmallIntegerField("Зум", default=15)

    # Служебное
    is_active   = models.BooleanField("Показывать", default=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Страница «Контакты»"
        verbose_name_plural = "Страница «Контакты»"

    def __str__(self):
        return f"Контакты (обновлено {self.updated_at:%Y-%m-%d %H:%M})"
    



class OfferPage(models.Model):
    title = models.CharField("Заголовок", max_length=160, default="Публичная оферта")
    file = models.FileField("Файл оферты (PDF/Docx)", upload_to="legal/", blank=True, null=True)
    html = models.TextField("Текст (если без файла)", blank=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Оферта"
        verbose_name_plural = "Оферта"

    def __str__(self):
        return self.title


class PrivacyPage(models.Model):
    title = models.CharField("Заголовок", max_length=160, default="Политика конфиденциальности")
    slug = models.SlugField(max_length=64, default="privacy", unique=True)
    content =  models.TextField("Текст", blank=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Политика конфиденциальности"
        verbose_name_plural = "Политики конфиденциальности"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:64]
        super().save(*args, **kwargs)