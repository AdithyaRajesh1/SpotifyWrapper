from django.contrib import admin
from .models import Social
from .models import ContactRequest
# Register your models here.
admin.site.register(Social)

@admin.register(ContactRequest)
class ContactRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'submitted_at')
    list_filter = ('submitted_at',)
    search_fields = ('name', 'email')