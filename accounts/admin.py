from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Account, UserProfile
from django.utils.html import format_html
# Register your models here.

class AccountAdmin(UserAdmin):
    list_display = ('email','first_name','last_name','username','date_joined','last_login','is_admin','is_staff')
    search_fields = ('email','first_name','last_name')
    readonly_fields = ('date_joined','last_login')
    list_diplay_links = ('email','first_name','last_name')
    ordering = ('-date_joined',)

    filter_horizontal = ()
    list_filter = ()
    fieldsets = ()

class UserProfileAdmin(admin.ModelAdmin):
    def thumbnail(self, profile):
        if not profile.profile_picture:
            return 'No profile picture'
        return format_html(
            '<img src="{}" width="30" style="border-radius: 50%;">',
            profile.profile_picture.url,
        )
    thumbnail.short_description = 'Profile Picture'
    list_display = ('thumbnail','user','city','state','country')

admin.site.register(UserProfile,UserProfileAdmin)
admin.site.register(Account,AccountAdmin)
