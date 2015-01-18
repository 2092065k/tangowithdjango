from django.contrib import admin
from rango.models import Category, Page

admin.AdminSite.site_header = "Rango's sheriff office"

class CategoryAdmin(admin.ModelAdmin):
    fields = ['name', 'views', 'likes']
    list_display = ('name', 'views', 'likes')

admin.site.register(Category, CategoryAdmin)

class PageAdmin(admin.ModelAdmin):
    fields = ['title', 'category', 'url', 'views']
    list_display = ('title', 'category', 'url')

admin.site.register(Page, PageAdmin)
