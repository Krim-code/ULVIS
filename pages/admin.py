import csv
import datetime
from django.contrib import admin
from django.http import HttpResponse
from .models import AboutSection, CategoryPhoto, ContactPage, HeroSlide,Category, Lead, LeadSection, OfferPage, PrivacyPage, USPItem, USPSection, GallerySection, GalleryImage, ReviewSection, Review
from django.db import models
from django_summernote.widgets import SummernoteWidget
@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ("__str__", "is_active", "order")
    list_editable = ("is_active", "order")
    search_fields = ("title", "subtitle")



class USPItemInline(admin.TabularInline):
    model = USPItem
    extra = 0
    fields = ("title", "text", "icon", "is_active", "order")
    show_change_link = True

@admin.register(USPSection)
class USPSectionAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "order")
    list_editable = ("is_active", "order")
    inlines = [USPItemInline]

@admin.register(USPItem)
class USPItemAdmin(admin.ModelAdmin):
    list_display = ("title", "section", "icon", "is_active", "order")
    list_filter = ("section", "is_active")
    list_editable = ("is_active", "order")
    search_fields = ("title", "text")

@admin.register(AboutSection)
class AboutSectionAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "order", "years", "projects", "partners")
    list_editable = ("is_active", "order")
    search_fields = ("title", "subtitle")


class GalleryImageInline(admin.TabularInline):
    model = GalleryImage
    extra = 0
    fields = ("image", "alt", "size", "is_active", "order")
    show_change_link = True

@admin.register(GallerySection)
class GallerySectionAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "order")
    list_editable = ("is_active", "order")
    inlines = [GalleryImageInline]

@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ("__str__", "section", "size", "is_active", "order")
    list_filter = ("section", "size", "is_active")
    list_editable = ("size", "is_active", "order")
    search_fields = ("alt",)

class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    fields = ("author","city","rating","text","avatar","is_active","order","date")
    show_change_link = True

@admin.register(ReviewSection)
class ReviewSectionAdmin(admin.ModelAdmin):
    list_display = ("title","is_active","use_slider","order")
    list_editable = ("is_active","use_slider","order")
    inlines = [ReviewInline]

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("author","section","rating","is_active","order")
    list_filter  = ("section","rating","is_active")
    list_editable = ("is_active","order")
    search_fields = ("author","text","city")

@admin.register(LeadSection)
class LeadSectionAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "order")
    list_editable = ("is_active", "order")
    search_fields = ("title",)
    ordering = ("order", "id")
    save_on_top = True


# --- actions ---
@admin.action(description="Пометить как В работе")
def make_in_work(modeladmin, request, queryset):
    queryset.update(status="in_work")

@admin.action(description="Пометить как Закрыта")
def make_done(modeladmin, request, queryset):
    queryset.update(status="done")

@admin.action(description="Экспорт в CSV")
def export_csv(modeladmin, request, queryset):
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    resp["Content-Disposition"] = f'attachment; filename="leads_{ts}.csv"'
    writer = csv.writer(resp, delimiter=";")
    writer.writerow(["Дата", "Имя", "Телефон", "Сообщение", "Статус",
                     "Источник", "UTM source", "UTM medium", "UTM campaign", "Referer", "IP"])
    for l in queryset.iterator():
        writer.writerow([
            l.created_at.strftime("%Y-%m-%d %H:%M"),
            l.name, l.phone, (l.message or "").replace("\n", " "),
            l.status, getattr(l, "source", ""),
            l.utm_source, l.utm_medium, l.utm_campaign, l.referer, l.ip
        ])
    return resp


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    # показ
    list_display = (
        "created_at", "name", "phone_pretty", "status",
        "source", "utm_source", "utm_campaign",
    )
    list_display_links = ("name",)
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 50
    save_on_top = True

    # фильтры/поиск
    list_filter = ("status", "source", "utm_source", "created_at")
    search_fields = ("name", "phone", "message", "utm_campaign", "utm_source")
    # нормализуем поиск по телефону: можно искать "7999", "8 999", "(999)"
    def get_search_results(self, request, queryset, search_term):
        qs, use_distinct = super().get_search_results(request, queryset, search_term)
        t = "".join(ch for ch in search_term if ch.isdigit())
        if t:
            qs |= queryset.filter(phone__regex=r".*%s.*" % t)
        return qs, use_distinct

    # read-only и группы полей
    readonly_fields = ("created_at", "ip", "referer", "utm_source", "utm_medium", "utm_campaign")
    fieldsets = (
        ("Клиент", {"fields": ("name", "phone", "message")}),
        ("Маркетинг", {"fields": ("source", "utm_source", "utm_medium", "utm_campaign", "referer", "ip")}),
        ("Сервис", {"fields": ("status", "admin_note", "created_at")}),
    )

    # действия
    actions = [make_in_work, make_done, export_csv]

    # красивый телефон
    @admin.display(description="Телефон", ordering="phone")
    def phone_pretty(self, obj):
        # +7 (999) 999-99-99 формат, если возможно
        d = "".join(ch for ch in obj.phone if ch.isdigit())
        if len(d) >= 11:
            d = ("7" + d[-10:]) if d[0] in "89" else d[:11]
            return f"+{d[0]} ({d[1:4]}) {d[4:7]}-{d[7:9]}-{d[9:11]}"
        return obj.phone
    

class CategoryPhotoInline(admin.TabularInline):
    model = CategoryPhoto
    extra = 0
    fields = ("image","title","size","is_active","order")
    readonly_fields = ()
    ordering = ("order","id")



@admin.register(CategoryPhoto)
class CategoryPhotoAdmin(admin.ModelAdmin):
    list_display = ("category","title","size","is_active","order")
    list_filter = ("category","size","is_active")
    search_fields = ("title",)
    ordering = ("category","order","id")

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("title","is_active","order")
    list_editable = ("is_active","order")
    prepopulated_fields = {"slug": ("title",)}
    fieldsets = (
        ("Базово", {"fields": ("title","slug","image","is_active","order")}),
        ("Хедер", {"fields": ("header_image","header_title","header_subtitle")}),
        ("Описание", {"fields": ("description",)}),
        ("SEO", {"fields": ("meta_title","meta_description")}),
    )



@admin.register(ContactPage)
class ContactPageAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "updated_at")
    list_editable = ("is_active",)
    fieldsets = (
        ("Хедер", {"fields": ("header_bg", "title", "subtitle")}),
        ("Контакты", {"fields": ("address", "phone", "email")}),
        ("Соцсети/мессенджеры", {"fields": ("whatsapp", "telegram", "vk")}),
        ("График и реквизиты", {"fields": ("schedule", "requisites")}),
        ("Карта", {"fields": ("map_embed",)}),
        ("Показ", {"fields": ("is_active",)}),
    )

    # Не даём плодить клонов — одна запись на проект
    def has_add_permission(self, request):
        if ContactPage.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(OfferPage)
class OfferAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "updated_at")
    list_editable = ("is_active",)
    fieldsets = (
        ("Основное", {"fields": ("title", "is_active")}),
        ("Контент",  {"fields": ("file", "html")}),
    )
    readonly_fields = ("updated_at",)

@admin.register(PrivacyPage)
class PrivacyAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "updated_at")
    formfield_overrides = {models.TextField: {"widget": SummernoteWidget()}}
    list_editable = ("is_active",)
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("updated_at",)
